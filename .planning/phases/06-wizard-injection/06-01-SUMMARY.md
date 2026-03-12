---
phase: 06-wizard-injection
plan: 01
subsystem: api
tags: [fastapi, middleware, pydantic, agent-review, wizard]

# Dependency graph
requires:
  - phase: 05-agent-review-middleware
    provides: "AgentReviewMiddleware with review_step_output() entry point, parallel fan-out, AI merge, and pass-through"
provides:
  - "Middleware injection in run_wizard() between wizard_generate() and DB write"
  - "WizardRunResponse.agents_consulted field with model_validator extraction from result._meta"
  - "Integration test suite proving injection, metadata propagation, and pass-through"
affects: [08-yolo-integration, 07-frontend-pipeline-tree]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Middleware injection pattern: single review_step_output() call between generation and DB write"
    - "Metadata propagation via result JSON _meta key with Pydantic model_validator extraction"

key-files:
  created:
    - "backend/app/tests/test_wizard_injection.py"
  modified:
    - "backend/app/api/endpoints/wizards.py"
    - "backend/app/models/schemas.py"

key-decisions:
  - "Embed agents_consulted in result JSON under _meta key rather than adding new DB column -- avoids migration for v1"
  - "Pass SessionLocal factory (not db session) to middleware for parallel session safety"
  - "Use model_validator(mode='after') to extract agents_consulted from _meta for convenient top-level access"

patterns-established:
  - "Middleware injection: insert review_step_output() between wizard_generate() return and wizard_run.result assignment"
  - "Metadata embedding: result['_meta'] carries system metadata that apply_wizard_result_to_db safely ignores"

requirements-completed: [REVW-01]

# Metrics
duration: 3min
completed: 2026-03-12
---

# Phase 6 Plan 1: Wizard Injection Summary

**AgentReviewMiddleware injected into run_wizard() with _meta.agents_consulted propagation and model_validator extraction on WizardRunResponse**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-12T02:57:31Z
- **Completed:** 2026-03-12T03:00:22Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Wired `review_step_output()` call in `run_wizard()` between `wizard_generate()` and DB write, completing REVW-01
- Added `agents_consulted` field to `WizardRunResponse` with `model_validator` that extracts from `result._meta`
- Created 3 integration tests covering injection with mapped agents, schema extraction, and zero-agent pass-through
- All 64 tests pass (3 new injection + 10 existing middleware + 51 other)

## Task Commits

Each task was committed atomically:

1. **Task 1: Schema update and test scaffold (TDD RED)** - `b63bc93` (test)
   - TDD GREEN implementation: `67194d2` (feat)
2. **Task 2: Inject middleware into wizards.py** - `3a40864` (feat)

## Files Created/Modified
- `backend/app/tests/test_wizard_injection.py` - 3 integration tests for injection, schema extraction, and pass-through (185 lines)
- `backend/app/api/endpoints/wizards.py` - Added SessionLocal/middleware imports and review_step_output() call with _meta embedding
- `backend/app/models/schemas.py` - Added agents_consulted field and model_validator to WizardRunResponse

## Decisions Made
- Embed agents_consulted in result JSON under `_meta` key rather than adding a new DB column -- avoids migration for v1, `apply_wizard_result_to_db` safely ignores unknown keys
- Pass `SessionLocal` factory (not `db` session) to middleware for parallel session safety -- same pattern as `chat.py` line 163
- Use `model_validator(mode="after")` to extract `agents_consulted` from `_meta` for convenient top-level access on the response schema

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 7 (Frontend Pipeline Tree) can proceed -- depends on Phase 3 which is complete
- Phase 8 (YOLO Integration) can proceed -- depends on Phase 6 which is now complete
- The middleware injection is transparent: zero-agent pass-through adds zero overhead

## Self-Check: PASSED

All files exist, all commits verified.

---
*Phase: 06-wizard-injection*
*Completed: 2026-03-12*
