# Phase 55 Context: MCP Foundation — Mount, Auth, Lifespan & Client Spike

**Phase:** 55
**Captured:** 2026-06-12
**Milestone:** v8.0 — MCP Server

## Domain

Stand up the foundation for the v8.0 MCP server: a remote Streamable HTTP MCP server mounted **in-process** on the existing FastAPI app at `/mcp`, authenticated by the existing v5.0 `sa_<key>` API-key gateway (per-key identity, usage accounting, rate limiting carried through), with a `whoami`/`ping` tool and a static-bearer client-compatibility spike. This is the highest-stakes phase of the milestone — it carries the integration pitfalls (auth bypass, middleware/streaming conflict, lifespan composition) and the GO/NO-GO client gate. Every later tool phase depends on it.

Requirements: MCPF-01, MCPF-02, MCPF-03, MCPF-04, MCPF-05.

## Decisions

### Key identity for MCP (user-decided 2026-06-12)

- **MCP clients use the SAME v5.0 `sa_<key>` API keys** — no separate key type, no new issuance flow. A user creates a key at `/settings/api-keys` and pastes the same `sa_<key>` into their MCP client (Claude Code/Desktop/Hermes). The MCP auth path reuses the v5.0 gateway verbatim (prefix + SHA-256 lookup, scopes column, expiry, per-key rate limit, `request_count`/`last_used_at` accounting).
  - **Why:** zero new auth surface; the whole point of v8.0 reusing v5.0. Keeps MCPF-02/03/04 a thin reuse, not a rebuild.
- **A valid key grants access to ALL tools** (always owner-scoped to that key's user). The key's `scopes` column is NOT enforced per-tool in v8.0 — a valid, non-expired, active key owned by the user can call any exposed tool, and every tool is filtered to that user's own projects/shows (MCPF-04).
  - **Why:** simplest path to MVP; per-tool scope enforcement (e.g. read-only keys) is deferred to v8.1 if a real need emerges. Avoids designing a scope→permission map now.
  - **Deferred:** scope-to-tool permission mapping (read/write/generate scopes gating which tools a key may call) → v8.1.

### Locked by research + roadmap (NOT re-litigated — carried into planning)

These are settled in `.planning/research/v8.0/` (SUMMARY/STACK/ARCHITECTURE/PITFALLS) and the ROADMAP Phase 55 detail. The planner must honor them:

- **Mount in-process** via `app.mount("/mcp", mcp_app)` on the existing FastAPI app (mirror the existing `app.mount("/media", ...)` pattern in `main.py:116`). NOT a separate Docker service/process.
- **Exempt `/mcp` from the `BaseHTTPMiddleware` stack** (`ApiKeyRateLimitMiddleware`, `RateLimitMiddleware`, `RequestSizeLimitMiddleware`, `SecurityMiddleware`, `LoggingMiddleware` — `main.py:54-58`) because `BaseHTTPMiddleware` buffers responses with no backpressure and breaks Streamable HTTP. The MCP auth hook becomes the single rate-limit + request_count authority for `/mcp` (avoid double-counting).
- **Compose the MCP session-manager lifespan into the app lifespan** — and migrate the existing `@app.on_event("startup")` `init_db()` (`main.py:122-127`) into a combined `lifespan` context manager, or the Streamable HTTP session manager's task group never starts (`RuntimeError: Task group is not initialized`).
- **Extract `authenticate_token(token, db)` out of `get_current_user`** (`api/dependencies.py:19-80`) as a shared core, and **move the atomic `request_count` / `last_used_at` increment into it** so MCP calls are both authenticated AND counted. The `sa_` lookup + increment currently lives inline in `get_current_user` — refactor it behavior-preserving so REST keeps working unchanged.
- **Read the inbound `Authorization` header fresh per MCP tool call** (via the SDK's header accessor) — do NOT cache the resolved user across calls (stale per-session request-context bug).
- **Transport is Streamable HTTP only** — do not expose a deprecated `/sse` endpoint.

### Spike (GO/NO-GO gate) — planner must front-load this

- **Library pin is an open spike decision:** STACK.md recommends the official `mcp` SDK (`mcp>=1.27.2,<2.0`, bundles FastMCP v1 in `mcp.server.fastmcp`); ARCHITECTURE.md recommends standalone `fastmcp` for better `get_http_headers()` / `http_app(path=...)` / lifespan-composition ergonomics. **Decide at scaffold time** against the concrete needs: inbound-header access inside tools, sub-path mounting, lifespan composition into the parent app, custom token verification, and a single resolved Starlette version alongside FastAPI. Pin exact import paths once chosen.
- **Static-bearer client compatibility is the GO/NO-GO gate for the whole milestone** — verify a `Authorization: Bearer sa_<key>` static header round-trips `initialize` + tool-list + one tool call from the real clients BEFORE any tool work. Claude Code (`claude mcp add --transport http <name> <url> --header "Authorization: Bearer sa_<key>"`) and Claude Desktop are research-confirmed to accept static headers. Hermes is unverified.
- **If Hermes does NOT support a static header:** v8.0 still ships for the Claude clients; Hermes support (OAuth shim or `mcp-remote` proxy) is deferred to v8.1 — NOT a milestone blocker (MCPF-05).

## Code Context

Reusable assets / integration points verified in the codebase:

- `backend/app/api/dependencies.py:19-80` — `get_current_user`; the `sa_`-key branch (lines ~30-67) does the SHA-256 lookup, expiry check, atomic `request_count`+`last_used_at` increment, and user resolution. **This is the logic to extract into `authenticate_token(token, db)`.**
- `backend/app/main.py:38` — `FastAPI(...)` app construction; `:54-58` the `BaseHTTPMiddleware` stack to exempt; `:116` the `app.mount("/media", StaticFiles(...))` pattern to mirror for `/mcp`; `:122-127` the `@app.on_event("startup")` `init_db()` to migrate into `lifespan`.
- `backend/app/db.py` — `init_db`, `get_db`, `SessionLocal` (sync SQLAlchemy). MCP tool handlers need a per-call session via a new `mcp_session()` context manager wrapping `SessionLocal` (not `Depends`).
- `backend/app/models/database.py` — `ApiKey` (key_hash, scopes, expires_at, is_active, request_count, last_used_at, user_id), `User`.
- v5.0 gateway: `api_keys` table + `ApiKeyRateLimitMiddleware` (default 1000 req/hr) — reuse, do not reinvent.
- `mock-token` works in `development` ENVIRONMENT — useful for local MCP smoke tests without minting a real key (but the spike must also prove a real `sa_<key>`).
- Local runtime: backend on host `8001` → container `8000` (via `docker-compose.override.yml`), frontend `5173`, db `5432`. MCP endpoint reachable at `http://localhost:8001/mcp` locally.

## Canonical Refs

- `.planning/research/v8.0/SUMMARY.md` — synthesized research; the authoritative cross-cutting decisions (MUST read before planning).
- `.planning/research/v8.0/STACK.md` — library/version + static-bearer verdict + FastAPI mount/lifespan wiring.
- `.planning/research/v8.0/ARCHITECTURE.md` — mount model, `authenticate_token` extraction, `mcp_session()`, build order, lifespan-composition gotcha (#1367).
- `.planning/research/v8.0/PITFALLS.md` — Pitfalls 1-4 all resolve in this phase; detection + prevention per pitfall.
- `.planning/ROADMAP.md` — Phase 55 detail (goal, constraints, success criteria).
- `.planning/REQUIREMENTS.md` — MCPF-01..05.
- `backend/app/api/dependencies.py`, `backend/app/main.py`, `backend/app/db.py` — the files being modified.

## Deferred Ideas

- **Per-tool scope enforcement** (key `scopes` gating which tools a key may call — e.g. read-only keys) → v8.1, only if a real need emerges.
- **Hermes static-header fallback** (OAuth shim or `mcp-remote` proxy) → v8.1, only if the Phase-55 spike shows Hermes can't do static headers.
- **Multi-worker rate limiting** (the in-memory per-key limiter is per-process) → revisit only if scaled beyond a single uvicorn worker.
