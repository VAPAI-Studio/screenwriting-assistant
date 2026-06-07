---
phase: 53-re-extraction-on-change
plan: 01
subsystem: breakdown
tags: [re-extraction, user-edits, scene-links, staleness, REEX-01, REEX-02]
requires:
  - "breakdown_service.extract() / _reconcile_scene_links / _upsert_elements (existing)"
  - "_mark_breakdown_stale (phase_data.py)"
  - "BreakdownElement.user_modified column (existing)"
provides:
  - "Extract-loop guard: user_modified elements' scene links untouched on re-extract (D-53-01)"
  - "REEX-02 link-preservation + scoping tests; REEX-01 full-chain integration test (D-53-02)"
affects:
  - "breakdown re-extraction behavior for user-owned elements only"
tech-stack:
  added: []
  patterns:
    - "Loop guard scoped to db_element.user_modified (consistent with SYNC-01 philosophy)"
key-files:
  created: []
  modified:
    - backend/app/services/breakdown_service.py
    - backend/app/tests/test_breakdown_service.py
decisions:
  - "D-53-01: skip _reconcile_scene_links when db_element.user_modified is True (loop guard, not method guard) — avoids an extra query; element_map membership preserved"
  - "D-53-02: prove the full stale -> re-extract -> preserve -> stale-cleared chain with an integration test"
  - "D-53-03: additive guard only — no schema change, no migration, no FE change; all existing behavior preserved"
metrics:
  duration: ~3min
  completed: 2026-06-07
---

# Phase 53 Plan 01: Re-Extraction Hardening Summary

A single surgical guard in `breakdown_service.extract()` now skips `_reconcile_scene_links` for any `user_modified` element, so a user-owned breakdown element's curated scene links are never wiped/recreated on re-extraction (REEX-02, D-53-01) — while non-user_modified (AI) elements still reconcile to the current script. Three new tests prove link preservation, guard scoping, and the full REEX-01 stale→re-extract→preserve→stale-cleared chain.

## What Was Built

- **Task 1 — Extract-loop guard (D-53-01):** In the reconcile loop (breakdown_service.py ~568-582), after fetching `db_element` and the existing `if db_element is None: continue`, added `if db_element.user_modified: continue` with a comment citing REEX-02/D-53-01. Skips ONLY the `_reconcile_scene_links` call; user_modified elements remain in `element_map`. Everything else (single AI call, EXTRACTION_SYSTEM_PROMPT, dedup, Phase 50 scene-scoped prompt, Phase 51 per-appearance context, Phase 52 categories, SYNC-01/02 skips, the stale-clear) is unchanged.
- **Task 2 — Tests (D-53-02):** Added `from app.api.endpoints.phase_data import _mark_breakdown_stale` and three tests to `test_breakdown_service.py`:
  - `test_user_modified_links_not_churned_on_reextract` (Test A, REEX-02): user_modified element with an existing source="ai" link to scene 0; AI re-attributes it to scenes 2/3 with a new description; asserts the link set is UNCHANGED (still exactly scene 0) and the description is preserved (SYNC-01).
  - `test_non_user_modified_links_still_reconcile` (Test B, scoping): AI element (user_modified=False) with an existing AI link to scene 0; AI attributes it to scene 3; asserts the link reconciles to scene 3 and scene 0 is gone — proving the guard is scoped to user_modified only.
  - `test_reextraction_chain_preserves_user_and_clears_stale` (Test C, REEX-01): seeds a user_modified element with a curated link; `_mark_breakdown_stale` → asserts `breakdown_stale is True`; `extract()` with AI returning the user element (would-overwrite) + a fresh Knight element; asserts user description+link preserved, Knight created with its reconciled link, and `breakdown_stale is False`.
- **Task 3 — Regression gate (D-53-03):** Ran the three modules together; all green, confirming no existing behavior regressed.

## Verification Results

- `pytest app/tests/test_breakdown_service.py -q` → **20 passed** (17 existing + 3 new).
- `pytest app/tests/test_breakdown_service.py app/tests/test_breakdown_api.py app/tests/test_staleness.py -q` → **71 passed**, 0 failed.
- Source assertion (D-53-01): the extract loop in `breakdown_service.py` skips `_reconcile_scene_links` for `user_modified` elements (guard at ~572-580); user_modified elements remain in `element_map`; file parses (`ast.parse` → parse-ok).
- `test_user_modified_preserved` (SYNC-01) and `test_deleted_not_resurrected` (SYNC-02) remain green.

## Deviations from Plan

None — plan executed exactly as written. Task 3 modifies no files (gate-only re-run of Task 2's file plus two unmodified suites), so it has no separate commit.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: backend/app/services/breakdown_service.py (guard present)
- FOUND: backend/app/tests/test_breakdown_service.py (3 new tests present)
- FOUND commit: b124dfe (feat: guard)
- FOUND commit: 85ef61e (test: REEX tests)
