---
phase: 25-staleness-sync
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, staleness, shotlist, sync]

# Dependency graph
requires:
  - phase: 19-shot-crud-api-core-model
    provides: Shot model and CRUD endpoints
  - phase: 17-data-foundation
    provides: shotlist_stale column on Project model
provides:
  - _mark_shotlist_stale helper function with Shot-exists guard
  - SHOTLIST_SENSITIVE_PHASES constant
  - _is_character_item helper for detecting story/characters mutations
  - GET /api/shots/{project_id}/status endpoint
  - POST /api/shots/{project_id}/acknowledge-stale endpoint
  - Shotlist staleness hooks in 6 mutation locations
affects: [25-staleness-sync, frontend-shotlist-banner]

# Tech tracking
tech-stack:
  added: []
  patterns: [shotlist-staleness-hook-pattern mirroring breakdown_stale]

key-files:
  created:
    - backend/app/tests/test_shotlist_staleness.py
  modified:
    - backend/app/api/endpoints/phase_data.py
    - backend/app/api/endpoints/wizards.py
    - backend/app/api/endpoints/list_items.py
    - backend/app/api/endpoints/shots.py

key-decisions:
  - "Shotlist staleness follows identical pattern to breakdown_stale: guard condition checks Shot existence, not BreakdownElement"
  - "Scene list item changes trigger BOTH breakdown_stale and shotlist_stale (dual hook)"
  - "Character list item changes trigger shotlist_stale only (not breakdown_stale)"
  - "Status and acknowledge-stale endpoints placed before /{project_id}/{shot_id} catch-all to prevent route shadowing"

patterns-established:
  - "_mark_shotlist_stale: identical pattern to _mark_breakdown_stale but guards on Shot existence"
  - "_is_character_item: parallel to _is_scene_item for detecting story/characters PhaseData"

requirements-completed: [SYNC-01, SYNC-03, SYNC-04]

# Metrics
duration: 5min
completed: 2026-03-20
---

# Phase 25 Plan 01: Shotlist Staleness Hooks Summary

**_mark_shotlist_stale wired into 6 backend mutation paths with Shot-exists guard, status/acknowledge endpoints, and 13 integration tests**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-20T16:12:14Z
- **Completed:** 2026-03-20T16:17:11Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- _mark_shotlist_stale helper with guard condition (only marks stale when shots exist)
- Staleness hooks wired into all 6 mutation locations: PATCH write/scenes, script_writer_wizard, scene_wizard, and scene/character list item CRUD
- GET /api/shots/{project_id}/status returns { shotlist_stale, shot_count }
- POST /api/shots/{project_id}/acknowledge-stale clears the flag
- 13 comprehensive integration tests all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test scaffold for shotlist staleness hooks (TDD RED)** - `3d44553` (test)
2. **Task 2: Implement _mark_shotlist_stale, wire all 6 hook locations, add status/acknowledge endpoints (TDD GREEN)** - `9f05e86` (feat)

## Files Created/Modified
- `backend/app/tests/test_shotlist_staleness.py` - 13 integration tests covering all staleness hook locations, status endpoint, and acknowledge endpoint
- `backend/app/api/endpoints/phase_data.py` - Added SHOTLIST_SENSITIVE_PHASES constant and _mark_shotlist_stale helper function
- `backend/app/api/endpoints/wizards.py` - Imported _mark_shotlist_stale and wired into script_writer_wizard and scene_wizard branches
- `backend/app/api/endpoints/list_items.py` - Added _is_character_item helper, wired shotlist staleness into scene and character CRUD
- `backend/app/api/endpoints/shots.py` - Added get_shotlist_status and acknowledge_shotlist_stale endpoints

## Decisions Made
- Shotlist staleness follows identical pattern to breakdown_stale: guard condition checks Shot existence (not BreakdownElement)
- Scene list item changes trigger BOTH breakdown_stale and shotlist_stale (dual hook) since scenes affect both breakdowns and shot grouping
- Character list item changes trigger shotlist_stale only (character names appear in shot fields, not breakdowns)
- Status and acknowledge-stale endpoints placed before /{project_id}/{shot_id} catch-all routes to prevent FastAPI route shadowing

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test failure in test_session_isolation.py (unrelated to this plan, not touched)

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Backend staleness infrastructure complete, ready for Plan 02 (frontend banner/UI)
- All hooks verified with integration tests
- Status endpoint available for frontend polling

## Self-Check: PASSED

All 6 files verified present. Both commit hashes (3d44553, 9f05e86) found in git log.

---
*Phase: 25-staleness-sync*
*Completed: 2026-03-20*
