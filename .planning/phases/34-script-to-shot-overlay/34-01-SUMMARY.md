---
phase: 34-script-to-shot-overlay
plan: 01
subsystem: ui
tags: [react, typescript, shot-overlay, popover, text-highlighting]

# Dependency graph
requires:
  - phase: 33-script-to-element-highlighting
    provides: "HighlightedScriptText component with element underline highlights"
  - phase: 20-shotlist-panel
    provides: "Shot CRUD API and shots query in ScriptReadView"
provides:
  - "buildShotOverlayRanges utility for substring-based shot coverage detection"
  - "ShotOverlayPopover component for showing linked shots on click"
  - "Two-layer highlighting (element underlines + shot background tint) in HighlightedScriptText"
  - ".shot-overlay CSS class with steel-blue background tint"
affects: [storyboard-mode, script-read-view]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Two-layer text highlighting with segment sub-splitting", "Character-level coverage array for substring matching"]

key-files:
  created:
    - frontend/src/lib/shotOverlay.ts
    - frontend/src/components/Breakdown/ShotOverlayPopover.tsx
  modified:
    - frontend/src/components/Breakdown/HighlightedScriptText.tsx
    - frontend/src/components/Breakdown/ScriptReadView.tsx
    - frontend/src/index.css

key-decisions:
  - "indexOf-based case-sensitive substring matching for shot.script_text to text mapping"
  - "Character-level Set<Shot> coverage array merged into contiguous ShotOverlayRange spans"
  - "Element-highlight click takes priority over shot-overlay click via stopPropagation"
  - "Segment sub-splitting approach to handle partial overlap between element highlights and shot ranges"

patterns-established:
  - "Two-layer highlight pattern: element underlines (text-decoration) coexist with shot background tint (background-color)"
  - "splitSegmentByShotRanges helper for sub-dividing text segments across overlay boundaries"

requirements-completed: [SSO-01]

# Metrics
duration: 2min
completed: 2026-03-22
---

# Phase 34 Plan 01: Script-to-Shot Overlay Summary

**Shot-coverage overlay with indexOf-based substring matching, steel-blue background tint, and click-to-popover showing linked shot details**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-22T17:35:52Z
- **Completed:** 2026-03-22T17:38:15Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Created buildShotOverlayRanges utility that finds shot.script_text occurrences in screenplay text and builds merged coverage ranges
- Created ShotOverlayPopover with fixed positioning, click-outside/Escape dismiss, and shot details (number, size, angle, description)
- Modified HighlightedScriptText to support two-layer highlighting: element underlines and shot background tints coexist without conflict
- Added .shot-overlay CSS class with steel-blue 12% opacity (22% on hover)

## Task Commits

Each task was committed atomically:

1. **Task 1: Shot overlay utility, popover component, and CSS classes** - `a3936be` (feat)
2. **Task 2: Integrate shot overlay into HighlightedScriptText and wire from ScriptReadView** - `dc3a9d5` (feat)

## Files Created/Modified
- `frontend/src/lib/shotOverlay.ts` - Pure utility: buildShotOverlayRanges with indexOf-based substring matching and Set<Shot> coverage array
- `frontend/src/components/Breakdown/ShotOverlayPopover.tsx` - Fixed-position popover showing linked shots with number, size, angle, description
- `frontend/src/components/Breakdown/HighlightedScriptText.tsx` - Added shots prop, useMemo overlay ranges, segment sub-splitting, and popover state
- `frontend/src/components/Breakdown/ScriptReadView.tsx` - Passes existing shots query data to HighlightedScriptText
- `frontend/src/index.css` - Added .shot-overlay and .shot-overlay:hover CSS classes

## Decisions Made
- Used indexOf-based case-sensitive matching (not regex) for script_text lookup -- consistent with how text was selected from the script
- Character-level Set<Shot> coverage array ensures overlapping shot references are correctly merged into single ranges
- Element-highlight clicks take priority over shot-overlay clicks via existing stopPropagation pattern
- Segment sub-splitting handles partial overlap between element names and shot ranges cleanly

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Shot-coverage overlay is fully functional in breakdown mode's script read view
- Element underline highlights and shot background highlights coexist correctly
- Ready for any future phases that extend the script read view or storyboard features

## Self-Check: PASSED

All files verified present. All commit hashes verified in git log.

---
*Phase: 34-script-to-shot-overlay*
*Completed: 2026-03-22*
