---
phase: 12-staleness-hooks
plan: "02"
subsystem: testing
tags: [staleness, breakdown, extraction, sync, tdd, sqlalchemy]

# Dependency graph
requires:
  - phase: 12-01
    provides: breakdown_stale flag set on write/scenes changes; _mark_breakdown_stale helper
  - phase: 11-02
    provides: BreakdownService.extract() pipeline with single-commit pattern
provides:
  - extract() success path sets breakdown_stale=False atomically with extraction commit (SYNC-04)
  - test_extraction_clears_stale integration test
  - test_failed_extraction_does_not_clear_stale integration test
affects:
  - 12-03 (frontend staleness banner should now see correct cleared state after extraction)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Stale-clear inserted between _record_run() and db.commit() -- stays in the same transaction"
    - "Re-query Project via str(project_id) cast for SQLite/PostgreSQL compat before clearing flag"
    - "TDD RED commit then GREEN commit for each TDD task"

key-files:
  created: []
  modified:
    - backend/app/services/breakdown_service.py
    - backend/app/tests/test_staleness.py

key-decisions:
  - "breakdown_stale=False cleared in the extract() success path between step 6 (_record_run) and step 7 (db.commit()) -- atomic with extraction, no second commit needed"
  - "Failure path (except block) deliberately unchanged -- failed extraction must not clear stale flag"
  - "Empty ExtractionResponse(elements=[]) sufficient for SYNC-04 tests -- extraction logic itself is tested in Phase 11"

patterns-established:
  - "Stale-clear pattern: query Project row in success path, set field, let existing commit handle it"

requirements-completed:
  - SYNC-04

# Metrics
duration: 2min
completed: 2026-03-14
---

# Phase 12 Plan 02: Staleness Hooks - Extraction Clears Stale Flag Summary

**breakdown_stale=False cleared atomically in BreakdownService.extract() success path, completing the SYNC-04 staleness cycle with 2 new integration tests (10 total)**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-14T13:55:23Z
- **Completed:** 2026-03-14T13:57:15Z
- **Tasks:** 1 (TDD: 2 commits)
- **Files modified:** 2

## Accomplishments
- Inserted SYNC-04 stale-clear block in `extract()` between `_record_run()` and `db.commit()` -- fully atomic
- `test_extraction_clears_stale`: sets stale=True, runs mocked extraction, asserts stale=False and BreakdownRun status="completed"
- `test_failed_extraction_does_not_clear_stale`: sets stale=True, mocks AI to raise RuntimeError, asserts stale remains True
- Full staleness test suite: 10/10 passed; full backend suite: 130/130 passed

## Task Commits

Each task was committed atomically via TDD:

1. **RED - SYNC-04 failing tests** - `934e7ab` (test)
2. **GREEN - extract() stale-clear implementation** - `3aebb47` (feat)

## Files Created/Modified
- `backend/app/services/breakdown_service.py` - Added 6b stale-clear block (5 lines) inside extract() success path
- `backend/app/tests/test_staleness.py` - Added imports (asyncio, BreakdownRun, ScreenplayContent, breakdown_service, ExtractionResponse) + 2 new SYNC-04 test methods

## Decisions Made
- breakdown_stale=False cleared in extract() success path between step 6 and step 7 -- same transaction, no second commit needed
- Failure path (except block) deliberately untouched -- failed extraction must not clear stale flag
- Empty ExtractionResponse(elements=[]) is sufficient for SYNC-04 stale-clear tests (the Phase 11 tests cover element extraction correctness)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- SYNC-04 complete: extraction now atomically clears the staleness flag
- Staleness cycle is fully wired: writes/scene changes set stale=True, successful extraction sets stale=False
- Frontend staleness banner (Phase 12-03 or later) can now read breakdown_stale from the project API and show/hide accordingly

## Self-Check: PASSED

- breakdown_service.py: FOUND
- test_staleness.py: FOUND
- 12-02-SUMMARY.md: FOUND
- Commit 934e7ab (test RED): FOUND
- Commit 3aebb47 (feat GREEN): FOUND

---
*Phase: 12-staleness-hooks*
*Completed: 2026-03-14*
