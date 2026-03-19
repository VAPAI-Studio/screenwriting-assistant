---
phase: 20-shotlist-panel
plan: 01
subsystem: ui
tags: [react, typescript, react-query, css-grid, inline-editing, shotlist]

# Dependency graph
requires:
  - phase: 19-shot-crud-api-core-model
    provides: Shot CRUD API endpoints (list, create, update, delete, reorder)
  - phase: 18-two-mode-ui-shell
    provides: BreakdownLayout 3-panel skeleton with center panel placeholder
provides:
  - Shot, ShotFields, ShotCreate, ShotUpdate TypeScript interfaces
  - QUERY_KEYS.SHOTS React Query key factory
  - Shot API client functions (listShots, createShot, updateShot, deleteShot, reorderShots)
  - ShotlistPanel component with React Query data fetching and optimistic mutations
  - SceneGroup component with scene header and shot count
  - ShotRow component with CSS grid layout and 5 editable field columns
  - InlineEditCell click-to-edit component with blur-save and keyboard handlers
affects: [20-02-shotlist-panel, 21-script-read-view, 24-ai-chat-breakdown]

# Tech tracking
tech-stack:
  added: []
  patterns: [optimistic-mutation-with-field-spread, css-grid-table-layout, click-to-edit-inline-cell]

key-files:
  created:
    - frontend/src/components/Breakdown/InlineEditCell.tsx
    - frontend/src/components/Breakdown/ShotRow.tsx
    - frontend/src/components/Breakdown/SceneGroup.tsx
    - frontend/src/components/Breakdown/ShotlistPanel.tsx
  modified:
    - frontend/src/types/index.ts
    - frontend/src/lib/constants.ts
    - frontend/src/lib/api.tsx
    - frontend/src/components/Breakdown/BreakdownLayout.tsx

key-decisions:
  - "Field spread on update: PUT sends { fields: { ...existingFields, [key]: newValue } } to prevent JSONB wipe since backend replaces entire fields dict"
  - "Scene grouping is frontend-only: flat API response grouped by scene_item_id with unassigned shots last"
  - "5 visible columns (shot_size, camera_angle, camera_movement, description, action) out of 13 total fields; remaining accessible in future detail/expansion view"

patterns-established:
  - "Optimistic field update with spread: always spread existing fields before overriding changed key in JSONB column updates"
  - "CSS grid table: shared gridTemplateColumns string between header row and data rows for alignment"
  - "InlineEditCell pattern: click-to-edit with 150ms blur-save, Enter save, Escape cancel"

requirements-completed: [SHOT-03, SHOT-04, SHOT-07]

# Metrics
duration: 4min
completed: 2026-03-19
---

# Phase 20 Plan 01: Shotlist Panel Summary

**Scene-grouped CSS grid shotlist table with inline field editing via optimistic React Query mutations, wired into BreakdownLayout center panel**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-19T19:41:32Z
- **Completed:** 2026-03-19T19:45:08Z
- **Tasks:** 2
- **Files modified:** 8 (4 created, 4 modified)

## Accomplishments
- Shot TypeScript interfaces (Shot, ShotFields, ShotCreate, ShotUpdate) and 5 API client functions added
- ShotlistPanel fetches shots via React Query, groups by scene, renders CSS grid table with sticky column headers
- InlineEditCell provides click-to-edit with Enter/Escape/blur-save (150ms) matching ElementCard pattern
- Optimistic update mutation spreads existing fields before overriding changed key, preventing JSONB wipe
- BreakdownLayout center panel now renders live ShotlistPanel instead of Phase 20 placeholder

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Shot types, API functions, and QUERY_KEYS constant** - `5465c11` (feat)
2. **Task 2: Create ShotlistPanel, SceneGroup, ShotRow, InlineEditCell and wire into BreakdownLayout** - `6f7dcff` (feat)

## Files Created/Modified
- `frontend/src/types/index.ts` - Added ShotFields, Shot, ShotCreate, ShotUpdate interfaces
- `frontend/src/lib/constants.ts` - Added QUERY_KEYS.SHOTS query key factory
- `frontend/src/lib/api.tsx` - Added listShots, createShot, updateShot, deleteShot, reorderShots API functions
- `frontend/src/components/Breakdown/InlineEditCell.tsx` - Click-to-edit cell with blur-save and keyboard handlers
- `frontend/src/components/Breakdown/ShotRow.tsx` - CSS grid row with 5 editable columns and action cell slot
- `frontend/src/components/Breakdown/SceneGroup.tsx` - Scene header with title/count and shot rows container
- `frontend/src/components/Breakdown/ShotlistPanel.tsx` - Main panel with React Query, optimistic mutations, scene grouping, loading/error states
- `frontend/src/components/Breakdown/BreakdownLayout.tsx` - Replaced placeholder with ShotlistPanel, removed unused List import

## Decisions Made
- Field spread on update: PUT sends `{ fields: { ...existingFields, [key]: newValue } }` to prevent JSONB wipe since backend replaces entire fields dict
- Scene grouping is frontend-only: flat API response grouped by scene_item_id with unassigned shots last
- 5 visible columns (shot_size, camera_angle, camera_movement, description, action) out of 13 total fields; remaining accessible in future detail/expansion view

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ShotlistPanel renders and edits shots; ready for Plan 02 to add delete confirmation, reorder controls, Add Shot button, and empty state CTA
- All mutations are centralized in ShotlistPanel; Plan 02 can inject controls via renderActionCell and renderAddButton render props

## Self-Check: PASSED

All 8 source files verified present. Both task commits (5465c11, 6f7dcff) verified in git log.

---
*Phase: 20-shotlist-panel*
*Completed: 2026-03-19*
