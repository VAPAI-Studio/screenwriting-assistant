"""MCP authentication — reuses the v5.0 sa_<key> gateway.

Two pieces:

1. ApiKeyTokenVerifier — the MCP SDK's transport-level gate. It returns None to
   make the SDK respond 401, or an AccessToken to allow the request through to
   tool dispatch. It does a NON-incrementing validity check (the request_count
   increment happens once, in require_user, so a single tool call counts once).

2. require_user — called inside each tool. It reads the inbound Authorization
   header FRESH (never cached across calls), then delegates to the shared
   authenticate_token core, which performs the atomic request_count /
   last_used_at increment and resolves the owning user.
"""

from typing import Mapping, Optional

from mcp.server.auth.provider import AccessToken, TokenVerifier
from fastapi import HTTPException

from ..api.dependencies import authenticate_token, validate_token
from ..models import schemas
from .session import mcp_session


class ApiKeyTokenVerifier(TokenVerifier):
    """SDK 401 gate: validate the bearer without side effects (no increment)."""

    async def verify_token(self, token: str) -> Optional[AccessToken]:
        try:
            with mcp_session() as db:
                client_id = validate_token(token, db)
        except Exception:
            return None
        if client_id is None:
            return None
        # scopes intentionally empty: in v8.0 a valid key grants all tools
        # (per-tool scope enforcement deferred to v8.1). Owner-scoping happens
        # in require_user via the resolved user.
        return AccessToken(token=token, client_id=client_id, scopes=[])


def require_user(headers: Mapping[str, str], db) -> schemas.User:
    """Resolve the authenticated user from the inbound Authorization header.

    Reads the header fresh per call (no caching). Delegates to the shared
    authenticate_token core, which performs the request_count increment for
    sa_ keys. Raises HTTPException(401) on a missing/malformed/invalid header.
    """
    auth = ""
    # Mapping may be case-sensitive (Starlette Headers is case-insensitive, but
    # a plain dict is not) — check both common cases.
    for key in ("authorization", "Authorization"):
        if key in headers:
            auth = headers.get(key) or ""
            break
    if not auth:
        # Starlette Headers supports .get with case-insensitivity
        try:
            auth = headers.get("authorization", "") or ""
        except Exception:
            auth = ""

    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    token = auth[len("bearer "):].strip()
    return authenticate_token(token, db)
