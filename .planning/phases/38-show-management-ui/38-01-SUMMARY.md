---
phase: 38-show-management-ui
plan: 01
subsystem: ui
tags: [react, typescript, react-query, radix-ui, show-management, series-bible]

# Dependency graph
requires:
  - phase: 37-series-bible-data-api
    provides: Show model, /api/shows CRUD endpoints, /api/shows/{id}/bible endpoints
provides:
  - Show, ShowCreate, BibleResponse, BibleUpdate TypeScript interfaces
  - 7 API client methods for shows and bible (getShows, getShow, createShow, updateShow, deleteShow, getBible, updateBible)
  - QUERY_KEYS.SHOWS/SHOW/BIBLE, ROUTES.SHOW, BIBLE_SECTIONS, DURATION_PRESETS constants
  - ShowCard component for show cards on home page
  - CreateShowModal for creating new shows
  - Split home page with Shows and Films sections
  - /shows/:showId route placeholder
affects: [38-02-show-detail-page, 39-episodes-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns: [split-home-page-sections, show-card-pattern, show-create-modal-pattern]

key-files:
  created:
    - frontend/src/components/Shows/ShowCard.tsx
    - frontend/src/components/Shows/CreateShowModal.tsx
  modified:
    - frontend/src/types/index.ts
    - frontend/src/lib/api.tsx
    - frontend/src/lib/constants.ts
    - frontend/src/components/Projects/ProjectList.tsx
    - frontend/src/App.tsx

key-decisions:
  - "ShowCard displays hardcoded '0 episodes' badge -- actual episode count comes in Phase 39"
  - "Home page heading changed from 'Projects' to 'Home' to reflect split sections"
  - "ShowDetailRoute is an inline placeholder in App.tsx -- real component comes in Plan 02"
  - "Films section empty state differs from shows -- uses Film icon instead of Tv icon"

patterns-established:
  - "Show components live in frontend/src/components/Shows/ directory"
  - "Shows use indigo accent color (vs amber for films) for visual differentiation"

requirements-completed: [SHOW-02]

# Metrics
duration: 4min
completed: 2026-03-24
---

# Phase 38 Plan 01: Show Management UI Summary

**Split home page with Shows and Films sections, ShowCard/CreateShowModal components, Show/Bible TypeScript types, 7 API client methods, and /shows/:showId route placeholder**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-24T19:21:51Z
- **Completed:** 2026-03-24T19:26:10Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Added Show, ShowCreate, BibleResponse, BibleUpdate TypeScript interfaces and 7 API client methods for full show/bible data layer
- Split home page into "Shows" section (indigo accent, Tv icon) and "Films" section (amber accent, Film icon) with independent empty states
- Created ShowCard component (title, description, date, "0 episodes" badge) and CreateShowModal (title + description fields, navigates to show detail on creation)
- Registered /shows/:showId route with placeholder component for Plan 02

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Show/Bible types, API methods, and constants** - `a895bc5` (feat)
2. **Task 2: Create ShowCard, CreateShowModal, split ProjectList, and register route** - `085bd02` (feat)

## Files Created/Modified
- `frontend/src/types/index.ts` - Added Show, ShowCreate, BibleResponse, BibleUpdate interfaces
- `frontend/src/lib/api.tsx` - Added 7 show/bible API methods (getShows, getShow, createShow, updateShow, deleteShow, getBible, updateBible)
- `frontend/src/lib/constants.ts` - Added QUERY_KEYS.SHOWS/SHOW/BIBLE, ROUTES.SHOW, BIBLE_SECTIONS, DURATION_PRESETS
- `frontend/src/components/Shows/ShowCard.tsx` - Show card with title, Tv icon, description, date, "0 episodes" badge
- `frontend/src/components/Shows/CreateShowModal.tsx` - Radix Dialog modal for creating shows with title and description
- `frontend/src/components/Projects/ProjectList.tsx` - Split into Shows and Films sections with unified loading state
- `frontend/src/App.tsx` - Added /shows/:showId route with ShowDetailRoute placeholder

## Decisions Made
- ShowCard displays hardcoded "0 episodes" badge since actual episode count requires Phase 39 episode model
- Changed home page heading from "Projects" to "Home" to better reflect the dual-section layout
- ShowDetailRoute is an inline placeholder function in App.tsx rather than a separate component file, since Plan 02 will replace it
- Shows use indigo accent color to visually differentiate from amber-colored film projects

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Types, API methods, constants, and route are all in place for Plan 02 (show detail page with bible editor)
- ShowCard and CreateShowModal are functional and ready for use
- The /shows/:showId route placeholder will be replaced by ShowDetail component in Plan 02

## Self-Check: PASSED

All 8 files verified present. Both task commits (a895bc5, 085bd02) verified in git log.

---
*Phase: 38-show-management-ui*
*Completed: 2026-03-24*
