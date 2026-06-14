# Stack Research

**Domain:** Remote Streamable HTTP MCP server mounted inside an existing FastAPI/Python 3.11 app, authenticated by the app's existing v5.0 API-key gateway (static `sa_<key>` bearer tokens)
**Researched:** 2026-06-11
**Confidence:** HIGH

## TL;DR Verdict (read this first)

1. **Library:** Use the **official Python `mcp` SDK** (which bundles `FastMCP` v1 as `mcp.server.fastmcp.FastMCP`). Do NOT add the third-party standalone `fastmcp` (jlowin/PrefectHQ) package, and do NOT add `fastapi-mcp` (auto-generates tools from routes — wrong fit; we want curated, AI-aware tools). One new dependency: `mcp>=1.27.2`.

2. **Transport:** Streamable HTTP, the current production transport (SSE is deprecated). The SDK exposes it as an ASGI sub-app via `mcp.streamable_http_app()`, mounted into the existing FastAPI app with `app.mount("/mcp", ...)` and the MCP session manager driven from the FastAPI **lifespan**.

3. **Static bearer auth — VIABLE, confirmed.** The SDK's auth is a **`TokenVerifier` protocol** — OAuth is *optional*, not required. You implement a `verify_token(token)` that runs the existing v5.0 API-key check (SHA-256 prefix/hash lookup, scopes, expiry, rate limit). **No OAuth Authorization Server needed.** On the client side, **Claude Code and Claude Desktop both accept a static `Authorization: Bearer sa_<key>` header** for remote HTTP MCP servers (`claude mcp add --transport http <name> <url> --header "Authorization: Bearer sa_<key>"`). Hermes is an HTTP client and can set the same header.

4. **What NOT to add:** No OAuth 2.1 server, no `authlib`, no separate identity provider, no `fastapi-mcp`, no standalone `fastmcp`. The only caveat is **claude.ai web** (the browser connector UI) which currently only does OAuth and cannot set a static header — but that client is **out of scope** for this milestone (consumers are Claude Desktop, Claude Code, Hermes).

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `mcp` (official Python SDK) | **>=1.27.2** (latest 1.x, released 2026-05-29; pin `~=1.27`) | MCP server primitives: `FastMCP` server, tool registration/JSON-schema generation, Streamable HTTP transport, `TokenVerifier` auth hook | The reference implementation maintained by the MCP project itself (`modelcontextprotocol/python-sdk`). Tracks the spec, ships the Streamable HTTP transport, and — critically — its auth layer is a pluggable `TokenVerifier` protocol that does **not** require OAuth. Bundles `FastMCP` v1 in-tree (`mcp.server.fastmcp`), so no extra package. `1.27.x` includes the host-header-validation security hardening for non-loopback servers. |
| FastAPI / Starlette (existing) | already in app | Host ASGI app; mounts the MCP ASGI sub-app and runs its session manager via lifespan | Already the app's web layer. The MCP SDK's `streamable_http_app()` returns a Starlette app, which mounts cleanly into FastAPI (FastAPI *is* Starlette). No new web framework. |
| Uvicorn (existing) | already in app | ASGI server | Already serving the app. Streamable HTTP is plain HTTP POST + optional SSE response stream — Uvicorn handles it with no extra config. |
| v5.0 API-key gateway (existing) | in-repo | Token verification + per-key identity + rate limiting behind the MCP `TokenVerifier` | Requirement: reuse, don't reinvent. The `verify_token` implementation calls the existing key-hash lookup / scope / expiry / rate-limit code path. Zero new auth dependencies. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pydantic` (existing v2) | already in app | Tool input/output schemas — `FastMCP` derives JSON Schema for tool discovery from type hints / Pydantic models | Already a core dep. Reuse existing Pydantic v2 schemas (`models/schemas.py`) as MCP tool argument/return models so introspection matches the REST contract. **No new install.** |
| `anyio` | transitive via `mcp` | Async task/session management used by the SDK's session manager | Pulled in automatically; do not pin separately. |
| `starlette` | transitive via FastAPI + `mcp` | ASGI mounting + the `streamable_http_app()` return type | Already present via FastAPI; ensure one resolved version (see Version Compatibility). |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| MCP Inspector (`npx @modelcontextprotocol/inspector`) | Local introspection/testing of the running Streamable HTTP server (list tools, call tools, set Authorization header) | Fastest way to validate tool discovery + static-bearer auth before wiring real Claude clients. Point it at `http://localhost:8000/mcp` with header `Authorization: Bearer sa_<key>`. |
| `claude mcp add --transport http` | Register the server in Claude Code for end-to-end UAT | `claude mcp add --transport http screenwriting http://localhost:8000/mcp --header "Authorization: Bearer sa_<key>"` |
| Existing `pytest` suite | Test `verify_token` (valid/expired/over-rate-limit/bad-scope keys) and tool handlers directly | Reuse `Bearer mock-token` convention for happy-path tests; add negative-auth cases. |

## Installation

```bash
# Backend (add to backend/requirements.txt) — ONE new runtime dependency
pip install "mcp>=1.27.2,<2.0"

# Everything else (FastAPI, Starlette, Uvicorn, Pydantic v2, anyio) is already present.

# Dev / verification only (Node, not a Python dep):
npx @modelcontextprotocol/inspector
```

`requirements.txt` line:
```
mcp>=1.27.2,<2.0
```

> Pin `<2.0`: MCP SDK **v2** is in alpha (`2.0.0aN` on PyPI) with a targeted beta 2026-06-30 and stable 2026-07-27. v2 reworks APIs; stay on the stable 1.27.x line for this milestone and treat v2 as a future migration, not a v8.0 concern.

## Integration Approach (concrete — for the phase planner)

**Mount path:** `POST/GET /mcp` on the existing FastAPI app (single Streamable HTTP endpoint; client→server POST and server→client SSE share it).

**Wiring shape (illustrative, not final code):**

```python
import contextlib
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.provider import TokenVerifier, AccessToken

# 1. Static-bearer verifier backed by the v5.0 gateway
class ApiKeyTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        record = await verify_api_key(token)          # existing v5.0 logic: prefix+SHA-256 lookup, expiry, scopes
        if record is None or not record.within_rate_limit():
            return None                                # -> SDK returns 401
        return AccessToken(token=token, client_id=record.key_prefix, scopes=record.scopes)

mcp = FastMCP("screenwriting-assistant", token_verifier=ApiKeyTokenVerifier())

@mcp.tool()
async def generate_scene(project_id: int, scene_index: int) -> dict:
    ...  # delegate to existing template_ai_service / wizards

# 2. Drive the MCP session manager from FastAPI's lifespan
@contextlib.asynccontextmanager
async def lifespan(app):
    async with mcp.session_manager.run():
        yield

app = FastAPI(lifespan=lifespan, ...)      # existing app, lifespan extended
app.mount("/mcp", mcp.streamable_http_app())
```

**Key integration facts the planner must respect:**

- **Lifespan is mandatory.** The Streamable HTTP session manager must be started/stopped via the app lifespan (`mcp.session_manager.run()`), or tool calls fail at runtime. The app already has middleware/lifespan plumbing in `main.py` — extend it, don't replace it.
- **`json_response=True`** can be set on `FastMCP` to return plain JSON responses (no SSE) for the simple request/response tools here — simpler for Hermes and easier to debug. SSE streaming is only needed for long-running/streamed tool output; most tools are request/response.
- **Auth runs inside the MCP transport**, via `TokenVerifier`, NOT via the app's existing global API-key middleware. Mount the MCP sub-app so the global middleware does not double-auth or 401 the MCP handshake. Two clean options: (a) let the MCP `TokenVerifier` be the sole authority for `/mcp` and exempt `/mcp` from the global middleware, or (b) have the global middleware pass through and the verifier re-validate. Recommend (a) — single source of truth, no double rate-limit decrement.
- **Rate-limit accounting:** the existing per-key atomic increment should fire once per MCP request inside `verify_token`. Confirm the increment isn't also charged by the global middleware (tie-in with the exemption above) to avoid double-counting one MCP call.

## The Static-Bearer-vs-OAuth Question (definitive answer + fallback)

**Question:** Hosted/remote MCP conventionally expects OAuth bearer tokens. Can we use the app's static `sa_<key>` instead?

**Answer: YES — on both server and client, for the in-scope consumers.**

**Server side (HIGH confidence — official SDK docs):** The SDK's auth is the `TokenVerifier` protocol. OAuth (Authorization Server metadata, `/register`, token exchange) is an *optional* layer you opt into. A bare `verify_token(token) -> AccessToken | None` is fully supported — the SDK validates "tokens issued by separate Authorization Servers" but the verification logic is entirely yours, so a static API key check is legitimate. No OAuth server required.

**Client side (HIGH confidence — Claude Code docs; MEDIUM for Desktop parity):**
- **Claude Code:** explicitly supports static headers — `claude mcp add --transport http <name> <url> --header "Authorization: Bearer sa_<key>"`, and the JSON form `{"type":"http","url":"...","headers":{"Authorization":"Bearer sa_<key>"}}` in `.mcp.json` / `~/.claude.json`. (`type: "streamable-http"` is accepted as an alias for `http`.) Confirmed in official Claude Code MCP docs.
- **Claude Desktop:** supports the same remote-HTTP-with-headers config form. (Desktop and Code share the remote MCP config model.)
- **Hermes:** a generic HTTP MCP client — sets the `Authorization` header directly. No constraint.

**Known limitation (out of scope, but record it):** **claude.ai web** (the browser "custom connector" UI) currently exposes only OAuth client-id/secret and has **no field for a static bearer/custom header** (anthropics/claude-ai-mcp issue #112), plus a reported bug where it completes OAuth but never attaches the token (#155). This client is **not a v8.0 consumer**, so it does not block static-bearer. If browser-connector support is ever required later, that is when an OAuth wrapper would be added — defer it.

**Fallback (only if a future client refuses static bearer):** wrap the same `verify_token` logic in the SDK's OAuth `OAuthAuthorizationServerProvider` / resource-server metadata flow, minting `sa_<key>`-equivalent tokens. This is an additive layer on the identical verification core — **do not build it now.** For v8.0, static bearer is the decision.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Official `mcp` SDK (bundled FastMCP v1) | Standalone `fastmcp` (jlowin / PrefectHQ, "FastMCP 2.x") | If you wanted FastMCP 2's richer server-composition, built-in auth providers, and deployment helpers. Not worth a second, faster-moving dependency here — the official SDK already covers Streamable HTTP + custom `TokenVerifier`, and staying on the official package minimizes spec-drift risk. (Note: `fastmcp` issue #1789 reports gaps setting custom headers from *its client* config — irrelevant to us as a server, but a sign of extra surface area.) |
| Curated `@mcp.tool()` handlers delegating to existing services | `fastapi-mcp` (auto-exposes FastAPI routes as MCP tools) | If you wanted a zero-effort mirror of all REST endpoints. Rejected: we want a *curated, AI-legible* tool surface (good names, descriptions, narrowed schemas) for the blank-page→breakdown flow, not a 1:1 dump of internal CRUD routes. Auto-exposure also leaks endpoint shapes and complicates the static-bearer auth story. |
| Streamable HTTP transport | SSE transport | Never for new work — SSE is deprecated in both the spec and Claude Code docs. Only relevant if a legacy client can't speak Streamable HTTP (none of our consumers). |
| Static `sa_<key>` bearer via `TokenVerifier` | Full OAuth 2.1 Authorization Server | Only if a future consumer (e.g. claude.ai web connector) cannot send a static header. Out of scope for v8.0. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| OAuth 2.1 server / `authlib` / separate IdP | Requirement is to **reuse the v5.0 API-key gateway**. In-scope clients (Claude Code/Desktop, Hermes) all accept static bearer headers, so an Authorization Server is pure overhead and a security-surface increase. | `TokenVerifier.verify_token` calling the existing v5.0 key validation |
| `fastapi-mcp` (auto-route-to-tool) | Produces an un-curated tool surface mirroring internal CRUD; poor AI ergonomics; muddies auth boundary | Hand-written `@mcp.tool()` handlers delegating to existing services |
| Standalone `fastmcp` (jlowin) as a *new* dependency | Second MCP package, faster-moving, overlaps the official SDK; the in-tree `mcp.server.fastmcp` already suffices | Bundled `FastMCP` inside official `mcp` |
| SSE transport | Deprecated in spec + Claude Code | Streamable HTTP |
| `mcp` 2.0.0aN (alpha) | v2 is pre-release (beta targeted 2026-06-30); API churn risk mid-milestone | `mcp>=1.27.2,<2.0` |
| Re-running the global API-key middleware over `/mcp` AND verifying in `TokenVerifier` | Double auth + double rate-limit decrement per MCP call | Exempt `/mcp` from global middleware; let `TokenVerifier` be the single authority |

## Stack Patterns by Variant

**If most tools are simple request/response (the common case here):**
- Set `FastMCP(..., json_response=True)`
- Because plain-JSON responses avoid SSE framing, are easier to debug, and are friendlier to Hermes and curl-style testing.

**If a tool must stream long AI output (e.g. live scene generation):**
- Leave SSE enabled for that path (default Streamable HTTP behavior)
- Because Streamable HTTP can upgrade a single response to an SSE stream; reuse the app's existing streaming generation pattern (breakdown_chat) inside the tool.

**If a future consumer is the claude.ai web connector:**
- Add the SDK's OAuth resource-server layer wrapping the same `verify_token` core
- Because the browser connector UI cannot send a static header today. Defer — not a v8.0 consumer.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `mcp` >=1.27.2 | Python >=3.10 | App is on 3.11 — satisfied. |
| `mcp` >=1.27.2 | Pydantic v2 | SDK targets Pydantic v2 (matches the app). No v1 conflict. |
| `mcp` (depends on `starlette`) | FastAPI's pinned `starlette` | **Verify one resolved `starlette` version** after install — both FastAPI and `mcp` depend on Starlette; let pip resolve and run the app's startup smoke test. Most likely compatible; flag if FastAPI pins an older Starlette than `mcp` requires. |
| `mcp` (depends on `anyio`, `httpx`, `uvicorn`-compatible ASGI) | existing app deps | All already present; `anyio`/`httpx` are common transitive deps — check for version pins in `requirements.txt`. |
| Claude Code config `type: "http"` | `type: "streamable-http"` | Aliases — server docs using `streamable-http` work unmodified in Claude Code. |

## Sources

- `modelcontextprotocol/python-sdk` (GitHub, official) — Streamable HTTP server (`streamable_http_app()`), lifespan/session-manager pattern, `TokenVerifier` protocol (OAuth optional), v1 vs v2 status — **HIGH**
- PyPI `mcp` release metadata — latest **1.27.2** (2026-05-29), 1.27.x line, Python >=3.10, v2 alpha pre-releases — **HIGH**
- Claude Code MCP docs (code.claude.com/docs/en/mcp) — `claude mcp add --transport http ... --header "Authorization: Bearer ..."`, `.mcp.json` `headers` field, `streamable-http` alias, SSE deprecated — **HIGH**
- anthropics/claude-ai-mcp issues #112, #155 — claude.ai **web** connector lacks static-header support (out-of-scope client) — **MEDIUM** (issue tracker, but directly corroborates the limitation)
- FastMCP / community guides (gofastmcp.com bearer auth, Medium FastAPI+MCP walkthroughs) — corroborating mount + bearer patterns; used only to cross-check, not as primary auth authority — **MEDIUM/LOW**

---
*Stack research for: remote Streamable HTTP MCP server on existing FastAPI app with static API-key bearer auth*
*Researched: 2026-06-11*
