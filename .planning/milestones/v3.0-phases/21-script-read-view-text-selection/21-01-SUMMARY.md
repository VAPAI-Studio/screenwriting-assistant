---
phase: 21-script-read-view-text-selection
plan: 01
subsystem: ui
tags: [react, text-selection, screenplay, shots, react-query, lucide-react]

# Dependency graph
requires:
  - phase: 20-shotlist-panel
    provides: Shot CRUD API, ShotlistPanel, shot types and query keys
  - phase: 19-shot-crud-api-core-model
    provides: Shot model and API endpoints
provides:
  - ScriptReadView component rendering read-only screenplay content by scene
  - SelectionBar floating component for text selection with Add Shot action
  - Text selection detection with scene resolution via data-scene-id
  - Shot creation from selected text with scene linkage
affects: [22-shot-detail-expansion, 23-breakdown-page, 24-ai-chat-panel]

# Tech tracking
tech-stack:
  added: []
  patterns: [text-selection-detection, floating-toolbar, data-attribute-scene-resolution]

key-files:
  created:
    - frontend/src/components/Breakdown/ScriptReadView.tsx
    - frontend/src/components/Breakdown/SelectionBar.tsx
  modified:
    - frontend/src/components/Breakdown/BreakdownLayout.tsx

key-decisions:
  - "No new dependencies -- used existing React, React Query, and lucide-react"
  - "Text selection uses selectionchange event with Safari mouseup fallback for cross-browser support"
  - "Scene resolution walks from selection anchor node to nearest [data-scene-id] ancestor"

patterns-established:
  - "Text selection detection: selectionchange + mouseup Safari fallback pattern"
  - "Floating action bar: position fixed near selection rect with outside click/Escape/X dismiss"
  - "Scene-to-shot linkage: data-scene-id attributes on rendered screenplay sections"

requirements-completed: [SELC-01, SELC-02, SELC-03, SELC-04, SELC-05]

# Metrics
duration: 2min
completed: 2026-03-19
---

# Phase 21 Plan 01: Script Read View & Text Selection Summary

**Read-only screenplay rendering with text selection detection, floating SelectionBar, and shot creation from selected script text linked to scenes**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-19T20:39:58Z
- **Completed:** 2026-03-19T20:42:40Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- ScriptReadView renders screenplay content organized by scene with sticky headers and data-scene-id attributes
- Text selection detection via selectionchange event with Safari mouseup fallback resolves scene context
- SelectionBar floating toolbar shows line count, + Add Shot button, and dismiss controls (outside click, Escape, X)
- Shot creation from selection pre-populates script_text and links to correct scene via scene_item_id
- BreakdownLayout left panel now renders ScriptReadView instead of Phase 21 placeholder

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ScriptReadView and SelectionBar components** - `023a6ee` (feat)
2. **Task 2: Wire ScriptReadView into BreakdownLayout left panel** - `cdea41a` (feat)

## Files Created/Modified
- `frontend/src/components/Breakdown/ScriptReadView.tsx` - Fetches screenplay + scene data, renders read-only text, detects selection, creates shots
- `frontend/src/components/Breakdown/SelectionBar.tsx` - Floating bar with line count, Add Shot button, and dismiss controls
- `frontend/src/components/Breakdown/BreakdownLayout.tsx` - Wires ScriptReadView into left panel with projectId from useParams

## Decisions Made
- No new dependencies -- leveraged existing React Query, lucide-react stack
- Text selection uses selectionchange event with mouseup fallback for Safari cross-browser support
- Scene resolution via closest('[data-scene-id]') ancestor walk from selection anchor node
- Shot numbering and sort_order calculated from existing shots in the same scene group (same pattern as ShotlistPanel)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing TypeScript errors in unrelated files (IndividualEditorView.tsx, RepeatableCardsView.tsx, SidebarChat.tsx) cause `npm run build` to fail at `tsc` step. These errors exist on main branch before any changes. Our new/modified files compile clean with zero errors.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Left panel script view complete, ready for Phase 22+ features
- Right panel AI Chat placeholder remains for Phase 24
- Shot detail/expansion view can build on the shots created via text selection

---
*Phase: 21-script-read-view-text-selection*
*Completed: 2026-03-19*
