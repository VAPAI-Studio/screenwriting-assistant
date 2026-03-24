---
phase: 42-breadcrumb-navigation
plan: 01
subsystem: ui
tags: [react, breadcrumb, navigation, react-query, episode]

# Dependency graph
requires:
  - phase: 38-show-model-home-split
    provides: "Show model, ROUTES.SHOW, QUERY_KEYS.SHOW, indigo show identity"
  - phase: 39-episode-crud
    provides: "Project.show_id FK, Project.episode_number fields"
provides:
  - "EpisodeBreadcrumb reusable component for episode-level navigation"
  - "Breadcrumb integration in all three project modes (screenwriting, breakdown, storyboard)"
affects: [future-episode-views, show-navigation]

# Tech tracking
tech-stack:
  added: []
  patterns: [conditional-breadcrumb-rendering, height-adjustment-for-breadcrumb]

key-files:
  created:
    - frontend/src/components/Editor/EpisodeBreadcrumb.tsx
  modified:
    - frontend/src/components/Editor/Editor.tsx
    - frontend/src/components/Breakdown/BreakdownLayout.tsx
    - frontend/src/components/Storyboard/StoryboardView.tsx

key-decisions:
  - "Breadcrumb renders nothing for standalone films -- parent components gate on show_id"
  - "Show title fetched with staleTime: Infinity since it rarely changes within a session"
  - "Height calc uses 89px (56px header + 33px breadcrumb) when breadcrumb is visible"

patterns-established:
  - "Conditional breadcrumb: isEpisode = !!project.show_id && project.episode_number != null"
  - "Fragment wrapper pattern for adding breadcrumb above existing layout div"

requirements-completed: [EPIS-05]

# Metrics
duration: 3min
completed: 2026-03-24
---

# Phase 42 Plan 01: Breadcrumb Navigation Summary

**Reusable EpisodeBreadcrumb component showing "Show Title > Episode N: Title" with indigo-styled link to parent show, integrated into all three project modes**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-24T21:39:29Z
- **Completed:** 2026-03-24T21:42:25Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created EpisodeBreadcrumb component with React Query show title fetch, loading/error states, and indigo link styling
- Integrated breadcrumb into Editor (screenwriting), BreakdownLayout (breakdown), and StoryboardView (storyboard)
- Standalone film projects remain completely unchanged -- no breadcrumb, no height adjustment

## Task Commits

Each task was committed atomically:

1. **Task 1: Create EpisodeBreadcrumb component** - `07a3513` (feat)
2. **Task 2: Integrate EpisodeBreadcrumb into Editor, BreakdownLayout, and StoryboardView** - `f3178ce` (feat)

**Plan metadata:** pending (docs: complete plan)

## Files Created/Modified
- `frontend/src/components/Editor/EpisodeBreadcrumb.tsx` - Reusable breadcrumb component accepting showId, episodeNumber, episodeTitle props
- `frontend/src/components/Editor/Editor.tsx` - Added breadcrumb above section sidebar layout for episodes
- `frontend/src/components/Breakdown/BreakdownLayout.tsx` - Added project query and breadcrumb above three-panel breakdown layout
- `frontend/src/components/Storyboard/StoryboardView.tsx` - Added project query and breadcrumb above storyboard grid

## Decisions Made
- Show title fetched with `staleTime: Infinity` to avoid unnecessary refetches (show title is stable within a session)
- On show fetch error, breadcrumb gracefully falls back to "Show" as link text rather than hiding entirely
- Height adjustment uses fixed calc (89px = 56px header + 33px breadcrumb) rather than dynamic measurement

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Breadcrumb navigation complete for all episode views
- Ready for any future episode-related features that need show context navigation

---
*Phase: 42-breadcrumb-navigation*
*Completed: 2026-03-24*
