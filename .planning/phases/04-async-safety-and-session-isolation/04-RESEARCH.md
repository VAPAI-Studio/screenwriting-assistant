# Phase 4: Async Safety and Session Isolation - Research

**Researched:** 2026-03-11
**Domain:** SQLAlchemy session management under concurrent async tasks
**Confidence:** HIGH

## Summary

Phase 4 addresses a known bug (REVW-05) where `run_multi_agent_review` in `agent_service.py` shares a single SQLAlchemy `Session` across multiple concurrent `asyncio.gather` tasks, causing intermittent `DetachedInstanceError` and `MissingGreenlet` exceptions. The fix is straightforward: change the function signature to accept a `session_factory` callable (the existing `SessionLocal` from `db.py`), and have each parallel task create and close its own session.

This project uses **synchronous** SQLAlchemy (`sqlalchemy.orm.Session` + `sessionmaker`) with async FastAPI endpoints. The `asyncio.gather` calls are used for concurrent LLM API calls, but each task also performs synchronous DB reads (via `rag_service` queries) using the same shared session. The solution does not require migrating to async SQLAlchemy (`AsyncSession`/`async_sessionmaker`) -- it only requires each task to get its own sync `Session` instance from the existing `SessionLocal` factory.

**Primary recommendation:** Refactor `run_multi_agent_review` (and the two `_orchestrate`/`_orchestrate_stream_prepare` methods that use `asyncio.gather` with shared sessions) to accept a `Callable[[], Session]` (`session_factory`) parameter instead of a shared `Session`. Each gathered task creates its own session, uses it for DB reads, and closes it in a `finally` block.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REVW-05 | Fix shared DB session bug in existing `run_multi_agent_review` for safe concurrent async context | Session-per-task pattern documented below; three `asyncio.gather` call sites identified; `SessionLocal` already exists as the factory |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.27 | ORM + session management | Already in use; session-per-task is the documented concurrency pattern |
| FastAPI | 0.110.0 | Async web framework | Already in use; provides the async context where gather runs |
| pytest-asyncio | 0.23.5 | Async test support | Already in use; needed for testing concurrent session behavior |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `SessionLocal` (app.db) | N/A | Existing session factory | Pass as `session_factory` callable to `run_multi_agent_review` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Sync `sessionmaker` per-task | `async_sessionmaker` + `AsyncSession` | Full async migration is a major refactor; overkill for this bug fix. The concurrency issue is DB reads during concurrent LLM calls, not DB I/O bottleneck |
| `session_factory` callable param | `scoped_session` with asyncio context | SQLAlchemy docs explicitly recommend against scoped sessions for asyncio |

**Installation:**
```bash
# No new packages needed -- all dependencies already installed
```

## Architecture Patterns

### Current Broken Pattern (3 sites)

All three `asyncio.gather` call sites in `agent_service.py` share a single `db: Session`:

```
# Site 1: run_multi_agent_review (line 1027) -- THE TARGET
# Creates tasks that call review_section(), which calls rag_service DB queries
tasks = [self.review_section(agent, section, project, db) for agent in agents]
results = await asyncio.gather(*tasks, return_exceptions=True)

# Site 2: _orchestrate (line 843)
# Creates tasks that call _get_specialist_context(), which calls rag_service.semantic_search()
tasks = [self._get_specialist_context(agent, user_message, owner_id, db) for agent in selected]
results = await asyncio.gather(*tasks, return_exceptions=True)

# Site 3: _orchestrate_stream_prepare (line 650)
# Same pattern as Site 2
tasks = [self._get_specialist_context(agent, user_message, owner_id, db) for agent in selected]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### Recommended Fix Pattern: Session-Per-Task

```python
# Source: SQLAlchemy 2.0 docs - Session Basics
# "Session per thread, AsyncSession per task"
# For sync sessions in async context: each task gets its own Session

from typing import Callable
from sqlalchemy.orm import Session

async def run_multi_agent_review(
    self,
    agents: List[Agent],
    section: Section,
    project: Project,
    session_factory: Callable[[], Session],  # CHANGED: callable, not instance
) -> List[Dict]:
    """Run all agents in parallel on a section."""
    tasks = [
        asyncio.wait_for(
            self._review_section_with_own_session(
                agent, section, project, session_factory
            ),
            timeout=settings.AGENT_REVIEW_TIMEOUT,
        )
        for agent in agents
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # ... error handling unchanged ...

async def _review_section_with_own_session(
    self,
    agent: Agent,
    section: Section,
    project: Project,
    session_factory: Callable[[], Session],
) -> Dict:
    """Wrapper that creates/closes a per-task session."""
    db = session_factory()
    try:
        return await self.review_section(agent, section, project, db)
    finally:
        db.close()
```

### Pattern for Orchestrator Sites (2 and 3)

Same fix applies to `_orchestrate` and `_orchestrate_stream_prepare`:

```python
async def _get_specialist_context_with_own_session(
    self,
    agent: Agent,
    query_text: str,
    owner_id,
    session_factory: Callable[[], Session],
) -> Dict:
    db = session_factory()
    try:
        return await self._get_specialist_context(agent, query_text, owner_id, db)
    finally:
        db.close()
```

### Call Sites That Must Pass `session_factory`

There is currently **only one direct caller** of `run_multi_agent_review`:
- **None in the current codebase.** `run_multi_agent_review` is defined but has zero callers today. It will be called in Phase 5 (Agent Review Middleware).

However, `_orchestrate` and `_orchestrate_stream_prepare` ARE called from `chat.py` endpoints:
- `chat.py` line 158: `agent_service.chat()` calls `_orchestrate()` internally
- `chat.py` line 184: `agent_service.chat_stream_prepare()` calls `_orchestrate_stream_prepare()` internally

These internal callers receive `db: Session` from the endpoint. The fix needs to thread through the `session_factory` or import `SessionLocal` directly.

### Recommended Project Structure Change

No new files needed. Changes affect:
```
backend/app/
  services/
    agent_service.py   # Refactor 3 asyncio.gather sites
  api/endpoints/
    chat.py            # Pass SessionLocal as session_factory to chat/chat_stream_prepare
```

### Anti-Patterns to Avoid
- **Passing `SessionLocal` as a default parameter:** Don't set `session_factory=SessionLocal` in the method signature. Import and pass explicitly at call sites for testability.
- **Reloading ORM objects inside per-task sessions:** The `agent`, `section`, `project` objects passed into each task were loaded by the request session. Reading their **already-loaded attributes** (name, system_prompt_template, etc.) is safe. Only lazy-loading unloaded relationships from a detached object would fail. Verify that `review_section` and `_get_specialist_context` only use already-loaded attributes from the passed ORM objects, and use the per-task `db` only for fresh queries.
- **Forgetting to close sessions on exception:** Always use `try/finally` pattern, not context managers (`with`), because `Session` is not a sync context manager in SQLAlchemy 2.0 `sessionmaker`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Session factory | Custom factory class | `SessionLocal` from `app.db` | Already configured with correct engine + pool settings |
| Async session management | `AsyncSession`/`async_sessionmaker` | Sync `Session` per-task via `SessionLocal()` | Project uses sync SQLAlchemy; async migration is out of scope |
| Connection pooling | Manual pool management | SQLAlchemy engine pool (default `QueuePool`) | Already handles concurrent session access safely at the connection level |

**Key insight:** The fix is purely about session **isolation**, not about making the DB layer async. Each sync session uses its own connection from the pool; the pool already handles concurrent access.

## Common Pitfalls

### Pitfall 1: Lazy-Loading Across Session Boundaries
**What goes wrong:** ORM objects loaded in the request session have relationships that may not be loaded yet. If a per-task session tries to lazy-load a relationship on an object from a different session, you get `DetachedInstanceError`.
**Why it happens:** `review_section()` accesses `agent.system_prompt_template`, `agent.personality`, `agent.agent_type`, `agent.tags_filter`, `project.framework`, `project.sections`, `section.type`, `section.user_notes`. Some of these may trigger lazy loads.
**How to avoid:** Before entering `asyncio.gather`, eagerly load all attributes that tasks will need. Alternatively, pass primitive values (strings, dicts) instead of ORM objects into the per-task functions. The simplest approach: use `db.refresh(agent)` or access all needed attributes before gather, or re-query the objects by ID inside each per-task session.
**Warning signs:** Intermittent errors only when concurrency > 1; works fine with a single agent.

### Pitfall 2: Session Not Closed on Task Cancellation
**What goes wrong:** `asyncio.wait_for` cancels tasks that exceed the timeout. If the cancellation happens mid-query, the session may not be closed, leaking a connection from the pool.
**Why it happens:** `asyncio.CancelledError` bypasses `except Exception` blocks (in Python 3.9+, `CancelledError` is a `BaseException`).
**How to avoid:** Use `try/finally` (not `try/except`) for session cleanup. `finally` blocks execute even on cancellation.
**Warning signs:** Connection pool exhaustion under load; slow DB queries after many timeouts.

### Pitfall 3: Test Database Using SQLite With StaticPool
**What goes wrong:** The test suite uses `SQLite in-memory + StaticPool` (single connection). Creating multiple sessions from the test `SessionLocal` all share the same underlying connection. Per-task sessions in tests won't truly isolate.
**Why it happens:** `StaticPool` returns the same connection every time, which is correct for single-threaded test isolation but means concurrent session access in tests still serializes.
**How to avoid:** For the integration test (plan 04-03), mock the DB operations and focus on verifying that `session_factory` is called N times, sessions are closed, and no exceptions propagate. Don't try to prove true parallel DB isolation in SQLite -- that's a PostgreSQL-only guarantee.
**Warning signs:** Tests pass but production still fails; false sense of security.

### Pitfall 4: Forgetting to Update _orchestrate Methods
**What goes wrong:** Only fixing `run_multi_agent_review` but leaving `_orchestrate` and `_orchestrate_stream_prepare` with the same shared-session bug.
**Why it happens:** Phase 4 requirement REVW-05 explicitly names `run_multi_agent_review`, but the same pattern exists in two other methods.
**How to avoid:** Fix all three `asyncio.gather` sites in the same refactor. They share the identical pattern.
**Warning signs:** Orchestrator chat mode produces intermittent DetachedInstanceError after Phase 4.

## Code Examples

### Example 1: Session Factory Type Annotation

```python
# Source: SQLAlchemy 2.0 docs + project convention
from typing import Callable
from sqlalchemy.orm import Session

# The session_factory type is a callable that returns a Session
SessionFactory = Callable[[], Session]

# In practice, SessionLocal from app.db is this callable:
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# SessionLocal() returns a new Session instance
```

### Example 2: Per-Task Session Wrapper

```python
# Pattern for wrapping existing methods with session isolation
async def _review_with_session(
    self,
    agent: Agent,
    section: Section,
    project: Project,
    session_factory: SessionFactory,
) -> Dict:
    db = session_factory()
    try:
        # Re-query objects by ID in the new session to avoid cross-session access
        # Only needed if review_section lazy-loads relationships
        return await self.review_section(agent, section, project, db)
    finally:
        db.close()
```

### Example 3: Caller Update in chat.py

```python
# Source: existing pattern in chat.py line 216 (finalize_db = SessionLocal())
from ...db import SessionLocal

# In chat endpoint or agent_service method:
result = await agent_service.chat(
    session=session,
    user_message=data.content,
    db=db,
    session_factory=SessionLocal,  # NEW PARAM
)
```

### Example 4: Integration Test for Concurrent Session Safety

```python
# Source: project test conventions (conftest.py)
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call

@pytest.mark.asyncio
async def test_run_multi_agent_review_creates_separate_sessions():
    """Each concurrent agent review gets its own session."""
    mock_session_1 = MagicMock()
    mock_session_2 = MagicMock()
    mock_session_3 = MagicMock()
    sessions = [mock_session_1, mock_session_2, mock_session_3]

    factory = MagicMock(side_effect=sessions)

    service = AgentService()
    # Mock review_section to return a result and verify it receives different sessions
    with patch.object(service, 'review_section', new_callable=AsyncMock) as mock_review:
        mock_review.return_value = {"status": "completed", ...}

        agents = [MagicMock(), MagicMock(), MagicMock()]
        result = await service.run_multi_agent_review(
            agents=agents,
            section=MagicMock(),
            project=MagicMock(),
            session_factory=factory,
        )

    # Factory called 3 times (once per agent)
    assert factory.call_count == 3
    # Each session closed
    for s in sessions:
        s.close.assert_called_once()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Shared `Session` across `asyncio.gather` | `session_factory` callable; per-task session | SQLAlchemy 1.4+ documented this pattern | Eliminates `DetachedInstanceError` in concurrent contexts |
| `scoped_session` for threading | Direct session-per-task management | SQLAlchemy 2.0 deprecated `scoped_session` for async | Simpler, more explicit lifecycle control |

**Deprecated/outdated:**
- `scoped_session`: SQLAlchemy docs recommend against it for asyncio contexts. Direct session management is preferred.

## Open Questions

1. **Do `review_section` and `_get_specialist_context` lazy-load any unloaded relationships?**
   - What we know: `review_section` accesses `agent.system_prompt_template`, `agent.personality`, `agent.agent_type`, `agent.tags_filter`, `project.framework`, `project.sections` (sorted), `section.type`, `section.user_notes`. The `_get_specialist_context` method accesses `agent.agent_type`, `agent.tags_filter`.
   - What's unclear: Whether `project.sections` is eagerly loaded when the project is queried in the chat endpoint. If not, accessing it inside a per-task session would fail because the project was loaded by a different session.
   - Recommendation: Audit Plan 04-01 must check relationship loading strategies. If lazy-loaded, either (a) eagerly load before gather, (b) re-query by ID inside per-task session, or (c) pass extracted data as primitives.

2. **Should `_orchestrate` and `_orchestrate_stream_prepare` be fixed in Phase 4 or deferred?**
   - What we know: REVW-05 specifically says "Fix shared DB session bug in existing `run_multi_agent_review`." The orchestrator methods have the same bug.
   - What's unclear: Whether the roadmap intends Phase 4 to be scoped strictly to `run_multi_agent_review` or to all shared-session concurrency bugs.
   - Recommendation: Fix all three sites. The orchestrator bug is identical, the fix is identical, and leaving it creates a ticking time bomb that will surface when users chat with orchestrators while multiple agents are active.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0.2 + pytest-asyncio 0.23.5 |
| Config file | None explicit (pytest discovers via `app/tests/`) |
| Quick run command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/test_pipeline_api.py -x -q` |
| Full suite command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/ -x -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REVW-05 (a) | `run_multi_agent_review` with 3+ agents via `asyncio.gather` produces no `DetachedInstanceError` | unit (mock DB + LLM) | `python -m pytest app/tests/test_session_isolation.py::test_concurrent_review_no_detached_error -x` | Wave 0 |
| REVW-05 (b) | Function accepts `session_factory` callable; each task creates/closes own session | unit (mock factory) | `python -m pytest app/tests/test_session_isolation.py::test_session_factory_creates_separate_sessions -x` | Wave 0 |
| REVW-05 (c) | Existing callers pass session_factory correctly; existing tests still pass | integration (full suite) | `python -m pytest app/tests/ -x -q` | Existing tests |

### Sampling Rate
- **Per task commit:** `python -m pytest app/tests/test_session_isolation.py -x -q`
- **Per wave merge:** `python -m pytest app/tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `app/tests/test_session_isolation.py` -- covers REVW-05 (concurrent session safety tests)
- [ ] No framework install needed (pytest-asyncio already in requirements.txt)
- [ ] No conftest changes needed (existing fixtures sufficient for mock-based tests)

## Sources

### Primary (HIGH confidence)
- [SQLAlchemy 2.0 Session Basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html) - "Session per thread, AsyncSession per task" concurrency model
- [SQLAlchemy 2.0 Async I/O docs](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) - Session isolation requirements for asyncio.gather
- Codebase audit: `backend/app/services/agent_service.py` lines 1027-1063 (`run_multi_agent_review`), 640-660 (`_orchestrate_stream_prepare`), 834-854 (`_orchestrate`) -- three `asyncio.gather` sites sharing `db: Session`
- Codebase audit: `backend/app/db.py` -- `SessionLocal` is the existing `sessionmaker` factory

### Secondary (MEDIUM confidence)
- [SQLAlchemy Discussion #9312](https://github.com/sqlalchemy/sqlalchemy/discussions/9312) - Community discussion confirming per-task session for gather

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new dependencies; existing `SessionLocal` is the factory
- Architecture: HIGH - Pattern is documented by SQLAlchemy and already used in `chat.py` line 216 for stream finalization
- Pitfalls: HIGH - Cross-session lazy loading is the main risk; auditable in Plan 04-01

**Research date:** 2026-03-11
**Valid until:** 2026-06-11 (stable pattern; SQLAlchemy 2.0 session model is mature)
