"""In-memory job registry for long-running MCP tools (v8.0 Phase 56).

AI generation/extraction tools run ~60s+, which exceeds MCP client timeouts.
Those tools start a background asyncio task and return a job_id immediately; the
agent polls the generic `job_status` tool until the job is done and reads the
result.

The registry is in-memory with a TTL sweep (decision D-56-A): jobs are
short-lived and polled within one agent session, so they need not survive a
restart (the agent just re-fires). Single-uvicorn-worker deployment assumed; for
multi-worker, move this to Redis/DB.
"""

import asyncio
import time
import uuid
from typing import Any, Awaitable, Callable, Optional

# Job lifetime after completion before the sweeper may drop it.
_JOB_TTL_SECONDS = 3600

# status values
PENDING = "pending"
RUNNING = "running"
DONE = "done"
ERROR = "error"


class _Job:
    __slots__ = ("id", "status", "result", "error", "owner_id", "kind", "created_at", "updated_at")

    def __init__(self, job_id: str, owner_id: str, kind: str):
        self.id = job_id
        self.status = PENDING
        self.result: Any = None
        self.error: Optional[str] = None
        self.owner_id = owner_id
        self.kind = kind
        self.created_at = time.time()
        self.updated_at = self.created_at

    def to_dict(self) -> dict:
        return {
            "job_id": self.id,
            "status": self.status,
            "kind": self.kind,
            "result": self.result,
            "error": self.error,
        }


class JobRegistry:
    def __init__(self):
        self._jobs: dict[str, _Job] = {}
        self._lock = asyncio.Lock()

    async def create(self, owner_id: str, kind: str) -> _Job:
        async with self._lock:
            self._sweep_locked()
            job_id = uuid.uuid4().hex
            job = _Job(job_id, owner_id, kind)
            self._jobs[job_id] = job
            return job

    async def get(self, job_id: str, owner_id: str) -> Optional[_Job]:
        """Return the job only if owned by owner_id (owner-scoping, MCPF-04)."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.owner_id != owner_id:
                return None
            return job

    async def _set(self, job_id: str, *, status: str, result: Any = None, error: Optional[str] = None):
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = status
            if result is not None:
                job.result = result
            if error is not None:
                job.error = error
            job.updated_at = time.time()

    def _sweep_locked(self):
        now = time.time()
        stale = [
            jid for jid, j in self._jobs.items()
            if j.status in (DONE, ERROR) and (now - j.updated_at) > _JOB_TTL_SECONDS
        ]
        for jid in stale:
            del self._jobs[jid]

    async def run(self, job: _Job, coro_factory: Callable[[], Awaitable[Any]]):
        """Run an async job in the background, recording status + result/error.

        coro_factory is called (not awaited) here and produces the awaitable that
        does the real work. It must NOT hold a DB session across its internal
        awaits (decision D-56-B) — load context, run the AI sessionless, persist.
        """
        await self._set(job.id, status=RUNNING)

        async def _runner():
            try:
                result = await coro_factory()
                await self._set(job.id, status=DONE, result=result)
            except Exception as exc:  # noqa: BLE001 — surface any failure as job error
                await self._set(job.id, status=ERROR, error=str(exc))

        asyncio.create_task(_runner())


# Module-level singleton used by all long-running tools.
registry = JobRegistry()
