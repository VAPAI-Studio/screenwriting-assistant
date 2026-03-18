---
phase: 14-reverse-sync
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, breakdown, characters, reverse-sync, pydantic]

# Dependency graph
requires:
  - phase: 13-breakdown-page
    provides: BreakdownElement, ElementSceneLink, scene_links on elements, breakdown API patterns
  - phase: 10-breakdown-elements
    provides: _verify_element_ownership, _verify_project_ownership, JSONResponse idempotency pattern
provides:
  - POST /api/breakdown/element/{element_id}/sync-to-project endpoint
  - synced_to_characters computed bool field on BreakdownElementResponse
  - _get_synced_character_names() helper (O(1) set lookup, no N+1)
  - TestSyncToProject integration test class (5 tests)
  - TestSyncedToCharacters integration test class (3 tests)
affects:
  - 14-02 (frontend sync button will call this endpoint)
  - Any plan consuming BreakdownElementResponse (new field, safe default=False)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Compute-once-per-request set for computed booleans on list endpoints (no N+1)"
    - "db.flush() before ListItem creation when PhaseData created on demand (single commit)"
    - "Python .lower() case-insensitive duplicate detection (not SQL JSON functions)"
    - "JSONResponse with HTTP 200 for idempotent endpoints (mirrors scene link pattern)"

key-files:
  created: []
  modified:
    - backend/app/models/schemas.py
    - backend/app/api/endpoints/breakdown.py
    - backend/app/tests/test_breakdown_api.py

key-decisions:
  - "synced_to_characters is a non-stored computed field (safe default=False so model_validate from ORM never fails)"
  - "PhaseData created with db.flush() (not db.commit()) so ListItem gets phase_data_id in a single atomic commit"
  - "Duplicate detection uses Python .lower() comparison, not SQL JSON operators, for SQLite/PostgreSQL compat"
  - "synced_names set computed once before the element loop (not per element) to avoid N+1 query"
  - "Endpoint placed between remove_scene_link and the summary section to follow logical grouping"

patterns-established:
  - "list_elements now loops to build result list instead of returning ORM objects directly, enabling per-element computed field injection"

requirements-completed:
  - SYNC-05

# Metrics
duration: 2min
completed: 2026-03-18
---

# Phase 14 Plan 01: Reverse Sync Backend Summary

**POST /element/{id}/sync-to-project endpoint that pushes character breakdown elements into story.characters as supporting ListItems, with case-insensitive idempotency and synced_to_characters computed field on list_elements**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-18T01:26:00Z
- **Completed:** 2026-03-18T01:28:15Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added `synced_to_characters: bool = False` to `BreakdownElementResponse` schema with safe default so ORM model_validate never fails
- Added `_get_synced_character_names()` helper that returns a set of lowercased names from story.characters ListItems (one query, no N+1)
- Modified `list_elements` to compute synced_names once before loop and inject field per element
- Implemented `POST /element/{element_id}/sync-to-project` endpoint with on-demand PhaseData creation, case-insensitive duplicate detection, and idempotent 200 responses
- 8 new integration tests (3 for synced field, 5 for sync endpoint); all 31 breakdown tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Add synced_to_characters to schema and update list_elements** - `5c9caa9` (feat)
2. **Task 2: Add sync-to-project endpoint and integration tests** - `35f974d` (feat)

**Plan metadata:** (docs commit follows)

_Note: TDD tasks — tests written first (RED), implementation second (GREEN)_

## Files Created/Modified
- `backend/app/models/schemas.py` - Added `synced_to_characters: bool = False` to `BreakdownElementResponse`
- `backend/app/api/endpoints/breakdown.py` - Added `_get_synced_character_names()`, modified `list_elements`, added `sync_element_to_project` endpoint
- `backend/app/tests/test_breakdown_api.py` - Added `TestSyncedToCharacters` (3 tests) and `TestSyncToProject` (5 tests)

## Decisions Made
- `synced_to_characters` is a computed non-stored field with `= False` default so `model_validate(orm_obj)` never fails (ORM has no such attribute)
- `db.flush()` (not `db.commit()`) when creating PhaseData on demand, so the following ListItem creation is covered by a single `db.commit()` at the end
- Python `.lower()` for case-insensitive comparison — not `func.lower()` or JSON SQL operators — for SQLite/PostgreSQL compat per project convention
- `synced_names` set computed once at the top of `list_elements` before the loop, not inside the loop, to avoid N+1 queries

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Backend sync endpoint is complete and tested; ready for Plan 14-02 (frontend "Add to Characters" button)
- `BreakdownElementResponse.synced_to_characters` provides the flag the frontend needs to show/hide the button
- No blockers

## Self-Check: PASSED

All files confirmed present. Both task commits verified in git history.

---
*Phase: 14-reverse-sync*
*Completed: 2026-03-18*
