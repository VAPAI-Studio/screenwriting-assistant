---
phase: 02-pipeline-composer-service
plan: 02
subsystem: api
tags: [cache, sha256, semantic-change, determinism, testing, pipeline]

# Dependency graph
requires:
  - phase: 02-pipeline-composer-service
    provides: PipelineComposer with _compute_cache_key(), is_semantic_change(), SEMANTIC_FIELDS, compose_pipeline() with cache check
provides:
  - 3 COMP-03 unit tests verifying cache determinism, cosmetic no-recompose, and semantic invalidation
  - Regression coverage for hash-based cache and semantic change detection logic
affects: [03-pipeline-map-api-and-crud-wiring]

# Tech tracking
tech-stack:
  added: []
  patterns: [tdd-green-on-first-run, orm-detached-instance-workaround]

key-files:
  created: []
  modified:
    - backend/app/tests/test_pipeline_composer.py

key-decisions:
  - "Capture ORM attributes before second compose_pipeline call to avoid DetachedInstanceError from full-replace write pattern"

patterns-established:
  - "Test pattern: eagerly read ORM attributes before subsequent session commits that expire instances"

requirements-completed: [COMP-03]

# Metrics
duration: 2min
completed: 2026-03-11
---

# Phase 2 Plan 02: Cache and Semantic Change Detection Summary

**3 COMP-03 tests verifying SHA-256 cache determinism, cosmetic-field no-recompose, and semantic-field cache invalidation**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-11T17:53:51Z
- **Completed:** 2026-03-11T17:56:59Z
- **Tasks:** 2 (Task 2 was no-op -- Plan 01 implementation already correct)
- **Files modified:** 1

## Accomplishments
- test_cache_hit_deterministic: verifies second compose_pipeline call with identical agents hits cache (exactly 1 AI call total, same mapping structure)
- test_cosmetic_change_no_recompose: verifies is_semantic_change returns False for name, color, icon (individual and combined)
- test_semantic_change_invalidates_cache: verifies is_semantic_change returns True for description, system_prompt_template, agent_type; also verifies _compute_cache_key produces different hash when semantic fields change
- Full test suite passes: 40/40 tests with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Write COMP-03 cache and semantic-change tests** - `be2b8ac` (test)
2. **Task 2: Fix cache and semantic-change logic if needed** - no-op (all tests passed on first run, Plan 01 implementation correct)

## Files Created/Modified
- `backend/app/tests/test_pipeline_composer.py` - Added 3 COMP-03 tests (cache hit determinism, cosmetic no-recompose, semantic invalidation) and imported SEMANTIC_FIELDS constant

## Decisions Made
- Captured ORM mapping attributes (agent_id, phase, subsection_key) from result1 immediately after first compose_pipeline call, before the second call's full-replace write pattern (delete + insert + commit) expires those instances. This avoids SQLAlchemy DetachedInstanceError while still verifying cache determinism.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ORM DetachedInstanceError in cache determinism test**
- **Found during:** Task 1 (COMP-03 test writing)
- **Issue:** compose_pipeline's full-replace write pattern (delete existing mappings + insert new + commit) expires result1 ORM instances. Accessing result1 attributes after second call raises DetachedInstanceError.
- **Fix:** Capture result1 identifying data (agent_id, phase, subsection_key tuples) immediately after first call, before second call commits and expires those instances.
- **Files modified:** backend/app/tests/test_pipeline_composer.py
- **Verification:** All 7 pipeline composer tests pass
- **Committed in:** be2b8ac (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug in test approach)
**Impact on plan:** Minor test structure adjustment. No impact on production code. No scope creep.

## Issues Encountered
- DetachedInstanceError when accessing result1 ORM objects after second compose_pipeline call. Root cause: full-replace write pattern commits session, expiring all previously loaded instances. Resolved by eagerly reading attributes before second call.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All 7 pipeline composer tests pass (4 COMP-01 + 3 COMP-03), covering composition, batch splitting, cache determinism, and semantic change detection
- Pipeline composer service fully tested and ready for Phase 3 API endpoint and CRUD wiring
- is_semantic_change() gating confirmed correct for Phase 3 agent update dirty-flag logic

## Self-Check: PASSED

- FOUND: backend/app/tests/test_pipeline_composer.py
- FOUND: backend/app/services/pipeline_composer.py
- FOUND: 02-02-SUMMARY.md
- FOUND: be2b8ac (Task 1 commit)
- All 7 pipeline composer tests PASSED (4 COMP-01 + 3 COMP-03)

---
*Phase: 02-pipeline-composer-service*
*Completed: 2026-03-11*
