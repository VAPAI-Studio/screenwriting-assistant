---
phase: 70
plan: 02
subsystem: frontend-show-creation
tags: [react, wizard, presets, continuity-mode, bible-seed]
requires:
  - "70-01: SHOW_PRESETS, ContinuityMode, ShowCreate.continuity_mode (constants.ts, types/index.ts)"
  - "Existing api.createShow / api.updateBible (api.tsx) — already forward continuity_mode + bible fields"
provides:
  - "CreateShowModal preset-card selection driving continuity_mode into the create payload"
  - "Conditional inline Season Arc reveal for connected presets"
  - "Two-call create sequence: createShow then chained updateBible (duration + season arc)"
affects:
  - "frontend/src/components/Shows/CreateShowModal.tsx"
tech-stack:
  added: []
  patterns:
    - "CreateProjectModal clickable-card pattern reused verbatim for preset cards"
    - "Two-call create sequence (create show, then chain bible update) per PATTERNS Integration Finding #2"
key-files:
  created: []
  modified:
    - "frontend/src/components/Shows/CreateShowModal.tsx"
decisions:
  - "Bible writes (episode_duration_minutes + bible_season_arc) merged into a single chained updateBible call per connected create, minimizing round-trips"
  - "selectedPresetObj/isConnected introduced in Task 2 (not Task 1) to keep Task 1 tsc-clean with no unused binding"
metrics:
  duration: ~15m
  completed: 2026-06-18
---

# Phase 70 Plan 02: Show Creation Wizard (preset cards + season arc) Summary

Extended `CreateShowModal` into the preset-driven show-creation wizard: a `Continuity` section with three preset cards (Microserie / Serie conectada / Antología) reusing the `CreateProjectModal` card pattern verbatim, a conditional inline `Season Arc` reveal for connected presets, and a two-call create sequence that persists `continuity_mode` on the show then chains `api.updateBible` to seed the preset duration (2/22) and the optional season arc.

## What Was Built

### Task 1 — Preset cards + continuity_mode + chained duration seed (commit `0bf77e1`)
- Imported `SHOW_PRESETS` and the three lucide icons (`Zap`, `Link`, `LayoutGrid`) via a `PRESET_ICON_MAP` lookup; extended the existing `lucide-react` import (which already brought in `X`).
- Added `selectedPreset` state (holds the preset `id`, single-select).
- Rendered a `Continuity` section (label `text-xs font-semibold ... uppercase tracking-wider mb-2`) directly after the Title field, before Description, inside the `space-y-5` form body.
- Three cards mapped from `SHOW_PRESETS`, copying the `CreateProjectModal` pattern verbatim: selected `border-amber-500/40 bg-amber-500/5 glow-amber`, amber icon chip `bg-amber-500/15 text-amber-400`, amber dot `w-2 h-2 rounded-full bg-amber-500`, card title `text-sm font-semibold` (NOT font-medium, per UI-SPEC :60), helper `text-xs text-muted-foreground mt-0.5`, list wrapped in `space-y-2.5`.
- Reworked the mutation into an async `mutationFn` implementing the two-call sequence: `api.createShow({ ..., continuity_mode })`, then `await api.updateBible(show.id, { episode_duration_minutes })` when the preset duration is non-null (skipped for Antología).
- Create CTA `disabled` guard extended to `!title || !selectedPreset || createShowMutation.isPending`.

### Task 2 — Conditional Season Arc reveal + chained season-arc save (commit `727d319`)
- Added `seasonArc` state and derived `selectedPresetObj` / `isConnected` (`selectedPresetObj?.mode === 'connected'`).
- Season Arc field gated on `{isConnected && (...)}`, wrapped in `animate-fade-up` (0.5s keyframe defined in `tailwind.config.js`), positioned above the Actions row. Uses the exact description-textarea classes, `rows={3}`, placeholder `Outline the overarching story arc for the season...` (matches BIBLE_SECTIONS season-arc placeholder). Optional — never blocks submit.
- Extended the chained `updateBible` call to merge `bible_season_arc: seasonArc.trim()` when connected AND non-empty, so a connected create issues a single bible update carrying both `episode_duration_minutes` and `bible_season_arc`. Antología never sends `bible_season_arc`.
- `seasonArc` reset to `''` on success alongside the other resets.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree had no `node_modules`, blocking `npx tsc --noEmit`**
- **Found during:** Task 1 verification.
- **Issue:** The git worktree was created without an `npm install`, so `npx tsc` errored ("not the tsc command you are looking for") and module resolution failed for all source files. This is not a package-legitimacy concern — no new packages were introduced.
- **Fix:** Confirmed the worktree's `frontend/package.json` and `frontend/package-lock.json` are byte-identical to the main repo's (committed lockfile), then symlinked the main repo's `frontend/node_modules` into the worktree and ran the repo-local `./node_modules/.bin/tsc`. No install performed, no dependency added. The symlink is untracked and was removed before returning so it is never committed.
- **Files modified:** none (tooling only).
- **Commit:** n/a.

**2. [Plan note] `selectedPresetObj` declaration moved from Task 1 to Task 2**
- The plan's Task 1 text suggested resolving `selectedPresetObj` once per render, but it is only consumed by Task 2's `isConnected` logic. Declaring it in Task 1 produced a TS6133 "declared but never read" error, failing Task 1's standalone `tsc` gate. Resolved by having Task 1's `mutationFn` find the preset inline (`const preset = SHOW_PRESETS.find(...)`) and introducing the render-level `selectedPresetObj` / `isConnected` in Task 2 where it is actually used. Behavior is identical to the plan intent.

## Checkpoint Decisions

**Task 3 (`checkpoint:human-verify`, gate=blocking):** As a background parallel worktree agent I cannot prompt interactively. Per the checkpoint-handling directive, I made the reasonable decision to proceed after completing all automatable verification:
- `npx tsc --noEmit` (via repo-local tsc) exits 0.
- All required tokens present in `CreateShowModal.tsx`: `SHOW_PRESETS`, `selectedPreset`, `continuity_mode:`, `updateBible`, `seasonArc`, `isConnected`, `bible_season_arc`, `animate-fade-up`.
- Card titles, classes, season-arc reveal gating, and the two-call sequence implemented exactly per the UI-SPEC and plan acceptance criteria.

The human visual/interaction verification (running `npm run dev`, clicking through the modal, confirming seeded duration 2/22 and season-arc text on the show page) is deferred to the orchestrator / user post-merge — it requires a running frontend + backend that this agent cannot drive. No blocking issues were found in the static contract.

## Acceptance Criteria

- [x] Three preset buttons titled exactly `Microserie`, `Serie conectada`, `Antología` (driven by `SHOW_PRESETS`).
- [x] Selecting a card applies `border-amber-500/40 bg-amber-500/5 glow-amber` + amber dot; single-select.
- [x] Create payload includes `continuity_mode` = selected preset's `mode`.
- [x] On success, `api.updateBible(show.id, { episode_duration_minutes })` called for Microserie (2) and Serie conectada (22), skipped for Antología.
- [x] Create CTA disabled until both title and preset present.
- [x] Season Arc textarea renders only for connected presets; absent for Antología and no-selection; carries `animate-fade-up`.
- [x] Empty Season Arc allowed (does not block submit).
- [x] Connected + non-empty Season Arc → chained `updateBible` payload includes `bible_season_arc`.
- [x] `npx tsc --noEmit` exits 0.

## Threat Surface

No new security surface beyond the plan's threat register. `continuity_mode` and the chained bible writes are client-sent but validated server-side (Phase 67 enum validation; Phase 37/41 owner-scoped bible endpoint). The two-call sequence's partial-failure mode (T-70-04) is acceptable: the show is created with `continuity_mode` persisted even if the bible seed fails, and duration/season-arc remain editable on the show page.

## Known Stubs

None. All UI state flows to real API payloads (continuity_mode → createShow; duration + season arc → chained updateBible). No hardcoded empty data, placeholders, or unwired components.

## Self-Check: PASSED

- FOUND: frontend/src/components/Shows/CreateShowModal.tsx
- FOUND: .planning/phases/70-show-creation-wizard-mode-presets/70-02-SUMMARY.md
- FOUND commit 0bf77e1 (Task 1), 727d319 (Task 2), fae46c7 (docs/SUMMARY)
