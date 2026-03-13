---
phase: 11-ai-extraction-service
plan: 03
subsystem: ai, testing
tags: [extraction, deduplication, integration-tests, structured-outputs, scene-linking, breakdown, pytest]

# Dependency graph
requires:
  - phase: 11-ai-extraction-service
    plan: 01
    provides: BreakdownService skeleton, ExtractionResponse/ExtractedElement Pydantic models, chat_completion_structured()
  - phase: 11-ai-extraction-service
    plan: 02
    provides: Full extract() pipeline with upsert, scene link reconciliation, and wired API endpoint
  - phase: 10-breakdown-api
    provides: BreakdownElement, ElementSceneLink, BreakdownRun database models and CRUD endpoints
provides:
  - _deduplicate_elements() post-processing method in BreakdownService
  - 8 comprehensive integration/unit tests covering all Phase 11 requirements (EXTR-01 through EXTR-05, SYNC-01, SYNC-02)
  - Updated extraction API tests with mocked AI provider
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [post-processing-deduplication, mock-ai-structured-output-testing, service-level-integration-tests]

key-files:
  created:
    - backend/app/tests/test_breakdown_service.py
  modified:
    - backend/app/services/breakdown_service.py
    - backend/app/tests/test_breakdown_api.py
    - backend/app/tests/conftest.py

key-decisions:
  - "Deduplication uses (category, canonical_name.lower()) as merge key, keeping first description and merging scene appearances"
  - "Integration tests mock chat_completion_structured at module level rather than mocking the entire AI provider"
  - "Conftest UUID default patching fixed to use name/module check instead of identity check for robust SQLite compatibility"

patterns-established:
  - "Service-level integration test pattern: setup project with screenplay, mock AI at chat_completion_structured level, verify DB state after pipeline"
  - "Post-processing deduplication as safety net: AI prompt instructs dedup, but _deduplicate_elements catches any remaining duplicates"

requirements-completed: [EXTR-01, EXTR-02, EXTR-03, EXTR-04, EXTR-05, SYNC-01, SYNC-02]

# Metrics
duration: 3min
completed: 2026-03-13
---

# Phase 11 Plan 03: Integration Tests and Deduplication Summary

**Post-processing deduplication method and 8 comprehensive tests proving all Phase 11 requirements (extraction, schema, dedup, temperature, scene linking, user-modified protection, soft-delete protection)**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-13T20:52:00Z
- **Completed:** 2026-03-13T20:55:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added `_deduplicate_elements()` to BreakdownService that merges elements with same (category, name_lower) and combines scene appearances
- Created 8 integration/unit tests covering all 7 Phase 11 requirements (EXTR-01 through EXTR-05, SYNC-01, SYNC-02)
- Updated extraction API tests to work with real service using mocked AI provider
- Fixed conftest UUID default patching for reliable SQLite test compatibility
- Full test suite of 120 tests passes with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add post-processing deduplication and update extraction API tests** - `2619fd9` (feat)
2. **Task 2: Create comprehensive integration tests for BreakdownService** - `ea9a52e` (test)

## Files Created/Modified
- `backend/app/services/breakdown_service.py` - Added _deduplicate_elements() method, wired into extract() pipeline before upsert
- `backend/app/tests/test_breakdown_service.py` - New file: 8 integration/unit tests for all Phase 11 requirements
- `backend/app/tests/test_breakdown_api.py` - Updated TestExtraction tests to mock AI and create screenplay content
- `backend/app/tests/conftest.py` - Fixed UUID default patching to use name/module check instead of identity check

## Decisions Made
- Deduplication uses (category, canonical_name.lower()) as the merge key, keeping the first element's canonical_name and description while combining all scene_appearances
- Integration tests mock `chat_completion_structured` at the module level (not the entire AI provider) for precision
- Conftest UUID default patching uses function name/module check instead of `is` identity check, which failed because SQLAlchemy wraps the callable

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed conftest UUID default patching for SQLite**
- **Found during:** Task 2 (Integration test creation)
- **Issue:** `_patch_uuid_columns_for_sqlite()` used `column.default.arg is uuid.uuid4` identity check which fails because SQLAlchemy wraps the callable, making direct service calls (without API layer) fail with KeyError on UUID insert
- **Fix:** Changed to name/module attribute check (`fn.__name__ == 'uuid4' and fn.__module__ == 'uuid'`) and updated lambda to accept optional ctx argument (`lambda *_args: str(uuid.uuid4())`)
- **Files modified:** `backend/app/tests/conftest.py`
- **Verification:** All 120 tests pass including new direct service-call integration tests
- **Committed in:** `ea9a52e` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential fix for test infrastructure; existing API-level tests were unaffected because they create IDs explicitly, but direct service calls rely on SQLAlchemy defaults.

## Issues Encountered
None beyond the conftest fix documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 11 (AI Extraction Service) is fully complete with all 7 requirements tested and verified
- Extraction pipeline functional: POST /extract/{project_id} performs real AI extraction with structured outputs
- Ready for Phase 12 and beyond

## Self-Check: PASSED

All files verified present. All commits verified in git log.

---
*Phase: 11-ai-extraction-service*
*Completed: 2026-03-13*
