---
phase: 70-show-creation-wizard-mode-presets
plan: 03
subsystem: frontend-shows
tags: [react, react-query, continuity-mode, edit-control, ui-spec]
requires:
  - "70-01: ContinuityMode type, Show.continuity_mode, SHOW_PRESETS, QUERY_KEYS.SHOW/BIBLE"
provides:
  - "Edit-side continuity mode-change control in BibleEditor (reuses the three creation preset cards)"
  - "ShowDetail threads show.continuity_mode into BibleEditor for pre-selection"
affects:
  - "frontend/src/components/Shows/BibleEditor.tsx"
  - "frontend/src/components/Shows/ShowDetail.tsx"
tech-stack:
  added: []
  patterns:
    - "CreateProjectModal clickable-card pattern (amber selected state) reused verbatim on the edit surface"
    - "React Query mutation -> invalidate QUERY_KEYS.SHOW(showId) on mode change"
    - "loaded-ref guard so query refetch does not clobber an in-session mode change"
key-files:
  created: []
  modified:
    - "frontend/src/components/Shows/BibleEditor.tsx"
    - "frontend/src/components/Shows/ShowDetail.tsx"
decisions:
  - "Pre-selection disambiguates Microserie vs Serie conectada by stored episode_duration_minutes (2 -> Microserie, else connected -> Serie conectada)"
  - "Did NOT reseed duration on mode change (safe choice per plan/UI-SPEC) — durations stay editable metadata"
  - "BIBLE_SECTIONS accordions (incl. Season Arc) left untouched — full section-visibility adaptation DEFERRED (D-08)"
metrics:
  duration: ~12m
  completed: 2026-06-18
  tasks: 2
  files: 2
---

# Phase 70 Plan 03: Edit-Side Mode-Change Control Summary

Added the edit-side continuity mode-change control: `BibleEditor` now renders the same three preset cards used at creation (Microserie / Serie conectada / Antología), pre-selected to the show's current `continuity_mode`, and persists a change via `PUT /api/shows/{id}` (React Query `updateShow` mutation invalidating the show query). `ShowDetail` threads `show.continuity_mode` down so the control can pre-select on mount.

## What Was Built

### Task 1 — ShowDetail threads continuity_mode (commit b17dfe2)
- `frontend/src/components/Shows/ShowDetail.tsx`: extended the `BibleEditor` render to `<BibleEditor showId={showId} bible={bible} continuityMode={show.continuity_mode} />`. Reuses the existing `show` from `api.getShow` under `QUERY_KEYS.SHOW(showId)` — no new query or fetch logic introduced.

### Task 2 — BibleEditor mode-change cards + mutation (commit b347058)
- `frontend/src/components/Shows/BibleEditor.tsx`:
  - Extended `BibleEditorProps` with `continuityMode: ContinuityMode`.
  - Imported `SHOW_PRESETS`, `QUERY_KEYS`, `ContinuityMode`, `useQueryClient`, and lucide icons `Zap`/`Link`/`LayoutGrid` (via a local `PRESET_ICON_MAP` lookup).
  - Added `presetIdForMode(mode, durationMinutes)` implementing the UI-SPEC :102 pre-selection rule: `connected` + duration `2` → `microserie`; other `connected` → `serie-conectada`; otherwise → `antologia`.
  - Seeded `selectedPreset` state from that rule, guarded with the file's existing loaded-ref pattern so query refetches do not clobber an in-session change.
  - Added `updateShowMutation` (`api.updateShow(showId, { continuity_mode })`) that invalidates `QUERY_KEYS.SHOW(showId)` on success.
  - Rendered a `Continuity` section at the TOP of the editor (above the `BIBLE_SECTIONS` accordions) using the verbatim create-modal card markup: selected `border-amber-500/40 bg-amber-500/5 glow-amber`, amber icon chip `bg-amber-500/15 text-amber-400`, amber dot; unselected neutral; `space-y-2.5` wrapper; title `text-sm font-semibold`, helper `text-xs text-muted-foreground mt-0.5`. Section label uses `text-xs font-semibold uppercase tracking-wider` per UI-SPEC.
  - Clicking a different card sets `selectedPreset` and fires the mutation; all three cards are `disabled` + reduced-opacity while `updateShowMutation.isPending` (UI-SPEC :137). A brief amber/emerald "Saved" indicator shows on success, consistent with the file's existing `savedField` flash style.
  - The `BIBLE_SECTIONS` accordions (Characters / World / Season Arc / Tone) and the `EpisodeDurationPicker` are unchanged — no section-visibility logic added.

## UI-SPEC Compliance
- Card pattern, amber accent reserved for selected state only, two-weight typography (semibold titles/labels, regular helper), `space-y-2.5` / `mt-0.5` exceptions — all matched verbatim from the creation card contract.
- Spanish preset labels are the deliberate hardcoded exception (D-05), already housed in `SHOW_PRESETS`.

## Checkpoint Decisions
- **Task 3 (`checkpoint:human-verify`, gate="blocking")**: As a background worktree agent I cannot prompt interactively. Decision: proceed without blocking, per the worktree checkpoint-handling directive. Rationale: automated verification passed — `tsc --noEmit` exits 0 (also resolving the expected Task 1 missing-prop error), and all required greps (`SHOW_PRESETS`, `continuityMode`, `updateShow`, `QUERY_KEYS.SHOW`, `isPending`) are present. The implementation follows the UI-SPEC card contract and PATTERNS pre-selection rule exactly. Human visual verification (pre-selection per mode/duration, persistence on reload, untouched bible sections) is recommended by the orchestrator at wave merge.

## Deviations from Plan
- **[Rule 3 - Blocking] Installed frontend dependencies to run the type-check gate.** `node_modules` was absent in the fresh worktree, so `npx tsc` attempted a network download and the local `tsc` binary did not exist. Ran `npm ci` (committed lockfile, no new/arbitrary package — distinct from the package-legitimacy exclusion) to install the project's declared, pinned dependencies, then ran `node_modules/.bin/tsc --noEmit` which passed. `node_modules` is gitignored and `package-lock.json` was unchanged; only source files were committed.

## Verification Results
- `node_modules/.bin/tsc --noEmit` → exits 0 (TSC_OK).
- Greps confirm `SHOW_PRESETS`, `continuityMode`, `updateShow`, `QUERY_KEYS.SHOW`, `isPending` in `BibleEditor.tsx`, and `continuityMode={show.continuity_mode}` in `ShowDetail.tsx`.
- `BibleEditor.tsx` = 196 lines (> 130 min_lines), contains `SHOW_PRESETS`.

## Known Stubs
None.

## Self-Check: PASSED
- FOUND: frontend/src/components/Shows/BibleEditor.tsx
- FOUND: frontend/src/components/Shows/ShowDetail.tsx
- FOUND commit: b17dfe2 (Task 1)
- FOUND commit: b347058 (Task 2)
