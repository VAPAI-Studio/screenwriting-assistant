---
phase: 38-show-management-ui
plan: 02
subsystem: ui
tags: [react, typescript, tanstack-query, lucide-react, tailwind, auto-save, collapsible-sections]

# Dependency graph
requires:
  - phase: 38-show-management-ui/38-01
    provides: "Show types, API methods, constants (BIBLE_SECTIONS, DURATION_PRESETS, QUERY_KEYS), ShowCard, CreateShowModal, App.tsx placeholder route"
  - phase: 37-series-bible-data-api
    provides: "Bible columns on Show model, /api/shows/{id}/bible endpoints"
provides:
  - "ShowDetail page component at /shows/:showId with header, bible editor, episode placeholder"
  - "BibleEditor component with four collapsible textarea sections and auto-save on blur"
  - "EpisodeDurationPicker component with preset and custom duration options"
  - "App.tsx route wired to real ShowDetail (replaces placeholder)"
affects: [39-episode-management, 40-bible-injection]

# Tech tracking
tech-stack:
  added: []
  patterns: [collapsible-panel-pattern, auto-save-on-blur, loaded-ref-for-query-refetch-protection]

key-files:
  created:
    - frontend/src/components/Shows/ShowDetail.tsx
    - frontend/src/components/Shows/BibleEditor.tsx
    - frontend/src/components/Shows/EpisodeDurationPicker.tsx
  modified:
    - frontend/src/App.tsx

key-decisions:
  - "No query invalidation on bible mutation success -- prevents refetch from overwriting local state"
  - "Used loaded ref pattern to initialize local state from bible props only on mount"
  - "Duration changes save immediately (no blur needed) since select/input interaction is discrete"

patterns-established:
  - "Collapsible panel: border rounded-xl with button header and conditional content render"
  - "Auto-save on blur: local state + mutation.mutate in onBlur handler + 2s saved indicator"
  - "Loaded ref: useRef(false) to guard against useEffect re-initializing state on prop change"

requirements-completed: [SHOW-03, BIBL-01, BIBL-02, BIBL-03]

# Metrics
duration: 3min
completed: 2026-03-24
---

# Phase 38 Plan 02: Show Detail & Bible Editor Summary

**Show detail page with four collapsible bible text sections (auto-save on blur), preset/custom episode duration picker, and episode list placeholder**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-24T19:28:52Z
- **Completed:** 2026-03-24T19:32:41Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- BibleEditor with four collapsible sections (Characters, World/Setting, Season Arc, Tone & Style) that auto-save on blur via PUT /api/shows/{id}/bible
- EpisodeDurationPicker with 10/22/44/60 min presets and Custom option with number input (1-480)
- ShowDetail page at /shows/:showId with show header, Series Bible section, and Episodes placeholder
- App.tsx wired with real ShowDetail component replacing the placeholder stub

## Task Commits

Each task was committed atomically:

1. **Task 1: Create BibleEditor and EpisodeDurationPicker components** - `be64147` (feat)
2. **Task 2: Create ShowDetail page and wire App.tsx route** - `333da5e` (feat)

## Files Created/Modified
- `frontend/src/components/Shows/EpisodeDurationPicker.tsx` - Duration selector with presets + custom number input
- `frontend/src/components/Shows/BibleEditor.tsx` - Four-section collapsible bible editor with auto-save on blur
- `frontend/src/components/Shows/ShowDetail.tsx` - Show detail page with header, bible, and episode placeholder
- `frontend/src/App.tsx` - Replaced placeholder ShowDetailRoute with real ShowDetail import

## Decisions Made
- No query invalidation on bible mutation success to prevent refetch from overwriting local edits
- Used `useRef(false)` loaded guard to initialize local state from bible props only on mount
- Duration changes fire mutation immediately (not on blur) since select/input changes are discrete actions

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Show management UI complete (Phase 38 done): list page, create modal, detail page with bible editor
- Ready for Phase 39 (episode management) which will replace the "Episodes coming soon" placeholder
- Ready for Phase 40 (bible injection) which will consume bible data during AI generation

## Self-Check: PASSED

All 3 created files verified on disk. Both task commits (be64147, 333da5e) verified in git log. TypeScript check shows only 3 pre-existing errors, zero new errors.

---
*Phase: 38-show-management-ui*
*Completed: 2026-03-24*
