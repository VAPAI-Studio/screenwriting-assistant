---
phase: 55-mcp-foundation-mount-auth-lifespan-client-spike
plan: 02
completed: 2026-06-12
status: complete
requirements: [MCPF-01, MCPF-02, MCPF-03, MCPF-04]
---

# Phase 55 Plan 02 Summary: mcp_server/ module, mount, lifespan, middleware exemption

Stood up the MCP server mounted in-process at `/mcp` over Streamable HTTP, with
auth reusing the v5.0 gateway, lifespan composed, and `/mcp` exempt from the
BaseHTTPMiddleware stack.

## What was built
- `backend/app/mcp_server/` (renamed from `mcp/` — D-55-D, avoids shadowing the
  `mcp` SDK): `__init__.py`, `session.py` (`mcp_session()` per-call DB ctx mgr),
  `auth.py` (`ApiKeyTokenVerifier` 401 gate via `validate_token`; `require_user`
  reads the inbound Authorization header fresh and calls `authenticate_token`),
  `server.py` (FastMCP instance with `token_verifier`+`AuthSettings`,
  `streamable_http_path="/"`, `json_response=True`, `stateless_http=True`,
  `transport_security` with DNS-rebinding protection off by default; `ping` +
  `whoami` tools; `mcp_app = mcp.streamable_http_app()`).
- `backend/app/main.py`: composed `lifespan` running the mounted MCP sub-app's
  own lifespan (`mcp_app.router.lifespan_context`) + `init_db()`; migrated off
  `@app.on_event`; `app.mount("/mcp", mcp_app)`; `SKIP_MCP_LIFESPAN` test flag.
- `backend/app/middleware.py`: `/mcp` short-circuit at the top of all five
  BaseHTTPMiddleware `dispatch` methods.
- `backend/app/tests/test_mcp_foundation.py`: one consolidated integration test
  (single lifespan entry) proving MCPF-01/02/03/04 over the mounted /mcp.

## Key decisions / findings
- **Trailing slash** `/mcp/` is the live endpoint (D-55-E).
- **DNS-rebinding protection off by default**, env-overridable (D-55-E).
- **Lifespan via the mounted sub-app's own `lifespan_context`** keeps the running
  manager bound to the exact mounted ASGI app (rebuilding it desyncs the mount).
- **SKIP_MCP_LIFESPAN** flag for test isolation (D-55-F): the MCP session
  manager is single-use, so REST tests skip it; production never sets it.

## Verification
- `test_mcp_foundation.py` — 1 passed (initialize + tools/list + whoami owner +
  request_count increment + missing-bearer reject, all over /mcp).
- `test_api.py` + `test_mcp_foundation.py` together — 19 passed (no REST
  regression; middleware/lifespan/mount edits safe).
- Full suite — 377 passed; only the 4 pre-existing order-sensitive
  `test_yolo_integration.py` flakes fail (D-55-G), unrelated to v8.0.

## Test harness used
Official `mcp` SDK `streamable_http_client(url, http_client=...)` over an
`httpx.ASGITransport(app=app)` — no live server. App lifespan entered manually
in the test (ASGITransport doesn't run lifespan); single entry because
`StreamableHTTPSessionManager.run()` is single-use.
