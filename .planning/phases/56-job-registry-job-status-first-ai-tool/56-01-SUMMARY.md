---
phase: 56-job-registry-job-status-first-ai-tool
plan: 01
completed: 2026-06-12
status: complete
requirements: [MCPJ-01, MCPJ-02, MCPJ-03]
---

# Phase 56 Summary: Job registry + job_status + first AI tool

## What was built
- `backend/app/mcp_server/jobs.py`: `JobRegistry` — in-memory, asyncio-locked,
  TTL-swept; `create`/`get`(owner-scoped)/`run`(asyncio.create_task background
  runner recording done/error). Module singleton `registry`.
- `backend/app/mcp_server/context.py`: `resolve_user(ctx, db)` shared tool helper.
- `backend/app/mcp_server/tools/core.py`: generic `job_status(job_id)` tool
  (owner-scoped poll → {status, result, error}).
- `backend/app/mcp_server/tools/screenwriting.py`: `screenplay_generate_scene`
  tool — builds regen context in a short DB session, starts a background job
  wrapping the async `regenerate_single_scene` (no DB session held across the AI
  await), returns `{job_id}` immediately.
- `server.py`: registers core + screenwriting tool groups (now 4 tools:
  ping, whoami, job_status, screenplay_generate_scene).
- `backend/app/tests/test_mcp_jobs.py`: 5 tests.

## Verification
- `test_mcp_jobs.py` — 5 passed (run-to-done, error capture, owner-scoping,
  immediate-return-on-slow-work, generate-scene tool returns job then polls done
  with the mocked AI result).
- Concurrency check: 5 concurrent jobs finish in ~0.21s (not 1.0s) — they run in
  parallel; the event loop is not serialized (criterion 4).
- Full suite: 382 passed; only the 4 documented pre-existing flakes
  (test_yolo_integration ×3, test_session_isolation::test_orchestrate_uses_session_factory)
  fail — unchanged by Phase 56.

## Notes
- MCPJ-03 (fast tools synchronous) holds by construction: whoami/ping/job_status
  return directly; only AI generators use the job indirection.
- Multi-worker caveat documented (in-memory = per-worker; single worker assumed).
