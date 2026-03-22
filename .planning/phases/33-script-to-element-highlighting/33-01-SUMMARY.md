---
phase: 33-script-to-element-highlighting
plan: 01
subsystem: ui
tags: [react, text-highlighting, regex, breakdown-elements, navigation]

# Dependency graph
requires:
  - phase: 32-element-detail-page
    provides: ROUTES.ELEMENT_DETAIL, ElementDetailPage route
  - phase: 17-data-foundation
    provides: BreakdownElement model, getBreakdownElements API
provides:
  - buildHighlightSegments pure text-segmentation utility
  - HighlightedScriptText React component with tooltip and click navigation
  - CATEGORY_COLORS constant for breakdown category color mapping
  - CSS highlight classes for 5 breakdown categories
  - ScriptReadView wired with elements query and highlighted text
affects: [breakdown-mode, script-read-view, element-navigation]

# Tech tracking
tech-stack:
  added: []
  patterns: [react-text-segmentation, regex-longest-match-first, css-category-colors]

key-files:
  created:
    - frontend/src/lib/textHighlight.ts
    - frontend/src/components/Breakdown/HighlightedScriptText.tsx
  modified:
    - frontend/src/lib/constants.ts
    - frontend/src/index.css
    - frontend/src/components/Breakdown/ScriptReadView.tsx

key-decisions:
  - "CSS-only tooltip via title attribute for zero-dependency hover hints"
  - "Word-boundary regex with longest-match-first ordering to avoid partial matches"
  - "stopPropagation + removeAllRanges on highlight click to avoid conflicting with text selection for shots"

patterns-established:
  - "Text segmentation: pure function returns TextSegment[] then React component renders spans"
  - "Category colors: CATEGORY_COLORS constant + CSS classes for per-category underline colors"

requirements-completed: [SEL-01]

# Metrics
duration: 2min
completed: 2026-03-22
---

# Phase 33 Plan 01: Script-to-Element Highlighting Summary

**Color-coded underline highlighting for breakdown elements in ScriptReadView with word-boundary regex matching, hover tooltips, and click-to-detail navigation**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-22T17:18:26Z
- **Completed:** 2026-03-22T17:20:14Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Built pure text-segmentation utility with case-insensitive, longest-match-first regex that handles special characters in element names
- Created HighlightedScriptText React component rendering category-colored underline spans with native tooltips and click navigation to element detail pages
- Wired ScriptReadView to fetch all breakdown elements and render highlighted text instead of raw content, preserving text-selection-to-shot functionality

## Task Commits

Each task was committed atomically:

1. **Task 1: Text highlight utility, React component, CSS classes, and CATEGORY_COLORS constant** - `abc17f8` (feat)
2. **Task 2: Wire HighlightedScriptText into ScriptReadView with elements query** - `6bf92c0` (feat)

## Files Created/Modified
- `frontend/src/lib/textHighlight.ts` - Pure buildHighlightSegments function with escapeRegex, ElementMatch, TextSegment types
- `frontend/src/components/Breakdown/HighlightedScriptText.tsx` - React component rendering highlight spans with tooltip and click navigation
- `frontend/src/lib/constants.ts` - Added CATEGORY_COLORS record for 5 breakdown categories
- `frontend/src/index.css` - Added .element-highlight CSS classes with per-category underline colors
- `frontend/src/components/Breakdown/ScriptReadView.tsx` - Added elements query and replaced raw text with HighlightedScriptText

## Decisions Made
- Used native HTML `title` attribute for tooltips (zero dependencies, sufficient for MVP)
- Word-boundary regex (`\b`) with elements sorted by name length descending for longest-match-first
- Used `e.stopPropagation()` and `window.getSelection()?.removeAllRanges()` on highlight clicks to prevent conflict with text-selection shot creation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All 5 breakdown categories (character, location, prop, wardrobe, vehicle) are highlighted with distinct colors
- Element detail page navigation works from highlighted text
- Text selection for shots remains functional alongside highlights
- Ready for any future UX enhancements (toggle highlights, richer tooltips)

## Self-Check: PASSED

All files exist, all commits verified.

---
*Phase: 33-script-to-element-highlighting*
*Completed: 2026-03-22*
