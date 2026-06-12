---
phase: 55-mcp-foundation-mount-auth-lifespan-client-spike
plan: 03
completed: 2026-06-12
status: complete-with-deferred-uat
requirements: [MCPF-01, MCPF-02, MCPF-03, MCPF-05]
---

# Phase 55 Plan 03 Summary: client spike (GO/NO-GO) + CLIENT-SETUP

## Automated spike — PASSED
The programmatic spike was implemented as `test_mcp_foundation.py` (built in
Plan 02 to keep one lifespan entry). Over a real MCP SDK client against the
mounted `/mcp`, it confirms end-to-end: `initialize` + `tools/list` round-trip,
valid `sa_<key>` static bearer authenticates, `whoami` returns the key owner,
missing bearer rejected, `request_count` increments. **The static-bearer
transport + auth foundation works** — GO at the API level.

## Deferred to USER (GUI clients — `checkpoint:human-verify`)
Cannot be run autonomously (require a human + GUI clients). Documented in
`CLIENT-SETUP.md`:
- [ ] Claude Code: `claude mcp add --transport http screenwriting
  http://localhost:8001/mcp/ --header "Authorization: Bearer sa_<key>"` → whoami.
- [ ] Claude Desktop: remote server config + static header → tools + whoami.
- [ ] Hermes: confirm whether it accepts a static Authorization header (go/no-go
  for native Hermes support; otherwise defer Hermes to v8.1 — not a blocker per
  MCPF-05).

## Deliverable
`CLIENT-SETUP.md` — connection instructions for all three clients, the
trailing-slash requirement, the DNS-rebinding-protection note, and the
pending-user checklist.
