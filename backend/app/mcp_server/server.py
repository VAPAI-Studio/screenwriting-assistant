"""FastMCP server instance for the screenwriting assistant.

Mounted in-process at /mcp by main.py over Streamable HTTP. Phase 55 exposes
only the transport/auth-proof tools (ping, whoami). Tool groups
(screenwriting / breakdown / shotlist / management) are added in Phases 56-60.
"""

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.auth.settings import AuthSettings
from mcp.server.transport_security import TransportSecuritySettings

from ..config import settings
from .auth import ApiKeyTokenVerifier, require_user
from .session import mcp_session

# Base URL is metadata only — static-bearer verification lives entirely in the
# TokenVerifier; no OAuth server is created. Localhost default is fine for an
# internal tool reached at http://localhost:8001/mcp.
_BASE_URL = "http://localhost:8001"

# DNS-rebinding protection validates the inbound Host header. This is an
# internal, API-key-gated server reached over a trusted network, so the host
# allowlist is disabled by default (otherwise every client host — localhost,
# Hermes, test harnesses — would need enumerating). Auth is still enforced by
# the TokenVerifier. Set MCP_DNS_REBINDING_PROTECTION=true to re-enable.
_dns_protect = str(getattr(settings, "MCP_DNS_REBINDING_PROTECTION", "false")).lower() == "true"
_transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=_dns_protect,
)

mcp = FastMCP(
    "screenwriting-assistant",
    token_verifier=ApiKeyTokenVerifier(),
    auth=AuthSettings(
        issuer_url=_BASE_URL,
        resource_server_url=_BASE_URL,
    ),
    # The app mounts this at /mcp, so the server's own path must be "/" to avoid
    # an effective /mcp/mcp.
    streamable_http_path="/",
    json_response=True,
    stateless_http=True,
    transport_security=_transport_security,
)


@mcp.tool()
def ping() -> dict:
    """Health/transport check — confirms the MCP endpoint is reachable and the
    bearer token was accepted. Returns immediately."""
    return {"status": "ok", "transport": "streamable-http"}


@mcp.tool()
def whoami(ctx: Context) -> dict:
    """Return the authenticated user resolved from the API key. Proves the
    request is owner-scoped — a tool only ever acts as the key's owner."""
    req = ctx.request_context.request
    with mcp_session() as db:
        user = require_user(req.headers, db)
        return {
            "user_id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
        }


# ASGI app for main.py to mount at /mcp.
mcp_app = mcp.streamable_http_app()
