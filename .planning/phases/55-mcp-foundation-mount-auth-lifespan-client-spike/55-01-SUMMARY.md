---
phase: 55-mcp-foundation-mount-auth-lifespan-client-spike
plan: 01
completed: 2026-06-12
status: complete
requirements: [MCPF-02, MCPF-03]
---

# Phase 55 Plan 01 Summary: authenticate_token extraction + MCP deps

Extracted the auth logic from `get_current_user` into a shared, `Depends`-free
`authenticate_token(token, db) -> schemas.User` core so REST and MCP share one
source of truth (including the atomic `request_count`/`last_used_at` increment
for sa_ keys). Added a non-incrementing `validate_token(token, db)` helper for
the MCP TokenVerifier gate. Pinned MCP runtime deps.

## What was built
- `backend/app/api/dependencies.py`: `authenticate_token` (the three branches —
  mock-token/sa_/JWT — moved verbatim, raising HTTPException(401) on failure so
  REST behavior is byte-identical); `validate_token` (non-incrementing validity
  check returning a client-id string or None); `get_current_user` is now a thin
  `return authenticate_token(credentials.credentials, db)` wrapper.
- `backend/requirements.txt`: `mcp>=1.27.2,<2.0`, `uvicorn>=0.31.1`,
  `starlette>=0.36.3,<0.37`, `sse-starlette<2.2` (see decision D-55-B2).
- `backend/app/tests/test_authenticate_token.py`: 9 tests covering each branch +
  increment-in-core proof + endpoint delegation.

## Key decisions
- **Kept HTTPException, did NOT introduce AuthException** — the plan suggested
  AuthException, but grep proved it doesn't exist and isn't registered as a
  handler, so raising it would have broken REST 401s. HTTPException is the
  behavior-preserving choice and MCP's TokenVerifier catches it fine.
- Dependency resolution (D-55-B2): pinned starlette/sse-starlette to keep the
  existing starlette 0.36.3 — **no FastAPI bump**.

## Verification
- `pytest test_authenticate_token.py` — 9 passed.
- `pytest test_api_keys.py` — 15 passed (REST auth byte-identical).
- `mcp 1.27.2` + `uvicorn` import at required floors.
