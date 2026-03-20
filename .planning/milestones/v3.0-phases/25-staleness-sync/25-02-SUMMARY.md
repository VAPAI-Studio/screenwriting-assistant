---
phase: 25-staleness-sync
plan: 02
subsystem: ui
tags: [react, react-query, tailwind, staleness, shotlist, accessibility]

# Dependency graph
requires:
  - phase: 25-staleness-sync plan 01
    provides: GET /api/shots/{project_id}/status and POST /api/shots/{project_id}/acknowledge-stale endpoints
  - phase: 18-two-mode-ui-shell
    provides: BreakdownLayout 3-panel skeleton
provides:
  - ShotlistStalenessBar amber warning banner component
  - React Query polling of shotlist-status with 30s staleTime
  - Dismiss mutation calling acknowledge-stale with query invalidation
  - Conditional banner rendering (shotlist_stale=true AND shot_count>0)
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [staleness-banner-with-dismiss-pattern]

key-files:
  created:
    - frontend/src/components/Breakdown/ShotlistStalenessBar.tsx
  modified:
    - frontend/src/lib/api.tsx
    - frontend/src/components/Breakdown/BreakdownLayout.tsx

key-decisions:
  - "ShotlistStalenessBar uses X dismiss (not Refresh) since auto-regeneration deferred to v3.1 (AUTO-01)"
  - "Banner only shown when BOTH shotlist_stale=true AND shot_count>0 to avoid confusing empty shotlists"
  - "30s staleTime for polling consistency with BreakdownPage staleness pattern"

patterns-established:
  - "Staleness banner pattern: useQuery polls status, useMutation dismisses, invalidateQueries re-fetches"

requirements-completed: [SYNC-02]

# Metrics
duration: 3min
completed: 2026-03-20
---

# Phase 25 Plan 02: Shotlist Staleness Banner Summary

**ShotlistStalenessBar amber banner in BreakdownLayout with React Query polling (30s) and dismiss via acknowledge-stale endpoint**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-20T16:19:00Z
- **Completed:** 2026-03-20T16:35:00Z
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint)
- **Files modified:** 3

## Accomplishments
- getShotlistStatus and acknowledgeShotlistStale API client methods added
- ShotlistStalenessBar component with amber styling, role="alert" accessibility, and dismiss button
- BreakdownLayout integration with React Query useQuery (30s staleTime) and useMutation (invalidates on dismiss)
- Conditional rendering: banner only appears when shotlist_stale=true AND shot_count>0
- End-to-end visual verification approved by user

## Task Commits

Each task was committed atomically:

1. **Task 1: Add API functions and create ShotlistStalenessBar component** - `447628a` (feat)
2. **Task 2: Wire ShotlistStalenessBar into BreakdownLayout with React Query** - `fa3482d` (feat)
3. **Task 3: Verify staleness banner end-to-end in browser** - human-verify checkpoint (approved)

## Files Created/Modified
- `frontend/src/components/Breakdown/ShotlistStalenessBar.tsx` - Amber warning banner with AlertTriangle icon, X dismiss button, role="alert", disabled state during API call
- `frontend/src/lib/api.tsx` - Added getShotlistStatus (GET /shots/{id}/status) and acknowledgeShotlistStale (POST /shots/{id}/acknowledge-stale)
- `frontend/src/components/Breakdown/BreakdownLayout.tsx` - Added useQuery for shotlist-status polling, useMutation for dismiss, conditional ShotlistStalenessBar render

## Decisions Made
- ShotlistStalenessBar uses X dismiss (not Refresh) since auto-regeneration is deferred to v3.1 (AUTO-01)
- Banner only shown when BOTH shotlist_stale=true AND shot_count>0 to avoid confusing empty shotlists
- 30s staleTime for polling consistency with BreakdownPage staleness pattern
- Query invalidation on dismiss success causes re-fetch, removing banner reactively

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 25 (Staleness & Sync) is now fully complete -- all SYNC requirements satisfied
- v3.0 milestone (Shotlist & Production Breakdown) is complete with all 45 requirements addressed
- Ready for v3.0 milestone closure and PROJECT.md evolution

## Self-Check: PASSED

All 4 files verified present. Both commit hashes (447628a, fa3482d) found in git log.

---
*Phase: 25-staleness-sync*
*Completed: 2026-03-20*
