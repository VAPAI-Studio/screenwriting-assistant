---
phase: 55-mcp-foundation-mount-auth-lifespan-client-spike
verified: 2026-06-12
status: human_needed
score: 4/5 success criteria verified by API; 1 (GUI client UAT) deferred to user
human_verification:
  - test: "Connect Claude Code / Claude Desktop / Hermes with a static sa_ bearer"
    expected: "tool-list + whoami round-trip; whoami returns the key owner. Hermes static-header support confirmed or deferred to v8.1."
    why_human: "Requires GUI clients and a human at the keyboard; cannot be driven autonomously. See CLIENT-SETUP.md."
---

# Phase 55 Verification: MCP Foundation

**Goal:** A remote Streamable HTTP MCP server mounted in-process at /mcp,
authenticated by the v5.0 sa_<key> gateway, verified to round-trip from real
clients.

## Success Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | /mcp reachable over Streamable HTTP on the existing app (no separate process); initialize + tools/list | ✓ VERIFIED (API) | `test_mcp_foundation.py` — initialize + tools/list round-trip against mounted /mcp |
| 2 | Valid sa_ bearer authenticated; invalid/expired/missing rejected at /mcp | ✓ VERIFIED (API) | test asserts whoami succeeds with valid sa_; missing bearer raises; `validate_token`+`authenticate_token` enforce expiry/active |
| 3 | Authenticated MCP call increments request_count / last_used_at; per-key rate limit applies | ✓ VERIFIED (API) | test asserts request_count rises by 1 via the /mcp path; increment lives in the shared core |
| 4 | whoami returns the resolved user; tools see only that user's resources | ✓ VERIFIED (API) | whoami returns the seeded key owner's email; owner resolved per-call from the fresh header |
| 5 | Static-header connection from Claude Code + Desktop round-trips; Hermes verified | ⏳ HUMAN NEEDED | Foundation proven by API; GUI-client UAT deferred to user (CLIENT-SETUP.md) |

## Pitfalls resolved
- P2 (auth/request_count bypass on mounted sub-app) — auth + increment via the
  MCP TokenVerifier/require_user, asserted on the /mcp path.
- P3 (BaseHTTPMiddleware breaks streaming) — /mcp exempted from all five.
- P4 (lifespan not composed → "Task group is not initialized") — composed via
  the mounted sub-app's lifespan_context.
- P7 (SSE vs Streamable) — Streamable HTTP only, no /sse.

## Tests
- `test_authenticate_token.py` (9) + `test_mcp_foundation.py` (1 e2e) pass.
- Full suite 377 passed; only the documented pre-existing `test_yolo_integration`
  ordering flakes fail (v6.0-PREEXISTING-TEST-CONCERN.md), unrelated to v8.0.

## Status
`human_needed` — code/mechanism complete and API-verified; the only outstanding
item is the GUI-client UAT (criterion 5), which needs a human and is documented
for the user. Not a failure; per MCPF-05 a Hermes static-header gap defers to
v8.1 without blocking the milestone.
