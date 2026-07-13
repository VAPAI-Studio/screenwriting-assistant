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
# TokenVerifier; no OAuth server is created. Sourced from settings.MCP_BASE_URL
# (localhost default) so prod can point it at the public host without weakening
# auth.

# DNS-rebinding protection validates the inbound Host header. This is an
# API-key-gated server, so the host allowlist is disabled by default (otherwise
# every client host — localhost, Hermes, test harnesses — would need
# enumerating). Auth is still enforced by the TokenVerifier. On a public host
# set MCP_DNS_REBINDING_PROTECTION=true to harden the now-public surface.
_dns_protect = settings.MCP_DNS_REBINDING_PROTECTION
_transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=_dns_protect,
)

# Injected into connecting agents' system prompts by MCP clients. This is the
# canonical description of the screenplay-production flow — keep it in sync
# with the tool docstrings when tools are added or reordered.
_INSTRUCTIONS = """\
This server IS the studio's screenplay-production pipeline. When asked to
create or work on a screenplay, drive it through these tools at every step
instead of improvising. The canonical flow:

1. ORIENT — project_list shows standalone film projects; show_list +
   episode_list cover TV shows (an episode is a project with a show_id).
   Before writing anything for a show, ALWAYS call show_read_bible and honor
   its characters, world/setting, season arc, and tone & style.
2. CREATE — project_create makes a standalone film project (framework:
   three_act | save_the_cat | hero_journey). Shows, episodes, and season maps
   are created in the web app, not over MCP — never invent them.
3. WRITE — screenplay_write persists the full screenplay text. Give every
   scene an INT./EXT. slugline (each slugline becomes one scene). Writes
   REPLACE all scenes, so to revise one scene: screenplay_read everything,
   edit, then screenplay_write the full text back. screenplay_generate_scene
   returns an AI-crafted PREVIEW of a single scene (continuity + character
   voice); it does not persist — merge the preview via screenplay_write.
   To import an existing screenplay (PDF, Fountain, plain text): extract the
   clean text yourself (drop page numbers / repeated headers, keep sluglines)
   and persist it with screenplay_write — that IS the import path over MCP.
4. BREAKDOWN — once the screenplay is settled, breakdown_extract pulls
   production elements (characters, locations, props, ...); read them with
   breakdown_read (filterable by category). A project's breakdown_stale flag
   means the screenplay changed since the last extraction — re-extract.
5. SHOTLIST — shotlist_generate builds shots from the screenplay (run it
   after the breakdown); shotlist_read lists them grouped by scene;
   shot_create adds manual shots. shotlist_stale mirrors breakdown_stale.

ASYNC JOBS — tools marked LONG-RUNNING return {job_id} immediately. Poll
job_status(job_id) until status is "done" (result holds the output) or
"error". Never assume a long-running tool finished without polling.

RULES — always match scenes by their episode_index field, never by list
position. All tools are owner-scoped to the API key: you only ever see and
touch the key owner's data. There are no delete tools by design.
"""

mcp = FastMCP(
    "screenwriting-assistant",
    instructions=_INSTRUCTIONS,
    token_verifier=ApiKeyTokenVerifier(),
    auth=AuthSettings(
        issuer_url=settings.MCP_BASE_URL,
        resource_server_url=settings.MCP_BASE_URL,
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


# Register tool groups. Imported here (after `mcp` exists) to avoid import cycles.
from .tools import core as _core_tools  # noqa: E402
from .tools import screenwriting as _screenwriting_tools  # noqa: E402
from .tools import management as _management_tools  # noqa: E402
from .tools import breakdown as _breakdown_tools  # noqa: E402
from .tools import shotlist as _shotlist_tools  # noqa: E402

_core_tools.register(mcp)            # generic job_status (Phase 56)
_screenwriting_tools.register(mcp)   # screenplay_generate_scene/read/write (Phase 56/58)
_management_tools.register(mcp)      # project/show/episode tools (Phase 57)
_breakdown_tools.register(mcp)       # breakdown_extract/read (Phase 59)
_shotlist_tools.register(mcp)        # shotlist_read/shot_create/shotlist_generate (Phase 60)


# ASGI app for main.py to mount at /mcp.
mcp_app = mcp.streamable_http_app()
