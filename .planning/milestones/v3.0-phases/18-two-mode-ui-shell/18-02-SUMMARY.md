---
phase: 18-two-mode-ui-shell
plan: 02
subsystem: ui
tags: [react, typescript, tailwind, css-variables, localStorage, lucide-react, react-router]

# Dependency graph
requires:
  - phase: 18-01
    provides: ".breakdown-mode CSS palette block, STORAGE_KEYS breakdown panel keys, ModeToggle navigation"
provides:
  - "BreakdownLayout.tsx — three-panel layout component with mode class lifecycle, resize handles, and collapse state"
  - "BreakdownPanel.tsx — reusable panel wrapper with header, collapse button, and collapsed 36px strip"
  - "App.tsx route /projects/:projectId/breakdown wired to BreakdownLayout"
affects:
  - 18-03
  - 19-shotlist-model
  - 20-shotlist-ui
  - 21-script-view
  - 24-ai-chat-panel
  - breakdown-layout

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Three-panel layout with flex-1 center + fixed-width resizable left/right panels"
    - "Drag handle delta direction: left panel widens on drag-right, right panel widens on drag-left"
    - "localStorage panel state init via useState lazy initializer (readStoredWidth/readStoredBool helpers)"
    - "latestXWidth ref pattern to capture current state in document-level event listeners"
    - "Collapse-to-strip with vertical rotated label (writingMode: vertical-rl, rotate 180deg)"

key-files:
  created:
    - frontend/src/components/Breakdown/BreakdownPanel.tsx
    - frontend/src/components/Breakdown/BreakdownLayout.tsx
  modified:
    - frontend/src/App.tsx

key-decisions:
  - "BreakdownPage import commented out (not deleted) in App.tsx — reserved for Phase 23 assets panel integration; TypeScript noUnusedLocals prevented keeping as live import"
  - "Drag handles hidden when panel is collapsed to avoid ghost resize target"
  - "Max panel width capped at 45% viewport so center always remains visible"

patterns-established:
  - "Breakdown panel resize: useRef for dragging state + latestWidth refs + document-level mousemove/mouseup listeners with cleanup"
  - "Panel persistence: lazy useState initializer reads localStorage on mount, mouseup handler writes on drag end"

requirements-completed: [MODE-02, MODE-03, MODE-05]

# Metrics
duration: 3min
completed: 2026-03-19
---

# Phase 18 Plan 02: Two-Mode UI Shell — Breakdown Layout Summary

**Three-panel BreakdownLayout with resize handles, collapse-to-strip panels, and localStorage persistence wired to /projects/:id/breakdown route**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-19T18:16:07Z
- **Completed:** 2026-03-19T18:19:00Z
- **Tasks:** 3
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments
- Created `BreakdownPanel.tsx` — reusable panel wrapper: expanded state shows header with collapse button; collapsed state renders 36px strip with vertical title and expand button; arrow direction per side
- Created `BreakdownLayout.tsx` — root breakdown route component: adds/removes `.breakdown-mode` class on `document.documentElement` via `useEffect` cleanup; three panels (Script/Assets left, Shotlist center, AI Chat right); drag handles with correct delta direction per side; min 200px / max 45% viewport; all widths and collapsed states persisted in `localStorage` via `STORAGE_KEYS` constants
- Wired `BreakdownLayout` into `App.tsx` on `/projects/:projectId/breakdown` route, replacing `BreakdownPage`; route order preserved (specific before wildcard)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create BreakdownPanel reusable panel wrapper** - `055cd0e` (feat)
2. **Task 2: Create BreakdownLayout with 3-panel skeleton, mode class lifecycle, and resize/collapse state** - `cab929b` (feat)
3. **Task 3: Wire BreakdownLayout into App.tsx, replacing BreakdownPage on the breakdown route** - `644514f` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `frontend/src/components/Breakdown/BreakdownPanel.tsx` - Reusable panel with expanded/collapsed rendering, collapse button, and vertical label strip
- `frontend/src/components/Breakdown/BreakdownLayout.tsx` - Three-panel breakdown route component with mode class lifecycle, drag resize, and localStorage persistence
- `frontend/src/App.tsx` - Added BreakdownLayout import; replaced BreakdownPage element on breakdown route; preserved route order

## Decisions Made
- `BreakdownPage` import commented out in `App.tsx` with Phase 23 note: TypeScript's `noUnusedLocals: true` prevented keeping it as a live unused import; a comment-retained import satisfies plan intent and passes TypeScript
- Drag handles hidden (`{!collapsed && ...}`) when panel is collapsed — prevents ghost resize target in collapsed state
- Max panel width set to 45% `window.innerWidth` — guarantees center panel always has at least ~10% visible regardless of viewport size

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Commented out unused BreakdownPage import to fix TS6133 error**
- **Found during:** Task 3 (wire BreakdownLayout into App.tsx)
- **Issue:** Plan instructed to keep `BreakdownPage` import live (for Phase 23), but TypeScript `noUnusedLocals: true` in tsconfig.json flagged it as TS6133 error, blocking build
- **Fix:** Converted live import to commented import with `// BreakdownPage retained for Phase 23 assets panel integration` note
- **Files modified:** `frontend/src/App.tsx`
- **Verification:** `tsc --noEmit` shows only pre-existing errors (no new TS6133)
- **Committed in:** `644514f` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug fix to pass TypeScript strict check)
**Impact on plan:** Minimal — BreakdownPage preserved as commented import with clear Phase 23 reference. Plan artifact intent maintained.

## Issues Encountered
- `npm run lint` still fails with missing ESLint config — pre-existing issue documented in Plan 01 SUMMARY, not caused by Plan 02 changes. Verified correctness via `tsc --noEmit`.
- `npm run build` fails due to 3 pre-existing TS errors in `IndividualEditorView.tsx`, `RepeatableCardsView.tsx`, and `SidebarChat.tsx` — confirmed pre-existing by running tsc before and after changes. No new errors introduced. Deferred per Plan 01 documentation.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Breakdown route `/projects/:id/breakdown` now renders the steel-blue three-panel layout
- Navigating away removes `.breakdown-mode` from `<html>`, restoring amber palette
- Panel widths/collapse state persist across refreshes via localStorage
- Left panel placeholder ready for Phase 21 (Script View)
- Center panel placeholder ready for Phase 20 (Shotlist)
- Right panel placeholder ready for Phase 24 (AI Chat)
- Phase 18 Two-Mode UI Shell is complete (Plans 01 and 02 done)

---
*Phase: 18-two-mode-ui-shell*
*Completed: 2026-03-19*
