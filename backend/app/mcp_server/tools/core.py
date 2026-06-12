"""Core/cross-cutting MCP tools (v8.0): the generic job_status poller."""

from mcp.server.fastmcp import Context
from fastapi import HTTPException

from ..context import resolve_user, mcp_session
from ..jobs import registry


def register(mcp):
    """Register the generic job_status tool on the given FastMCP instance."""

    @mcp.tool()
    async def job_status(ctx: Context, job_id: str) -> dict:
        """Poll a long-running tool's job by id. Returns {job_id, status, kind,
        result, error}. status is one of: pending, running, done, error. When
        status is "done", `result` holds the finished tool's output. Only the
        job's owner can read it.
        """
        with mcp_session() as db:
            user = resolve_user(ctx, db)
            owner_id = str(user.id)
        job = await registry.get(job_id, owner_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return job.to_dict()
