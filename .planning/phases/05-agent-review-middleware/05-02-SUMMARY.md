---
phase: 05-agent-review-middleware
plan: 02
status: complete
started: 2026-03-11
completed: 2026-03-11
duration: 4min
tasks_completed: 2
tasks_total: 2
---

# Plan 05-02 Summary: AI Merge with Schema Validation

## What was built

Replaced the stub merge in `agent_review_middleware.py` with a real AI merge call that synthesizes multiple agent reviews into refined output matching wizard result JSON schemas.

## Key additions

- **WIZARD_RESULT_SCHEMAS**: Maps idea_wizard, scene_wizard, script_writer_wizard to expected top-level keys and schema descriptions
- **MERGE_SYSTEM_PROMPT**: Conflict-resolution rules (most specific/actionable wins, no blending)
- **_merge_reviews()**: AI merge call with json_mode=True, temperature=0.3, schema validation on top-level key
- **_summarize_feedback()**: Builds concise summary strings from agent feedback for agents_consulted metadata

## Requirements covered

- **REVW-03**: AI merge with conflict-resolution and schema validation
- **REVW-01** (partial, finalized): agents_consulted with contribution summaries complete; injection into wizards.py deferred to Phase 6

## Key files

### Modified
- `backend/app/services/agent_review_middleware.py` — Added merge logic, schemas, prompt (now ~340 lines)
- `backend/app/tests/test_agent_review_middleware.py` — 5 new tests + updated 3 existing tests for merge pattern (now ~380 lines)

## Test results

- 10/10 middleware tests pass (5 from 05-01 + 5 from 05-02)
- 61/61 full suite passes (zero regressions)

## Decisions

- Schema validation checks top-level key only (not deep structure) — sufficient for catching wrong schema
- Merge temperature=0.3 for more deterministic output
- When schema validation fails, falls back to raw_output with review_applied=False (safe degradation)
- Unknown wizard types skip schema validation (no WIZARD_RESULT_SCHEMAS entry)

## Self-Check: PASSED

- [x] All tasks executed
- [x] Each task committed individually (2 commits)
- [x] Tests pass
- [x] No regressions
- [x] Stub merge fully replaced
