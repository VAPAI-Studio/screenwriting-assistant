# Architecture Research

**Domain:** Remote Streamable HTTP MCP server integrated into an existing FastAPI monolith
**Researched:** 2026-06-11
**Confidence:** HIGH (mount model, auth threading, build order); MEDIUM (specific FastMCP API surface — two competing libraries, see Decision below)

> Scope: This answers *how* an MCP server bolts onto THIS codebase. It does not re-research the existing app (middleware stack, `get_current_user`, services) — those are treated as fixed integration surfaces. Grounded in `backend/app/main.py`, `api/dependencies.py`, `middleware.py`, `db.py`, and the projects/breakdown/shots endpoint+service patterns.

---

## Decision Up Front (the two load-bearing choices)

**1. Mount model: mount the MCP ASGI sub-app INSIDE the existing FastAPI app** (`app.mount("/mcp", mcp_app)`) — NOT a separate Docker service. Rationale below.

**2. MCP library: use `fastmcp` (jlowin/PrefectHQ `fastmcp`, gofastmcp.com), not the bare `mcp.server.fastmcp` from the official `modelcontextprotocol/python-sdk`.** Both expose `FastMCP` and Streamable HTTP, but `fastmcp` ships first-class helpers we need: `get_http_headers()` / `get_http_request()` to read the inbound `Authorization` header inside a tool, cleaner `http_app(path=...)` mounting, and server middleware hooks. The official SDK can mount but makes inbound-header access and sub-path mounting awkward (see Pitfalls). Confidence MEDIUM only because the exact import paths must be pinned at scaffold time against the installed version.

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│  REMOTE MCP CLIENTS                                                    │
│  Claude Desktop / Claude Code (primary) · Hermes (secondary)          │
│  speak MCP over Streamable HTTP, Authorization: Bearer sa_<key>       │
└───────────────────────────────┬──────────────────────────────────────┘
                                 │  HTTPS  POST /mcp  (JSON-RPC framed)
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  FastAPI app (backend, uvicorn :8000)  — UNCHANGED entrypoint         │
│  Middleware stack (outer → inner), runs for /mcp too:                 │
│   ApiKeyRateLimit → RateLimit → RequestSizeLimit → Security → Logging │
│  ┌──────────────────────────┐   ┌────────────────────────────────┐   │
│  │ Existing REST routers     │   │  MOUNTED MCP SUB-APP  /mcp     │   │
│  │ /api/projects, /sections, │   │  (FastMCP ASGI streamable app) │   │
│  │ /breakdown, /shots, ...   │   │  ┌──────────────────────────┐  │   │
│  │  Depends(get_current_user)│   │  │ MCP tool handlers         │  │   │
│  │  Depends(get_db)          │   │  │ (mcp/tools/*.py)          │  │   │
│  └──────────┬───────────────┘   │  │  read Bearer via          │  │   │
│             │                    │  │  get_http_headers()       │  │   │
│             │                    │  │  → authenticate_token()   │  │   │
│             │                    │  │  → open DB session        │  │   │
│             │                    │  └────────────┬─────────────┘  │   │
│             │                    └───────────────┼────────────────┘   │
│             ▼                                     ▼                    │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  SHARED SERVICE LAYER (UNCHANGED)                                │  │
│  │  template_ai_service · breakdown_service · shots logic ·         │  │
│  │  wizards · shows/episodes/bible · screenplay write/split        │  │
│  │  all take (db: Session, ids, payload) — NOT FastAPI Depends      │  │
│  └───────────────────────────────┬────────────────────────────────┘  │
└──────────────────────────────────┼───────────────────────────────────┘
                                    ▼
                       ┌────────────────────────┐
                       │  PostgreSQL (db)        │
                       │  Project→Section→...    │
                       │  ScreenplayContent,     │
                       │  shots, shows, api_keys │
                       └────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `mcp_app` (FastMCP ASGI) | Speaks MCP/JSON-RPC over Streamable HTTP, advertises tool schemas, dispatches to handlers | `FastMCP("...").http_app(path="/")`, mounted at `/mcp` |
| MCP tool handlers (`mcp/tools/*.py`) | Thin adapters: parse args → authenticate → open session → call existing service → shape MCP result | New module; **wrap, never reimplement** services |
| `authenticate_token(token, db)` | Reusable auth core (sa_ key / JWT / mock) returning a `User` | Refactored OUT of `get_current_user` so both REST and MCP share it |
| `mcp_session()` ctx manager | Opens/closes a `SessionLocal()` for the duration of one tool call | New; mirrors `get_db()` but as a plain context manager (no `Depends`) |
| Existing middleware stack | Rate limiting (per-IP + per-key), size limit, security headers, logging — applied to `/mcp` automatically | UNCHANGED (runs because mount is inside the same app) |
| Service layer | All real work (AI generation, extraction, CRUD) | UNCHANGED |

---

## Recommended Project Structure

```
backend/app/
├── main.py                      # MODIFIED: build mcp_app, set lifespan, app.mount("/mcp", mcp_app)
├── mcp/                         # NEW MODULE — the entire MCP surface lives here
│   ├── __init__.py
│   ├── server.py                # FastMCP() instance, http_app(), tool registration wiring
│   ├── auth.py                  # _require_user(): get_http_headers() → authenticate_token() → User
│   ├── session.py               # mcp_session() context manager around SessionLocal
│   ├── errors.py                # map app exceptions → MCP tool errors / structured content
│   └── tools/
│       ├── projects.py          # create/list projects, shows, episodes, bible (mgmt group)
│       ├── screenwriting.py     # read screenplay, generate/regenerate scene, write directly
│       ├── breakdown.py         # trigger extraction, read elements, per-scene appearances
│       └── shotlist.py          # read/create/edit shots, AI-generate shotlist
├── api/dependencies.py          # MODIFIED: factor authenticate_token(token, db) out of get_current_user
├── services/                    # UNCHANGED — wrapped by mcp/tools/*
└── ...
```

### Structure Rationale

- **`mcp/` is a sibling of `api/`, not nested in it.** MCP is a second delivery surface (peer to REST), not another router. Keeping it isolated means the REST app is untouched except `main.py` wiring and one auth refactor.
- **`mcp/tools/` mirrors the REST router grouping** (projects/screenwriting/breakdown/shotlist) so each tool group maps 1:1 to a service area and can be built/tested independently (parallelizable phases).
- **`auth.py` + `session.py` are the only genuinely new infra.** Everything else is glue that calls existing services.

---

## Architectural Patterns

### Pattern 1: Mount-inside-the-app (single process), with lifespan propagation

**What:** Construct the FastMCP ASGI app and mount it on the existing FastAPI instance. The single non-obvious requirement: the MCP app's **lifespan must be handed to the parent FastAPI app**, or the Streamable HTTP session manager's task group is never started and every call fails with `RuntimeError: Task group is not initialized` (confirmed in python-sdk issue #1367).

**When to use:** Whenever the MCP server needs the same DB, auth, and middleware as the REST app — which is exactly this case.

**Trade-offs:**
- (+) Reuses the ENTIRE middleware stack (per-key rate limit, request-count, logging, security) with zero new code — `/mcp` is just another path under the same app.
- (+) Same connection pool / `SessionLocal`, same config, one container, one deploy. No new Docker service, no inter-service auth.
- (+) Per-key rate limiting "just works": `ApiKeyRateLimitMiddleware` already keys off `Authorization: Bearer sa_` regardless of path.
- (−) MCP traffic shares the uvicorn worker pool with REST. Long-running AI tool calls (scene generation) can occupy workers — mitigate with adequate `--workers` / async and, if needed later, a dedicated uvicorn worker count. This is a tuning concern, not an architecture change.
- (−) FastAPI's auto-generated OpenAPI/docs won't describe MCP tools (MCP has its own discovery) — acceptable, they're different protocols.

**Example (main.py wiring — the load-bearing 4 lines):**
```python
# main.py
from contextlib import asynccontextmanager
from .mcp.server import mcp            # FastMCP instance

mcp_app = mcp.http_app(path="/")       # ASGI Streamable HTTP app

# Propagate MCP lifespan into the existing FastAPI app (REQUIRED).
# If FastAPI already has startup logic (init_db), compose both.
@asynccontextmanager
async def lifespan(app):
    async with mcp_app.lifespan(app):   # starts MCP session manager task group
        init_db()
        yield

app = FastAPI(..., lifespan=lifespan)
# ... existing add_middleware(...) calls unchanged ...
app.mount("/mcp", mcp_app)             # clients connect to https://host/mcp
```
> Note: the existing code uses `@app.on_event("startup")` for `init_db()`. Migrating that into the composed `lifespan` is the one structural edit in `main.py` (FastAPI deprecates `on_event` in favor of lifespan anyway).

### Pattern 2: Auth threading — read the header in the tool, reuse the existing auth core

**What:** MCP tool functions are NOT FastAPI route handlers, so `Depends(get_current_user)` cannot run. Instead, each tool reads the inbound HTTP `Authorization` header via FastMCP's `get_http_headers()`, then calls a refactored `authenticate_token(token, db)` that contains the exact sa_/JWT/mock logic already in `get_current_user`.

**When to use:** Every authenticated tool. Implemented once in `mcp/auth.py` and reused.

**Trade-offs:** Requires factoring the auth body out of `get_current_user` so it is callable without `Depends`. Net positive: REST and MCP then share one source of truth for auth (and for the request-count increment).

**Example:**
```python
# api/dependencies.py — REFACTOR (behavior-preserving)
def authenticate_token(token: str, db: Session) -> schemas.User:
    """Pure auth core: mock-token / sa_<key> / JWT → User. Also increments
    api_keys.request_count for sa_ keys (existing behavior, moved here)."""
    ...  # the body currently inside get_current_user, minus Depends plumbing

async def get_current_user(credentials=Depends(security), db=Depends(get_db)):
    return authenticate_token(credentials.credentials, db)   # REST path unchanged
```
```python
# mcp/auth.py — NEW
from fastmcp.server.dependencies import get_http_headers
from ..api.dependencies import authenticate_token
from ..exceptions import AuthException

def require_user(db):
    headers = get_http_headers()                      # inbound request headers
    auth = headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise AuthException("Missing bearer token")
    token = auth.split(" ", 1)[1]
    return authenticate_token(token, db)              # same logic as REST
```

### Pattern 3: Per-tool DB session via context manager (not Depends)

**What:** `get_db()` is a FastAPI dependency generator. Tools open a session explicitly with a context manager that wraps the same `SessionLocal`, scoped to the single tool call.

**Trade-offs:** Slightly more boilerplate per tool than `Depends`, but explicit and correct under Streamable HTTP (where one MCP session may carry many tool calls — you want a fresh DB session per call, not per connection).

**Example — a representative tool (thin wrapper, zero service logic):**
```python
# mcp/tools/screenwriting.py
@mcp.tool()
def generate_scene(project_id: str, section_id: str) -> dict:
    with mcp_session() as db:                         # session.py: SessionLocal()
        user = require_user(db)                       # auth.py
        # authorization check reuses existing ownership rules
        result = template_ai_service.generate_scene(  # EXISTING service, unchanged
            db=db, project_id=UUID(project_id),
            section_id=UUID(section_id), owner_id=user.id,
        )
        db.commit()
        return result.to_mcp()                        # shape → MCP structured content
```

---

## Data Flow

### Representative tool call: "generate a scene"

```
Claude Desktop  ──POST /mcp (JSON-RPC: tools/call generate_scene)──►
  Authorization: Bearer sa_ab12_secret
        │
        ▼  (FastAPI middleware stack runs FIRST, because /mcp is in-app)
  ApiKeyRateLimitMiddleware  → hash sa_ key, check per-key/hour window  (429 if over)
  RateLimitMiddleware        → per-IP/min window                        (429 if over)
  RequestSizeLimit / Security / Logging  → headers, request-id, log line
        │
        ▼  mount routes to mcp_app → FastMCP dispatches tools/call → generate_scene()
  require_user(db):
     get_http_headers() → "Bearer sa_ab12_secret"
     authenticate_token(token, db):
        sa_ branch → sha256 → lookup api_keys (active, unexpired)
        UPDATE api_keys SET request_count+1, last_used_at=now   ← request-count tracking
        → User
        │
        ▼
  template_ai_service.generate_scene(db, project_id, section_id, owner_id)
        → reads ScreenplayContent, prior-scene continuity, voice profiles (v6.0 path)
        → calls AI provider → writes generated scene
        │
        ▼
  db.commit()
        │
        ▼
  result.to_mcp()  → JSON-RPC result (Streamable HTTP frame, possibly chunked)
        │
        ▼
Claude Desktop renders the generated scene
```

**Two things to notice:**
1. The per-key rate limit and the `request_count` increment are hit on the **exact same code paths** as REST — middleware (counting/limiting) + `authenticate_token` (increment). No MCP-specific rate-limit code needed.
2. The service call is byte-for-byte the REST service call. The tool added only: header read, auth, session open/commit, result shaping.

### Rate limiter & request-count reuse (explicit)

| Mechanism | Where it lives today | Applies to MCP? | Action needed |
|-----------|----------------------|-----------------|---------------|
| Per-IP rate limit (600/min) | `RateLimitMiddleware` | YES — `/mcp` is in-app | None |
| Per-API-key rate limit (1000/hr) | `ApiKeyRateLimitMiddleware`, keyed on `Bearer sa_` | YES — keys off header, path-agnostic | None |
| `request_count` + `last_used_at` increment | inside `get_current_user` (sa_ branch) | Only if MCP calls the shared core | **Move increment into `authenticate_token`** so MCP tools increment it too |
| Request size limit / security headers / logging | respective middlewares | YES | None |

> The single required change for billing/usage fidelity is the auth refactor (Pattern 2): the `request_count` increment must live in `authenticate_token`, not in the FastAPI-only wrapper, or MCP calls won't be counted.

---

## Suggested Build Order (phase decomposition for the roadmapper)

Dependencies: **scaffold + auth must land before any tool group.** Tool groups are mutually independent and can parallelize once the foundation exists. Discovery/UAT closes it out.

| # | Phase | Depends on | Parallelizable | New vs Modified |
|---|-------|-----------|----------------|-----------------|
| 1 | **MCP scaffold + mount + lifespan** — add `fastmcp` dep; `mcp/server.py`; mount at `/mcp`; compose lifespan; one trivial unauthenticated `ping` tool proves transport + Claude Desktop connectivity | — | No (foundation) | NEW `mcp/server.py`; MODIFIED `main.py`, `requirements.txt` |
| 2 | **Auth + session threading** — refactor `authenticate_token` out of `get_current_user` (move request_count increment in); `mcp/auth.py` (`require_user`), `mcp/session.py` (`mcp_session`); convert `ping` into an authenticated `whoami` tool returning the resolved user | 1 | No (foundation) | NEW `mcp/auth.py`, `mcp/session.py`; MODIFIED `api/dependencies.py` |
| 3 | **Project/show management tools** — create/list projects, create show/episode, read series bible | 2 | YES | NEW `mcp/tools/projects.py` |
| 4 | **Screenwriting tools** — read screenplay, generate/regenerate scene (v6.0 path), write screenplay directly (Phase 54 path) | 2 | YES | NEW `mcp/tools/screenwriting.py` |
| 5 | **Breakdown tools** — trigger extraction, read elements by category, read per-scene appearances + context (v7.0 output) | 2 | YES | NEW `mcp/tools/breakdown.py` |
| 6 | **Shotlist tools** — read/create/edit shots, AI-generate shotlist | 2 | YES | NEW `mcp/tools/shotlist.py` |
| 7 | **Discovery polish + error mapping + client UAT** — finalize tool schemas/descriptions for generic introspection; `mcp/errors.py` maps app exceptions to MCP errors; end-to-end test from Claude Desktop/Code (and a Hermes smoke test) | 3–6 | No (integration) | NEW `mcp/errors.py`; touch-ups across tools |

> Phases 3–6 each follow the identical adapter pattern (Pattern 3), so they are low-risk and independent — ideal for parallel execution or fast sequential batching. Phase 1 and especially the lifespan wiring carry the only real integration risk.

---

## Integration Points

### New components

| Component | Type | Purpose |
|-----------|------|---------|
| `mcp/server.py` | NEW | FastMCP instance + `http_app()` |
| `mcp/auth.py` | NEW | header → `authenticate_token` → User |
| `mcp/session.py` | NEW | per-call DB session context manager |
| `mcp/errors.py` | NEW | exception → MCP error mapping |
| `mcp/tools/{projects,screenwriting,breakdown,shotlist}.py` | NEW | thin tool adapters over existing services |
| `fastmcp` dependency | NEW | in `requirements.txt` |

### Modified components

| Component | Change | Risk |
|-----------|--------|------|
| `main.py` | Build `mcp_app`, compose lifespan (migrate `init_db` off `on_event`), `app.mount("/mcp", mcp_app)` | MED — lifespan must wrap MCP session manager or all calls fail |
| `api/dependencies.py` | Factor `authenticate_token(token, db)` out of `get_current_user`; move `request_count` increment into it | LOW — behavior-preserving refactor; cover with existing auth tests |

### Unchanged (do NOT touch)

- All `services/*` — wrapped, never reimplemented (quality-gate requirement).
- All middleware — reused as-is for `/mcp`.
- All REST routers and the frontend.

---

## Anti-Patterns

### Anti-Pattern 1: Running MCP as a separate Docker service

**What people do:** Spin up a second container for the MCP server "to keep it isolated."
**Why it's wrong here:** It would need its own DB pool, its own copy/import of auth, and either re-implement or HTTP-call the per-key rate limiter and `request_count` tracking — duplicating the v5.0 gateway. It buys isolation this internal tool doesn't need and costs you the free reuse of the entire middleware stack.
**Do this instead:** Mount in-process (Pattern 1). Revisit only if MCP traffic ever needs independent scaling — not an MVP concern.

### Anti-Pattern 2: Reimplementing service logic inside tool handlers

**What people do:** Inline AI-generation or extraction logic into the tool because "the service signature isn't convenient."
**Why it's wrong:** Forks the v6.0/v7.0 quality logic; the two surfaces drift.
**Do this instead:** If a service signature is awkward, adapt at the boundary (the tool shapes args/results); keep the service authoritative. Services already take `(db, ids, payload)`, which is exactly what a tool can pass.

### Anti-Pattern 3: Forgetting lifespan propagation / mounting at a deep path naively

**What people do:** `app.mount("/mcp", mcp.streamable_http_app())` and nothing else.
**Why it's wrong:** Without composing the MCP app's lifespan into the parent, the session manager task group never starts → `RuntimeError: Task group is not initialized` on the first call (python-sdk #1367). Using `fastmcp`'s `http_app(path="/")` + parent lifespan composition is the supported pattern.
**Do this instead:** Compose lifespans (Pattern 1) and verify connectivity with the Phase-1 `ping` tool before building real tools.

### Anti-Pattern 4: Trusting per-session HTTP request context across calls

**What people do:** Cache the request/headers object at session start and reuse it.
**Why it's wrong:** Documented bug class — under Streamable HTTP with multiple calls in one MCP session, tools can receive **stale** HTTP request context from the first request (jlowin/fastmcp #1233, #596). Caching the auth from call N can leak into call N+1.
**Do this instead:** Call `get_http_headers()` and `authenticate_token()` fresh inside each tool invocation; never cache the resolved user across calls in a session.

---

## Scaling Considerations

| Scale | Adjustments |
|-------|-------------|
| Internal use (handful of clients) | In-process mount, default uvicorn workers. Fine. |
| Many concurrent long AI tool calls | Long generations occupy workers; bump uvicorn `--workers` or run generation as the existing async path. DB pool (`SessionLocal`) sizing may need a bump. |
| If MCP ever needs independent scaling | Only then split to a separate service sharing the same DB + auth library; reuse `authenticate_token` and the api_keys table. Not an MVP concern. |

**First bottleneck:** worker occupancy from synchronous AI tool calls — tune workers/async, not architecture.
**Second bottleneck:** DB connection pool under concurrent tool calls — size the pool.

---

## Sources

- modelcontextprotocol/python-sdk — README (Streamable HTTP, `streamable_http_app()`, `session_manager.run()`, `TokenVerifier`): https://github.com/modelcontextprotocol/python-sdk — HIGH
- python-sdk Issue #1367 — mounting on existing FastAPI fails without lifespan/task-group init: https://github.com/modelcontextprotocol/python-sdk/issues/1367 — HIGH
- python-sdk Issue #750 — getting HTTP request headers in tools under Streamable HTTP: https://github.com/modelcontextprotocol/python-sdk/issues/750 — MEDIUM
- FastMCP (jlowin/PrefectHQ) — FastAPI integration (`http_app(path=...)`, lifespan propagation, `app.mount`): https://gofastmcp.com/integrations/fastapi — HIGH
- FastMCP — server dependencies (`get_http_headers()`, `get_http_request()`): https://gofastmcp.com/python-sdk/fastmcp-server-dependencies — HIGH
- jlowin/fastmcp Issue #1233 / #596 — stale HTTP request context across calls in a session: https://github.com/jlowin/fastmcp/issues/1233 — MEDIUM
- "Mount, Stream, Authenticate FastMCP with FastAPI" (Ekky Armandi, May 2026) — end-to-end mount+auth walkthrough: https://ekky.dev/blog/2026-05-10-fastapi-fastmcp-mount-stream-authenticate — MEDIUM
- Existing codebase (ground truth): `backend/app/main.py`, `api/dependencies.py`, `middleware.py`, `db.py`, projects/breakdown/shots endpoints + services — HIGH

---
*Architecture research for: MCP server integration into existing FastAPI app (v8.0)*
*Researched: 2026-06-11*
