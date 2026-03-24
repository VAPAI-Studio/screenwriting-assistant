---
phase: 40-episode-management-ui
plan: 01
subsystem: ui, api
tags: [react, fastapi, react-query, radix-ui, episodes, crud]

# Dependency graph
requires:
  - phase: 39-episode-data-model-linking
    provides: "Project model with show_id FK and episode_number, POST episodes endpoint"
  - phase: 38-show-management-ui
    provides: "ShowDetail page with placeholder episode section, Shows components directory"
provides:
  - "GET /api/shows/{show_id}/episodes endpoint returning ordered episodes"
  - "EpisodeList component with ordered display, navigation, and delete"
  - "CreateEpisodeModal with framework selection and episode number preview"
  - "Project TypeScript type with show_id and episode_number fields"
  - "QUERY_KEYS.EPISODES and api.getEpisodes/createEpisode functions"
affects: [episode-editor-integration, show-episode-count]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Episode list uses existing deleteProject for deletion", "Episode number auto-calculated from max+1 client-side for preview"]

key-files:
  created:
    - frontend/src/components/Shows/EpisodeList.tsx
    - frontend/src/components/Shows/CreateEpisodeModal.tsx
  modified:
    - backend/app/api/endpoints/shows.py
    - backend/app/tests/test_shows_api.py
    - frontend/src/types/index.ts
    - frontend/src/lib/constants.ts
    - frontend/src/lib/api.tsx
    - frontend/src/components/Shows/ShowDetail.tsx

key-decisions:
  - "Reuse deleteProject API for episode deletion since episodes are Projects"
  - "Client-side next episode number calculation via Math.max for preview display"

patterns-established:
  - "Episode CRUD reuses Project endpoints for delete/update operations"

requirements-completed: [EPIS-03]

# Metrics
duration: 3min
completed: 2026-03-24
---

# Phase 40 Plan 01: Episode Management UI Summary

**GET episodes endpoint with ordered listing, create/delete UI, and navigation on ShowDetail page using EpisodeList and CreateEpisodeModal components**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-24T20:37:16Z
- **Completed:** 2026-03-24T20:40:23Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- GET /api/shows/{show_id}/episodes endpoint returns episodes ordered by episode_number with 404 for unknown show
- EpisodeList component renders episodes with Ep. N prefix, title, framework badge, and delete button
- CreateEpisodeModal with title input, framework selector, and "Will be Episode N" preview
- ShowDetail placeholder replaced with live EpisodeList wired to React Query

## Task Commits

Each task was committed atomically:

1. **Task 1: Add GET episodes endpoint and tests (TDD RED)** - `48a56f9` (test)
2. **Task 1: Add GET episodes endpoint and tests (TDD GREEN)** - `827b6fe` (feat)
3. **Task 2: Build EpisodeList, CreateEpisodeModal, and wire into ShowDetail** - `cb1c7b7` (feat)

## Files Created/Modified
- `backend/app/api/endpoints/shows.py` - Added list_episodes GET endpoint with episode_number ordering
- `backend/app/tests/test_shows_api.py` - 3 new tests: list, empty, not_found
- `frontend/src/types/index.ts` - Added show_id and episode_number to Project interface
- `frontend/src/lib/constants.ts` - Added QUERY_KEYS.EPISODES
- `frontend/src/lib/api.tsx` - Added getEpisodes and createEpisode API functions
- `frontend/src/components/Shows/EpisodeList.tsx` - Episode list with query, navigation, delete
- `frontend/src/components/Shows/CreateEpisodeModal.tsx` - Modal dialog for episode creation
- `frontend/src/components/Shows/ShowDetail.tsx` - Replaced placeholder with EpisodeList

## Decisions Made
- Reused existing deleteProject API for episode deletion (episodes are Projects with show_id)
- Client-side Math.max calculation for next episode number preview in CreateEpisodeModal

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Episode CRUD is fully wired -- users can create, view, navigate to, and delete episodes from the show detail page
- ShowCard still shows hardcoded "0 episodes" -- future work to query actual count
- 1 pre-existing test failure in test_session_isolation (unrelated to this phase)

## Self-Check: PASSED

All 8 files verified present. All 3 task commits verified in git log.

---
*Phase: 40-episode-management-ui*
*Completed: 2026-03-24*
