---
phase: 70-show-creation-wizard-mode-presets
plan: 01
subsystem: frontend-types-config
tags: [frontend, types, continuity-mode, show-presets, foundation]
requires:
  - "backend/app/models/schemas.py ContinuityMode enum (Phase 67)"
provides:
  - "ContinuityMode string-literal union (frontend/src/types/index.ts)"
  - "continuity_mode field on Show (required) and ShowCreate (optional)"
  - "SHOW_PRESETS shared config (frontend/src/lib/constants.ts)"
affects:
  - "Plan 02 (create modal consumes SHOW_PRESETS + ShowCreate.continuity_mode)"
  - "Plan 03 (edit-side mode control consumes SHOW_PRESETS + ContinuityMode)"
tech-stack:
  added: []
  patterns:
    - "Frontend string-literal union mirrors backend str-enum values (typing aid, not the security boundary)"
    - "Single shared `as const` preset config typed against the domain union (DURATION_PRESETS shape)"
key-files:
  created: []
  modified:
    - "frontend/src/types/index.ts"
    - "frontend/src/lib/constants.ts"
decisions:
  - "D-02: ContinuityMode union includes `standalone` for type-completeness even though the wizard offers only two presets"
  - "D-01/D-04/D-05: three presets Microserie=connected/2, Serie conectada=connected/22, Antología=anthology/null; Spanish labels verbatim, no i18n"
  - "D-03: preset `duration` seeds an editable default and is not coupled to the mode beyond seeding; Microserie's 2 is a custom seed, intentionally NOT added to DURATION_PRESETS"
  - "Integration Finding #3: no separate ShowUpdate interface — api.updateShow is typed Partial<ShowCreate>, so adding the field to ShowCreate covers edit"
metrics:
  duration: ~6min
  completed: 2026-06-18
---

# Phase 70 Plan 01: Continuity Mode Types & Show Presets Summary

Established the typed frontend foundation for Phase 70: a `ContinuityMode` string-literal union mirroring the backend enum, `continuity_mode` threaded through `Show`/`ShowCreate`, and a single shared `SHOW_PRESETS` config that both downstream plans (create modal, edit-side control) consume.

## What Was Built

### Task 1 — ContinuityMode union + Show/ShowCreate threading
- Added `export type ContinuityMode = 'connected' | 'anthology' | 'standalone';` immediately above the `Show` interface in `frontend/src/types/index.ts`, mirroring the backend `ContinuityMode` str-enum (schemas.py, Phase 67). All three values included for type-completeness (D-02 — `standalone` is the `show_id IS NULL` feature-film path, not a wizard preset).
- Added required `continuity_mode: ContinuityMode;` to `Show` (always returned by the backend `ShowResponse`, backend default `'anthology'`).
- Added optional `continuity_mode?: ContinuityMode;` to `ShowCreate` (backend defaults to `'anthology'` when omitted — Phase 67 D-01). No separate `ShowUpdate` interface was introduced: `api.updateShow` is typed `Partial<ShowCreate>`, so the field automatically covers the edit payload (Integration Finding #3). `episode_duration_minutes` was NOT added to `ShowCreate` — it remains a Bible field on `BibleUpdate`/`BibleResponse` (Integration Finding #2); those interfaces are unchanged.
- Commit: `34fe4f9`

### Task 2 — Shared SHOW_PRESETS config
- Added the `ContinuityMode` type import to `frontend/src/lib/constants.ts`.
- Added exported `SHOW_PRESETS` near `DURATION_PRESETS`, typed as `ReadonlyArray<{ id; label; helper; icon; mode: ContinuityMode; duration: number | null }>` with `as const`. Three entries in the exact order Microserie / Serie conectada / Antología, with verbatim Spanish labels and English helpers per the UI-SPEC copywriting contract. The em-dash in the Serie conectada and Antología helpers is the literal `—` character.
- `icon` values are lucide-react component names as strings (`Zap`, `Link`, `LayoutGrid`); consumers map them to the imported component.
- `DURATION_PRESETS` left untouched (still 10/22/44/60/-1) — Microserie's `duration: 2` is a custom seed and was deliberately NOT added to the shared duration presets.
- Commit: `94d6462`

## Verification

- `npx tsc --noEmit` exits 0 for the whole frontend (run after each task).
- `grep` confirms the exact `ContinuityMode` union line, the required/optional `continuity_mode` fields, `SHOW_PRESETS` with all three Spanish labels, and both `mode: 'connected'` / `mode: 'anthology'`.
- `awk` over the `DURATION_PRESETS` block confirms no `value: 2` entry was added; the block remains 10/22/44/60/-1.
- Em-dash literal present (2 occurrences) matching the copywriting contract.

Note: `frontend/node_modules` was not present in this worktree, so `npm ci` was run (deterministic install from the existing `package-lock.json`; no new packages — `typescript` is an already-declared devDependency) to make `tsc` available. No package.json or lockfile changes; nothing committed beyond the two source files.

## Deviations from Plan

None — plan executed exactly as written. (The `npm ci` to obtain the existing locked toolchain in a fresh worktree is environment setup, not a deviation: no new dependency was introduced and no manifest/lockfile changed.)

## Known Stubs

None. This plan adds only type definitions and a static config consumed by later plans; no UI data sources are wired in this plan (by design — "No component changes in this plan").

## Self-Check: PASSED

- FOUND: frontend/src/types/index.ts (ContinuityMode union + continuity_mode on Show/ShowCreate)
- FOUND: frontend/src/lib/constants.ts (SHOW_PRESETS)
- FOUND commit: 34fe4f9 (feat 70-01: ContinuityMode union + Show/ShowCreate)
- FOUND commit: 94d6462 (feat 70-01: SHOW_PRESETS config)
