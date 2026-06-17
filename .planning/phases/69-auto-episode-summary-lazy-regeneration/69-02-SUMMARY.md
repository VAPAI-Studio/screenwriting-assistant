---
phase: 69-auto-episode-summary-lazy-regeneration
plan: 02
subsystem: backend
tags: [esum-03, episode-summary, lazy-regeneration, continuity, connected-mode, tdd]
requires:
  - "Plan 69-01: template_ai_service.summarize_episode(db, project) -> str (bounded prose, caller-commits)"
  - "Phase 68: build_bible_context connected-mode Prior Episodes block + STALE_SUMMARY_MARKER"
  - "Phase 67: Project.episode_summary / episode_summary_stale columns"
provides:
  - "async regenerate_stale_priors(db, show, project) lazy-regen pre-pass (backend/app/utils/episode_summary.py)"
  - "run_wizard connected-mode pre-pass call BEFORE build_bible_context (ESUM-03 wired end-to-end)"
  - "ESUM-03 tests: lazy_regen, preserves_fresh, regen_failure, existence_gate (reuse Plan 69-01 scaffold)"
affects:
  - backend/app/api/endpoints/wizards.py
  - backend/app/utils/episode_summary.py
tech-stack:
  added: []
  patterns:
    - "Lazy regen as an async pre-pass in the connected-mode generation path, BEFORE the sync build_bible_context read (Pitfall 2 — frozen-context)"
    - "Pre-pass query mirrors _build_prior_episodes_block: show_id, episode_number < current, episode_summary isnot None, stale.is_(True), episode_number.asc()"
    - "Existence-gate ((episode_summary or '').strip()) + per-prior try/except: failure leaves flag True -> Phase 68 marker fallback (generation never fails)"
    - "Connected gate via show.continuity_mode == ContinuityMode.CONNECTED.value (VARCHAR string compare, never the enum object)"
key-files:
  created:
    - backend/app/utils/episode_summary.py
  modified:
    - backend/app/api/endpoints/wizards.py
    - backend/app/tests/test_episode_summary.py
decisions:
  - "ESUM-03 end-to-end tests exercise the regenerate_stale_priors -> build_bible_context COMPOSITION directly (the exact run_wizard ordering) rather than driving the full run_wizard endpoint; standing up the async BackgroundTasks generation + WizardRun lifecycle is heavy and orthogonal to the behavior under test. The wiring itself (call site precedes build_bible_context, connected gate, build_bible_context stays sync) is asserted structurally via inspect.getsource."
  - "On summarize_episode returning '' (empty source text) during regen, the helper leaves the existing summary + flag untouched rather than clobbering with empty (mirrors Plan 69-01 endpoint no-clobber choice)."
metrics:
  duration: ~6min
  completed: 2026-06-17
requirements: [ESUM-03]
---

# Phase 69 Plan 02: Auto Episode Summary Lazy Regeneration Summary

ESUM-03 regenerate-before-read: a new `async regenerate_stale_priors(db, show, project)` pre-pass refreshes only stale-with-summary strictly-prior episodes of a connected show, wired into `run_wizard` immediately BEFORE the synchronous `build_bible_context(db, project)` so the frozen context string sees fresh rows; on per-prior AI failure the stale flag stays True and Phase 68's `(summary may be out of date)` marker path degrades gracefully — generation never fails.

## What Was Built

- **`regenerate_stale_priors(db, show, project) -> None`** (new `backend/app/utils/episode_summary.py`): no-op when `project.episode_number is None`; queries strictly-prior episodes of THIS show (`show_id == str(show.id)`, `episode_number < current`, `episode_summary.isnot(None)`, `episode_summary_stale.is_(True)`, ordered `episode_number.asc()`) — mirroring `_build_prior_episodes_block` (T-69-04 scope). Per-prior: existence-gate (`(episode_summary or "").strip()`) skips summary-less rows; inside a try/except `fresh = await template_ai_service.summarize_episode(db, prior)`, and on truthy result sets `episode_summary = fresh` + `episode_summary_stale = False`. On `Exception`: `logger.warning(...)`, leaves the flag True (no re-raise). Single `db.commit()` after the loop. `summarize_episode` stays caller-commit (no write inside the summarizer).
- **`run_wizard` pre-pass wiring** (`backend/app/api/endpoints/wizards.py`): immediately before line ~146's `bible_context = build_bible_context(db, project)`, loads the show when `project.show_id` is set and, gated on `show.continuity_mode == ContinuityMode.CONNECTED.value`, `await regenerate_stale_priors(db, show, project)`. Added imports for `regenerate_stale_priors` and `ContinuityMode`. `build_bible_context` is untouched (remains a pure sync reader).
- **ESUM-03 tests** (`backend/app/tests/test_episode_summary.py`, reusing the Plan 69-01 scaffold): helper-level `existence_gate` / `preserves_fresh` (×3) / `regen_failure`; end-to-end `lazy_regen` (fresh text, no marker, flag cleared after pre-pass + `build_bible_context`) and `regen_failure` (stale-with-marker injected, flag stays True, no raise); structural wiring assertion (regen call precedes `build_bible_context`, connected gate present, `build_bible_context` stays sync) and an anthology-skips-pre-pass gate test.

## Task Commits

| Task | Name | Commit(s) | Files |
| ---- | ---- | --------- | ----- |
| 1 | regenerate_stale_priors helper (TDD) | `7fccb9e` (test/RED), `7d6a2a0` (feat/GREEN) | episode_summary.py, test_episode_summary.py |
| 2 | Wire pre-pass into run_wizard + end-to-end tests (TDD) | `aad3b6b` (test/RED), `13fa6ff` (feat/GREEN) | wizards.py, test_episode_summary.py |

## Verification

- `pytest app/tests/test_episode_summary.py -k "preserves_fresh or existence_gate or regen_failure"` (Task 1) → 5 passed.
- `pytest app/tests/test_episode_summary.py -k "lazy_regen or regen_failure"` (Task 2) → 4 passed.
- `pytest app/tests/test_episode_summary.py -q` → **21 passed** (12 from Plan 69-01 + 9 new).
- Full suite: `pytest app/tests/ -q` → **481 passed, 5 failed** — the 5 are the documented pre-existing failures (test_mcp_foundation / test_session_isolation / test_yolo_integration), out of scope, NOT phase-69 regressions.
- Grep gate: `regenerate_stale_priors` call at wizards.py:143 sits ABOVE `build_bible_context(db, project)` at :146; `build_bible_context` remains `def` (not `async def`).

## TDD Gate Compliance

Both tasks followed RED → GREEN: a `test(...)` commit precedes the `feat(...)` commit in each (`7fccb9e`→`7d6a2a0`, `aad3b6b`→`13fa6ff`). Task 2's RED was the structural wiring assertion (the 3 behavior tests passed pre-wiring because they drive the Task-1 helper directly — the new surface Task 2 adds is the run_wizard wiring, which was correctly red until GREEN). No unexpected fully-passing RED. No REFACTOR commits needed.

## Deviations from Plan

### Documented Choice (per plan Task 2 note)

- **End-to-end tests target the pre-pass → build_bible_context composition, not the full run_wizard endpoint.** The plan explicitly allowed "test the pre-pass+build_bible_context composition directly if full run_wizard plumbing is heavy — document which." Driving `run_wizard` end-to-end requires standing up the async `BackgroundTasks` generation path + `WizardRun` lifecycle + provider mocks for the wizard generation itself, which is orthogonal to the ESUM-03 regenerate-before-read behavior. The exact run_wizard ordering (regen BEFORE the sync read) is asserted structurally (`inspect.getsource`), and the behavior (fresh-no-marker / stale-with-marker / connected gate) is asserted on the composition. No auto-fixed bugs (Rules 1-3) were needed.

## Threat Surface

- T-69-04 (info disclosure / tampering) mitigated: the pre-pass query is scoped to `Project.show_id == str(show.id)` and `episode_number < current` (same show; `project` is owner-resolved in `run_wizard` before the pre-pass) — mirrors Phase 68 T-68-01.
- T-69-05 (DoS / generation aborts on AI error) mitigated: per-prior try/except leaves the flag True and falls through to Phase 68's marker path; `regen_failure` tests assert generation proceeds (no raise) and the flag stays True.
- T-69-06 (token blow-up) accepted: bounded summary (Plan 69-01) + Phase 68 `PRIOR_EPISODE_CAP=8` bound the prompt; concurrent double-regen accepted best-effort for the internal-tool MVP.
- No new threat surface beyond the plan's `<threat_model>`.

## Known Stubs

None. ESUM-03 is fully wired into the connected-mode generation read site (`run_wizard`). Review / ai_chat / MCP read sites are intentionally NOT wired (Phase 71+ scope, per D-REGEN-SCOPE).

## Self-Check: PASSED
