---
phase: 39-episode-data-model-linking
plan: 01
subsystem: api, database
tags: [sqlalchemy, fastapi, episode, show, fk, migration, pydantic]

# Dependency graph
requires:
  - phase: 36-show-model-frontend-shell
    provides: "Show model and CRUD endpoints"
  - phase: 37-series-bible-data-api
    provides: "Bible columns on Show model"
provides:
  - "Project model with show_id FK and episode_number columns"
  - "EpisodeCreate schema with title/episode_number/framework validation"
  - "POST /api/shows/{show_id}/episodes endpoint with auto-increment and section scaffolding"
  - "Migration 008 for show_id and episode_number on projects table"
affects: [40-episode-list-ui, 41-episode-detail-view, bible-injection]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Episode-as-Project: episodes reuse the existing Project model with nullable show_id FK"
    - "Auto-increment episode_number via MAX query when not provided"
    - "Section scaffolding shared between standalone and episode creation"

key-files:
  created:
    - "backend/migrations/delta/008_episode_columns.sql"
  modified:
    - "backend/app/models/database.py"
    - "backend/app/models/schemas.py"
    - "backend/app/api/endpoints/shows.py"
    - "backend/app/tests/test_shows_api.py"

key-decisions:
  - "Episodes are Projects with show_id FK -- no separate Episode table"
  - "episode_number auto-increments via MAX+1 query when not provided"
  - "Section scaffolding identical to standalone projects (6 sections)"

patterns-established:
  - "Episode linking: show_id FK with CASCADE delete on projects table"
  - "Auto-increment via func.max query pattern for episode numbering"

requirements-completed: [EPIS-01, EPIS-02, EPIS-04]

# Metrics
duration: 4min
completed: 2026-03-24
---

# Phase 39 Plan 01: Episode Data Model & Linking Summary

**Episode support via nullable show_id FK on Project model, POST /api/shows/{show_id}/episodes endpoint with auto-increment and 6-section scaffolding**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-24T19:49:59Z
- **Completed:** 2026-03-24T20:20:02Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Extended Project model with show_id FK (CASCADE delete) and episode_number columns
- Created EpisodeCreate schema with title/episode_number/framework validation
- Added POST /api/shows/{show_id}/episodes endpoint with auto-increment episode numbering
- Full backward compatibility -- standalone projects (show_id=NULL) unaffected
- 48 tests pass including 10 new episode-specific tests, zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend Project model with episode columns, add migration and schemas** - `19e4251` (feat)
2. **Task 2: Add episode creation endpoint with section scaffolding and API tests** - `38c71a7` (feat)

_Note: Both tasks used TDD (RED -> GREEN flow)_

## Files Created/Modified
- `backend/app/models/database.py` - Added show_id FK and episode_number columns to Project model
- `backend/app/models/schemas.py` - Added EpisodeCreate schema, extended Project response with show_id/episode_number
- `backend/app/api/endpoints/shows.py` - Added create_episode endpoint with auto-increment and section scaffolding
- `backend/migrations/delta/008_episode_columns.sql` - Idempotent migration for show_id and episode_number
- `backend/app/tests/test_shows_api.py` - Added TestEpisodeModel (4 tests) and TestEpisodesAPI (6 tests)

## Decisions Made
None - followed plan as specified

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Episode creation endpoint is live and tested
- Ready for frontend episode list UI (Phase 40)
- Ready for bible injection into generation services
- Show deletion cascades to episode projects

## Self-Check: PASSED

All 6 files verified present. Both commit hashes (19e4251, 38c71a7) confirmed in git log. 48 tests pass.

---
*Phase: 39-episode-data-model-linking*
*Completed: 2026-03-24*
