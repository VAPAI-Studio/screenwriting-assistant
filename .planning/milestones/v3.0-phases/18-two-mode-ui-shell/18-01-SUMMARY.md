---
phase: 18-two-mode-ui-shell
plan: 01
subsystem: ui
tags: [react, radix-ui, tailwind, css-variables, react-router, typescript]

# Dependency graph
requires: []
provides:
  - ".breakdown-mode CSS variable block with steel-blue palette in index.css"
  - "STORAGE_KEYS for four breakdown panel state keys in constants.ts"
  - "ModeToggle component using Radix DropdownMenu for screenwriting/breakdown navigation"
  - "Header.tsx wired with ModeToggle between logo and nav"
affects:
  - 18-02
  - breakdown-layout
  - breakdown-mode

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CSS variables scoped to .breakdown-mode class for visual identity separation"
    - "ModeToggle self-guards via useParams — returns null outside project routes, no conditional rendering needed in parent"
    - "Three-part header layout: logo | mode-toggle | nav (gap-4 + ml-auto pattern)"

key-files:
  created:
    - frontend/src/components/Layout/ModeToggle.tsx
  modified:
    - frontend/src/index.css
    - frontend/src/lib/constants.ts
    - frontend/src/components/Layout/Header.tsx

key-decisions:
  - "Used .breakdown-mode CSS class scoped to :root descendants (not data attribute) for palette override"
  - "ModeToggle returns null when projectId is absent from useParams — single component handles its own visibility guard"
  - "Pre-existing TS build errors in unrelated files (IndividualEditorView, RepeatableCardsView, SidebarChat) are out of scope — deferred"

patterns-established:
  - "Mode-scoped CSS: add .mode-name block inside @layer base to override CSS custom properties per UI mode"
  - "Self-guarding component pattern: component reads useParams and returns null if context absent"

requirements-completed: [MODE-01, MODE-04, MODE-05]

# Metrics
duration: 12min
completed: 2026-03-19
---

# Phase 18 Plan 01: Two-Mode UI Shell Foundation Summary

**Steel-blue .breakdown-mode CSS palette, four panel STORAGE_KEYS, and Radix ModeToggle dropdown wired into Header between logo and nav**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-19T18:00:00Z
- **Completed:** 2026-03-19T18:12:00Z
- **Tasks:** 3
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- Added `.breakdown-mode` CSS block with 18 custom property overrides (steel-blue palette replacing warm amber) and body transition in `index.css`
- Extended `STORAGE_KEYS` with four breakdown panel persistence keys (`BREAKDOWN_LEFT_WIDTH`, `BREAKDOWN_RIGHT_WIDTH`, `BREAKDOWN_LEFT_COLLAPSED`, `BREAKDOWN_RIGHT_COLLAPSED`)
- Created `ModeToggle.tsx` — Radix DropdownMenu with screenwriting/breakdown items, self-guards to null outside project routes, navigates via `ROUTES.PROJECT_BREAKDOWN` and `ROUTES.PROJECT`
- Wired `ModeToggle` into `Header.tsx` center slot with three-part layout (logo | toggle | nav)

## Task Commits

Each task was committed atomically:

1. **Task 1: .breakdown-mode CSS variables and body transition** - `1710eb4` (feat)
2. **Task 2: STORAGE_KEYS and ModeToggle component** - `a3de95a` (feat)
3. **Task 3: Wire ModeToggle into Header.tsx** - `c039fd4` (feat)

## Files Created/Modified
- `frontend/src/index.css` - Added transition to body rule; added .breakdown-mode block with 18 CSS variable overrides
- `frontend/src/lib/constants.ts` - Added 4 BREAKDOWN_* keys to STORAGE_KEYS
- `frontend/src/components/Layout/ModeToggle.tsx` - New component: Radix DropdownMenu mode switcher
- `frontend/src/components/Layout/Header.tsx` - Import + render ModeToggle; three-part layout with gap-4 and ml-auto

## Decisions Made
- Used `.breakdown-mode` CSS class (not a data attribute) for palette override — consistent with Tailwind's class-based theming approach already in use
- ModeToggle self-guards via `useParams` returning null when `projectId` is absent, so no conditional render needed in Header
- Pre-existing TS errors in three unrelated files are logged as deferred (out of scope per deviation rules)

## Deviations from Plan

None - plan executed exactly as written.

Note: `npm run lint` failed with a missing ESLint config — this is a pre-existing infrastructure issue not caused by changes in this plan. Verified via `tsc --noEmit` that no TypeScript errors exist in plan-related files. Three pre-existing TS errors in unrelated files (`IndividualEditorView.tsx`, `RepeatableCardsView.tsx`, `SidebarChat.tsx`) confirmed pre-existing by running build before and after changes — logged to deferred items.

## Issues Encountered
- `npm run lint` missing ESLint config file — pre-existing issue, not introduced by this plan. Verified TypeScript correctness via `tsc --noEmit` scoped to changed files (zero errors).
- Pre-existing `npm run build` failures in 3 unrelated files confirmed by running build on prior commit before changes.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 02 can now build the breakdown layout shell: `.breakdown-mode` CSS class ready to activate, `STORAGE_KEYS` for panel persistence available, `ModeToggle` navigation wired
- Route `/projects/:id/breakdown` navigation target is live from the dropdown
- No blockers

---
*Phase: 18-two-mode-ui-shell*
*Completed: 2026-03-19*
