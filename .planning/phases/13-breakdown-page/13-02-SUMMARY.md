---
phase: 13-breakdown-page
plan: "02"
subsystem: ui
tags: [react, typescript, radix-ui, react-query, inline-editing, optimistic-update]

# Dependency graph
requires:
  - phase: 13-breakdown-page
    plan: "01"
    provides: TypeScript types, API client methods, QUERY_KEYS, ROUTES, PhaseNavigation Breakdown tab, BreakdownPage stub
provides:
  - BreakdownPage full implementation at frontend/src/components/Breakdown/BreakdownPage.tsx
  - StalenessBar amber banner with Refresh button at frontend/src/components/Breakdown/StalenessBar.tsx
  - CategoryTabs Radix Tabs with count badges at frontend/src/components/Breakdown/CategoryTabs.tsx
  - ElementList per-category query with skeleton loaders at frontend/src/components/Breakdown/ElementList.tsx
  - ElementCard inline editing with optimistic PUT mutation and scene chips at frontend/src/components/Breakdown/ElementCard.tsx
affects:
  - 13-03 (ElementCard and ElementList used directly; Add Element dialog will be added to CategoryTabs or ElementList)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Radix Tabs.Root with data-[state=active] CSS for amber active border-b-2 pattern"
    - "Optimistic useMutation with onMutate cancel/snapshot, onError rollback, onSettled dual-invalidate (BREAKDOWN_ELEMENTS + BREAKDOWN_SUMMARY)"
    - "Inline edit with 150ms blur debounce to allow confirm-button click before save fires"
    - "Elements enabled: isActive to avoid N parallel queries on tab mount"

key-files:
  created:
    - frontend/src/components/Breakdown/BreakdownPage.tsx
    - frontend/src/components/Breakdown/StalenessBar.tsx
    - frontend/src/components/Breakdown/CategoryTabs.tsx
    - frontend/src/components/Breakdown/ElementList.tsx
    - frontend/src/components/Breakdown/ElementCard.tsx
  modified: []

key-decisions:
  - "StalenessBar only renders when is_stale=true AND total_elements > 0 -- avoids showing banner on empty breakdown"
  - "ElementList enabled only when isActive -- prevents 5 parallel API calls on Breakdown page mount"
  - "Scene chips use link.scene_item_id (not element.id) for navigation -- correct routing to scene in workspace"
  - "onSettled invalidates both BREAKDOWN_ELEMENTS and BREAKDOWN_SUMMARY after any PUT -- keeps counts in sync"
  - "ElementCard tracks editName/editDescription local state; only fires PUT if values actually changed"

patterns-established:
  - "Dual-invalidate pattern: PUT mutation always invalidates both element list AND summary (count changes on user_modified)"
  - "isActive guard on ElementList queries to avoid unnecessary backend calls"

requirements-completed:
  - UI-02
  - UI-03
  - UI-04
  - UI-05
  - UI-06

# Metrics
duration: 5min
completed: 2026-03-14
---

# Phase 13 Plan 02: Breakdown Page Layout Summary

**Radix Tabs category layout with optimistic inline-editing ElementCards, source badges, scene chips, and staleness banner — full BreakdownPage replacing stub from Plan 13-01**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-14T14:57:24Z
- **Completed:** 2026-03-14T15:02:00Z
- **Tasks:** 2 of 3 (Task 3 is a human-verify checkpoint — awaiting approval)
- **Files created:** 5

## Accomplishments
- BreakdownPage: project/template queries, extractMutation, PhaseNavigation with isBreakdownActive=true, StalenessBar conditional render
- StalenessBar: amber banner with Refresh button showing spinner + disabled state during extraction
- CategoryTabs: Radix Tabs with 5 category triggers, count badges from summary.counts_by_category, amber active state
- ElementList: per-category React Query fetch (enabled only when tab isActive), 3-skeleton loader, empty message
- ElementCard: source badge (AI=blue, User=green), user_modified pencil icon, inline name/description editing with optimistic update + rollback, scene chips navigating via scene_item_id

## Task Commits

Each task was committed atomically:

1. **Task 1: BreakdownPage shell and StalenessBar** - `2f48218` (feat)
2. **Task 2: CategoryTabs, ElementList, ElementCard** - `a4b3a4c` (feat)
3. **Task 3: Human verification checkpoint** - awaiting

## Files Created/Modified
- `frontend/src/components/Breakdown/BreakdownPage.tsx` - Full page shell replacing stub; PhaseNavigation + StalenessBar + CategoryTabs
- `frontend/src/components/Breakdown/StalenessBar.tsx` - Amber staleness banner with Refresh/Extracting button
- `frontend/src/components/Breakdown/CategoryTabs.tsx` - Radix Tabs with category count badges
- `frontend/src/components/Breakdown/ElementList.tsx` - Per-category fetch with skeleton loaders and ElementCard list
- `frontend/src/components/Breakdown/ElementCard.tsx` - Inline editing, source badges, user_modified indicator, scene chips

## Decisions Made
- StalenessBar only renders when `is_stale=true AND total_elements > 0` to avoid showing the warning banner on a completely empty breakdown
- ElementList query enabled only when `isActive` to prevent 5 simultaneous backend calls when the page first loads
- Scene chips use `link.scene_item_id` (not `element.id`) per plan requirement — correct routing to the scene in the workspace
- onSettled invalidates both BREAKDOWN_ELEMENTS and BREAKDOWN_SUMMARY because user edits can affect element counts
- ElementCard tracks local edit state and only fires PUT mutation if the saved values actually differ from original

## Deviations from Plan

None - plan executed exactly as written.

Pre-existing TypeScript errors in IndividualEditorView.tsx, RepeatableCardsView.tsx, SidebarChat.tsx are unchanged (documented in deferred-items.md from Plan 13-01). Vite build passes cleanly.

## Issues Encountered
- Pre-existing TypeScript errors (3 files) prevent `tsc --noEmit` from exiting 0. These are out of scope — already logged in deferred-items.md. Vite build (the actual deployment build) passes cleanly.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Breakdown page is fully functional for viewing and editing elements
- Task 3 checkpoint awaits human verification of the running application
- Plan 13-03 will add the Add Element dialog and empty state CTA

---
*Phase: 13-breakdown-page*
*Completed: 2026-03-14*

## Self-Check: PASSED

All 5 created files found. Both task commits verified.
