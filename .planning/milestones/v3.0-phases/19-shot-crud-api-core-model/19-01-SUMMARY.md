---
phase: 19-shot-crud-api-core-model
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, shot, crud, reorder, jsonb]

# Dependency graph
requires:
  - phase: 17-data-foundation
    provides: Shot ORM model, ShotCreate/ShotUpdate/ShotResponse schemas, ReorderRequest schema
provides:
  - Shot CRUD API endpoints (create, list, get, update, delete, reorder) at /api/shots
  - 18 integration tests covering all Shot endpoints
affects: [20-shotlist-frontend-panel, shot-ai-generation]

# Tech tracking
tech-stack:
  added: []
  patterns: [Shot CRUD follows breakdown.py pattern with _verify_project_ownership, JSONB fields column for freeform shot metadata]

key-files:
  created:
    - backend/app/api/endpoints/shots.py
    - backend/app/tests/test_shots_api.py
  modified:
    - backend/app/main.py

key-decisions:
  - "Copied _verify_project_ownership locally into shots.py rather than sharing from breakdown.py -- avoids cross-module coupling"
  - "Reorder returns 403 (not 404) for foreign shot IDs -- distinguishes ownership violation from not-found"
  - "Fields dict is fully replaced on PUT (not merged) -- consistent with JSONB column semantics"

patterns-established:
  - "Shot CRUD pattern: ownership check -> query -> mutate -> commit -> return"
  - "Reorder validation: count matching IDs vs submitted IDs, 403 on mismatch"

requirements-completed: [DATA-04, SHOT-01, SHOT-02]

# Metrics
duration: 3min
completed: 2026-03-19
---

# Phase 19 Plan 01: Shot CRUD API Summary

**6 Shot CRUD + reorder endpoints with JSONB fields storage, ownership checks, and 18 passing integration tests**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-19T18:58:23Z
- **Completed:** 2026-03-19T19:01:32Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created 6 Shot API endpoints: POST create (201), GET list, GET single, PUT partial update, DELETE hard-delete (204), POST reorder
- All 13 standard shot fields (shot_size, camera_angle, camera_movement, lens, description, action, dialogue, sound, characters, environment, props, equipment, notes) stored and retrieved via JSONB fields column
- Reorder endpoint validates shot ownership (403 for foreign IDs) and bulk-updates sort_order
- 18 integration tests covering create, list, get, update, delete, reorder, auth, and ownership

## Task Commits

Each task was committed atomically:

1. **Task 1: Create shots.py endpoint file and register router in main.py** - `8fbc8ed` (feat)
2. **Task 2: Create test_shots_api.py with comprehensive integration tests** - `e6f39d4` (test)

## Files Created/Modified
- `backend/app/api/endpoints/shots.py` - 6 Shot CRUD + reorder endpoints with ownership verification
- `backend/app/tests/test_shots_api.py` - 18 integration tests across 8 test classes
- `backend/app/main.py` - Router registration for shots at /api/shots

## Decisions Made
- Copied `_verify_project_ownership` locally into shots.py rather than importing from breakdown.py -- avoids cross-endpoint coupling while maintaining consistent pattern
- Reorder returns 403 (Forbidden) for foreign shot IDs rather than 404 -- semantically distinguishes "you don't own this" from "it doesn't exist"
- PUT fields replacement (not merge) -- sending `{"fields": {"camera_angle": "High"}}` replaces the entire fields dict, consistent with how JSONB columns work

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Pre-existing test failures noted (not caused by this plan):
- `test_session_isolation.py::test_orchestrate_uses_session_factory` - MagicMock template resolution issue
- `test_yolo_integration.py::test_yolo_wizard_routes_through_middleware` - SQLite FK constraint from test ordering

These are logged for awareness but are out of scope per deviation rules.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Shot CRUD API complete and tested, ready for frontend shotlist panel (Phase 20)
- All 6 endpoints registered at /api/shots with proper auth and ownership checks
- No blockers for downstream phases

## Self-Check: PASSED

- [x] backend/app/api/endpoints/shots.py exists
- [x] backend/app/tests/test_shots_api.py exists
- [x] 19-01-SUMMARY.md exists
- [x] Commit 8fbc8ed found in git log
- [x] Commit e6f39d4 found in git log

---
*Phase: 19-shot-crud-api-core-model*
*Completed: 2026-03-19*
