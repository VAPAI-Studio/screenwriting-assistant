---
phase: 20-shotlist-panel
plan: 02
subsystem: ui
tags: [react, typescript, react-query, optimistic-mutations, delete-confirmation, reorder, empty-state]

# Dependency graph
requires:
  - phase: 20-shotlist-panel
    provides: ShotlistPanel, SceneGroup, ShotRow with render prop slots for action controls
  - phase: 19-shot-crud-api-core-model
    provides: Shot CRUD API endpoints (create, delete, reorder)
provides:
  - DeleteShotButton component with two-click confirmation and 3s auto-dismiss
  - ReorderControls component with up/down arrow buttons
  - AddShotButton ghost button for scene-level shot creation
  - ShotlistEmptyState component with icon, heading, body, and CTA
  - Create, delete, and reorder mutations with optimistic updates in ShotlistPanel
affects: [21-script-read-view, 24-ai-chat-breakdown]

# Tech tracking
tech-stack:
  added: []
  patterns: [two-click-delete-with-auto-dismiss, optimistic-sort-order-swap, render-prop-action-injection]

key-files:
  created:
    - frontend/src/components/Breakdown/DeleteShotButton.tsx
    - frontend/src/components/Breakdown/ReorderControls.tsx
    - frontend/src/components/Breakdown/AddShotButton.tsx
    - frontend/src/components/Breakdown/ShotlistEmptyState.tsx
  modified:
    - frontend/src/components/Breakdown/ShotlistPanel.tsx

key-decisions:
  - "Empty state CTA creates shot with scene_item_id: null (unassigned) -- simplest approach, user can reassign later"
  - "Reorder swaps sort_order values between adjacent shots rather than recalculating all -- minimizes API payload"
  - "Action controls (reorder + delete) use opacity-0 group-hover:opacity-100 for hover-reveal -- reduces visual noise"

patterns-established:
  - "Two-click delete: Trash2 icon -> 'Delete?' text button with 3s setTimeout auto-dismiss -> confirm deletes"
  - "Render prop injection: parent provides renderActionCell and renderAddButton callbacks, child renders them in slots"
  - "Optimistic sort_order swap: swap sort_order values between two shots, re-sort cache array by scene then sort_order"

requirements-completed: [SHOT-05, SHOT-06, SHOT-08]

# Metrics
duration: 2min
completed: 2026-03-19
---

# Phase 20 Plan 02: Shotlist Panel Interactions Summary

**Delete confirmation, reorder arrows, add-shot buttons, and empty state CTA completing full shotlist CRUD interactions with optimistic React Query mutations**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-19T19:48:10Z
- **Completed:** 2026-03-19T19:50:55Z
- **Tasks:** 2
- **Files modified:** 5 (4 created, 1 modified)

## Accomplishments
- DeleteShotButton with two-click confirmation matching ElementCard pattern (trash icon -> "Delete?" -> confirm or 3s auto-dismiss)
- ReorderControls with ChevronUp/ChevronDown arrows, disabled states for first/last shot, calling /reorder endpoint
- AddShotButton ghost button at bottom of each scene group with auto-increment shot_number and sort_order
- ShotlistEmptyState with List icon, "No shots yet" heading, body copy, and "Add First Shot" CTA
- Three new optimistic mutations (create, delete, reorder) wired into ShotlistPanel with rollback on error

## Task Commits

Each task was committed atomically:

1. **Task 1: Create DeleteShotButton, ReorderControls, AddShotButton, ShotlistEmptyState components** - `cb7a105` (feat)
2. **Task 2: Wire create/delete/reorder mutations into ShotlistPanel and render action controls** - `a669c6b` (feat)

## Files Created/Modified
- `frontend/src/components/Breakdown/DeleteShotButton.tsx` - Two-click delete with 3s auto-dismiss timer
- `frontend/src/components/Breakdown/ReorderControls.tsx` - Up/down arrow buttons with disabled states for boundary shots
- `frontend/src/components/Breakdown/AddShotButton.tsx` - Ghost button with Plus icon for adding shots within scene groups
- `frontend/src/components/Breakdown/ShotlistEmptyState.tsx` - Centered empty state with List icon, heading, body, and primary CTA
- `frontend/src/components/Breakdown/ShotlistPanel.tsx` - Added createMutation, deleteMutation, reorderMutation; replaced placeholder empty state; wired renderActionCell and renderAddButton props

## Decisions Made
- Empty state CTA creates shot with `scene_item_id: null` (unassigned) -- simplest approach, user can reassign later
- Reorder swaps sort_order values between adjacent shots rather than recalculating all -- minimizes API payload
- Action controls use `opacity-0 group-hover:opacity-100` for hover-reveal to reduce visual noise

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Shotlist panel is fully interactive: create, edit, delete, and reorder shots all working with optimistic updates
- Phase 20 (shotlist-panel) is complete -- all 6 requirements (SHOT-03 through SHOT-08) fulfilled across Plans 01 and 02
- Ready for Phase 21 (script-read-view) and Phase 24 (ai-chat-breakdown) which depend on shot data

## Self-Check: PASSED

All 5 source files verified present. Both task commits (cb7a105, a669c6b) verified in git log.

---
*Phase: 20-shotlist-panel*
*Completed: 2026-03-19*
