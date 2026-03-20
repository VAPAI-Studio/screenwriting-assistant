---
phase: 23-assets-panel-media-display
plan: 01
subsystem: ui
tags: [react, typescript, tailwind, react-query, vite, breakdown, assets]

# Dependency graph
requires:
  - phase: 22-media-upload-backend
    provides: Media upload/download API and file storage
  - phase: 18-two-mode-ui-shell
    provides: BreakdownLayout 3-panel skeleton and breakdown-mode CSS scope
provides:
  - AssetMedia TypeScript interface for media objects
  - listElementMedia, uploadMedia, deleteMedia API functions
  - ELEMENT_MEDIA and PROJECT_MEDIA React Query keys
  - Script/Assets toggle in breakdown left panel
  - AssetsPanel with category-grouped breakdown element browsing
  - AssetElementCard with collapsible expand/collapse
  - Vite /media proxy for dev server
affects: [23-02-media-display, 24-ai-chat]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "display:none/contents toggle for state-preserving view switching (ASST-05)"
    - "Audio overlap prevention via useRef callback pattern"

key-files:
  created:
    - frontend/src/components/Breakdown/AssetsPanel.tsx
    - frontend/src/components/Breakdown/AssetElementCard.tsx
  modified:
    - frontend/src/types/index.ts
    - frontend/src/lib/api.tsx
    - frontend/src/lib/constants.ts
    - frontend/vite.config.ts
    - frontend/src/components/Breakdown/BreakdownLayout.tsx

key-decisions:
  - "Both Script and Assets views always mounted in DOM (display:none toggle) to preserve scroll position and expanded state across toggles"
  - "Audio overlap prevention refs (currentlyPlayingId, stopCurrentAudio) placed in AssetsPanel as useRef for Plan 02 consumption"
  - "Empty categories hidden entirely rather than shown with zero count"

patterns-established:
  - "display:none/contents toggle: hide/show sibling views without unmounting to preserve React state and scroll position"

requirements-completed: [ASST-01, ASST-02, ASST-05]

# Metrics
duration: 3min
completed: 2026-03-20
---

# Phase 23 Plan 01: Assets Panel Foundation Summary

**Script/Assets toggle with category-grouped breakdown element browsing, media API functions, and Vite /media proxy**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-20T12:34:56Z
- **Completed:** 2026-03-20T12:37:40Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Left panel in breakdown mode now has Script/Assets toggle buttons with active/inactive visual states
- Assets view shows breakdown elements grouped by category (Characters, Locations, Props, Wardrobe, Vehicles) with sticky headers and element counts
- AssetElementCard expands/collapses on click with chevron indicators and accordion animation
- AssetMedia type, 3 API functions (listElementMedia, uploadMedia, deleteMedia), 2 query keys, and /media Vite proxy ready for Plan 02
- Both views always mounted in DOM -- toggling preserves scroll position, expanded elements, and React Query subscriptions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add AssetMedia type, media API functions, query keys, and Vite proxy** - `0a91fc8` (feat)
2. **Task 2: Add Script/Assets toggle to BreakdownLayout and create AssetsPanel with AssetElementCard** - `689ef24` (feat)

## Files Created/Modified
- `frontend/src/types/index.ts` - Added AssetMedia interface with image/audio file_type union
- `frontend/src/lib/api.tsx` - Added listElementMedia, uploadMedia, deleteMedia API functions
- `frontend/src/lib/constants.ts` - Added ELEMENT_MEDIA, PROJECT_MEDIA query keys and BREAKDOWN_LEFT_PANEL_VIEW storage key
- `frontend/vite.config.ts` - Added /media proxy entry for dev server
- `frontend/src/components/Breakdown/AssetsPanel.tsx` - Category-grouped element list with sticky headers and empty state
- `frontend/src/components/Breakdown/AssetElementCard.tsx` - Collapsible element card with chevron expand/collapse
- `frontend/src/components/Breakdown/BreakdownLayout.tsx` - Script/Assets toggle, dual-mounted views with display:none switching

## Decisions Made
- Both Script and Assets views always mounted in DOM (display:none toggle, not conditional rendering) to preserve scroll position, expanded state, and React Query subscriptions when toggling (ASST-05)
- Audio overlap prevention refs (currentlyPlayingId, stopCurrentAudio) placed as useRef in AssetsPanel, ready for Plan 02 audio player consumption
- Empty categories hidden entirely rather than shown with zero count (matches UI-SPEC requirement)
- uploadMedia uses Authorization-only header (no Content-Type) to let browser set multipart boundary automatically, matching existing uploadBook pattern

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- 3 pre-existing TypeScript errors in unrelated files (IndividualEditorView.tsx, RepeatableCardsView.tsx, SidebarChat.tsx) cause `npm run build` to fail. These are NOT caused by this plan's changes and are out of scope. Zero errors in files modified by this plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All types, API functions, query keys, and Vite proxy ready for Plan 02 (MediaThumbnail, AudioPlayer, MediaUploadZone)
- AssetsPanel has audio overlap prevention refs ready for Plan 02 wiring
- AssetElementCard has placeholder comments marking exactly where Plan 02 components will be inserted

---
*Phase: 23-assets-panel-media-display*
*Completed: 2026-03-20*
