"""Shared plumbing for MCP tool handlers (v8.0).

Every tool needs: the authenticated user (resolved fresh from the inbound
Authorization header) and a short-lived DB session. resolve_user() centralizes
that so individual tools stay thin.
"""

from mcp.server.fastmcp import Context

from ..models import schemas
from .auth import require_user
from .session import mcp_session


def resolve_user(ctx: Context, db) -> schemas.User:
    """Resolve the authenticated user for an MCP tool call from the inbound
    request headers. Raises HTTPException(401) on a bad/missing token. Owner-
    scoping (MCPF-04) is then done by filtering queries on user.id.
    """
    req = ctx.request_context.request
    return require_user(req.headers, db)


# Re-export for convenience so tools can do `from .context import mcp_session`.
__all__ = ["resolve_user", "mcp_session"]
