---
phase: 69-auto-episode-summary-lazy-regeneration
verified: 2026-06-17T00:00:00Z
status: passed
score: 9/9 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 69: Auto Episode Summary Lazy Regeneration — Verification Report

**Phase Goal:** Each episode gets an AI-generated summary automatically, and a stale summary is refreshed before it is ever used as context for a later episode — so connected generation never reads an out-of-date summary.
**Verified:** 2026-06-17
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | POST /api/projects/{id}/episode-summary generates and stores a non-empty episode_summary and clears episode_summary_stale | VERIFIED | `projects.py:144-184` — endpoint awaits `summarize_episode`, sets `project.episode_summary = summary`, `project.episode_summary_stale = False`, `db.commit()`; test `test_initial_endpoint_generates_stores_and_clears_flag` asserts 200 + stored text + flag False |
| 2 | The endpoint rejects a project not owned by the caller (404) | VERIFIED | `projects.py:164-169` — owner-scoped str-coerced filter (`owner_id == str(current_user.id)`); 404 on miss; test `test_initial_endpoint_cross_owner_returns_404` asserts 404 and 0 provider calls |
| 3 | summarize_episode produces bounded prose (json_mode=False, max_tokens~500), not the full script | VERIFIED | `template_ai_service.py:360-372` — `chat_completion(json_mode=False, max_tokens=500, temperature=0.3)`; test `test_initial_summarizer_calls_chat_completion_bounded_prose` asserts `json_mode is False` and `400 <= max_tokens <= 600` |
| 4 | Episode source text is reconstructed by episode_index, never positionally | VERIFIED | `template_ai_service.py:14-40` — `_read_episode_text_by_index` filters by `project_id`, builds dict keyed by `formatted_content.episode_index`, joins in `sorted()` order; test `test_by_index_reconstructs_in_episode_index_order` inserts rows out-of-order and asserts the correct ascending reconstruction |
| 5 | A stale-with-summary prior is regenerated before connected-mode generation reads it; its flag is cleared | VERIFIED | `episode_summary.py:63-84` — loop over stale priors, existence-gated, calls `summarize_episode`, sets `episode_summary = fresh` and `episode_summary_stale = False`; test `test_lazy_regen_fresh_text_no_marker_after_prepass` asserts fresh text in `build_bible_context` output with no stale marker, flag cleared |
| 6 | Up-to-date priors are NOT regenerated or disturbed (SC-3) | VERIFIED | `episode_summary.py:51-61` — query filters `episode_summary_stale.is_(True)`; `test_preserves_fresh_does_not_touch_up_to_date_prior` asserts 0 provider calls and byte-identical summary |
| 7 | Summary-less priors are NOT regenerated (existence-gate) | VERIFIED | `episode_summary.py:66-67` — `if not (prior.episode_summary or "").strip(): continue`; `test_existence_gate_skips_summary_less_and_regens_stale_with_summary` asserts whitespace-only prior triggers no provider call |
| 8 | On regen failure the flag stays True, Phase 68 stale marker is injected, and generation still proceeds | VERIFIED | `episode_summary.py:75-82` — per-prior `try/except` logs warning, no re-raise; test `test_regen_failure_injects_stale_with_marker_generation_proceeds` and `test_regen_failure_helper_leaves_flag_true_no_raise` assert flag stays True, stale text+marker appears in `build_bible_context`, no exception escapes |
| 9 | The pre-pass runs in run_wizard BEFORE build_bible_context, gated on connected mode | VERIFIED | `wizards.py:140-146` — `await regenerate_stale_priors(db, show, project)` at line 143, `build_bible_context(db, project)` at line 146; structural test `test_lazy_regen_call_precedes_build_bible_context_in_run_wizard` asserts ordering via `inspect.getsource`, presence of `ContinuityMode.CONNECTED.value` gate, and `build_bible_context` remains sync (`def`, not `async def`) |

**Score:** 9/9 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/tests/test_episode_summary.py` | ESUM-01/03 unit tests + `_patch_chat_completion` mock helper | VERIFIED | File exists, 21 tests, `_patch_chat_completion` context-manager patches `app.services.template_ai_service.chat_completion` with `AsyncMock`; all pass |
| `backend/app/services/template_ai_service.py` | `async summarize_episode(db, project)` + `_read_episode_text_by_index` | VERIFIED | Lines 14-40 (`_read_episode_text_by_index`) and 334-372 (`summarize_episode`) both exist and are substantive |
| `backend/app/api/endpoints/projects.py` | `POST /{project_id}/episode-summary` owner-scoped trigger | VERIFIED | Lines 144-184; contains `episode-summary` route, owner-scoped filter, 404 on miss, calls `summarize_episode`, writes+commits |
| `backend/app/utils/episode_summary.py` | `async regenerate_stale_priors(db, show, project)` lazy-regen pre-pass | VERIFIED | File created; function at lines 37-84; no stubs; committed and substantive |
| `backend/app/api/endpoints/wizards.py` | Connected-mode pre-pass call before `build_bible_context` in `run_wizard` | VERIFIED | Lines 140-146 — pre-pass at 143, `build_bible_context` at 146; import at line 16 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `projects.py` | `template_ai_service.summarize_episode` | `await` in `generate_episode_summary` endpoint | VERIFIED | Line 172: `summary = await template_ai_service.summarize_episode(db, project)` |
| `template_ai_service.py` | `ai_provider.chat_completion` | bounded prose call `json_mode=False` | VERIFIED | Line 360: `text = await chat_completion(... json_mode=False, max_tokens=500 ...)` |
| `wizards.py` | `episode_summary.regenerate_stale_priors` | `await` immediately before `build_bible_context(db, project)` | VERIFIED | Line 143: `await regenerate_stale_priors(db, show, project)`; line 146: `bible_context = build_bible_context(db, project)` |
| `episode_summary.py` | `template_ai_service.summarize_episode` | per-prior `await` inside `try/except` | VERIFIED | Line 69: `fresh = await template_ai_service.summarize_episode(db, prior)` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `episode_summary.py:regenerate_stale_priors` | `fresh` (regen result) | `template_ai_service.summarize_episode` → `_read_episode_text_by_index` → `ScreenplayContent` DB query → `chat_completion` | Yes — DB rows flow into the prompt; mock verifies call path | FLOWING |
| `projects.py:generate_episode_summary` | `summary` (stored) | Same path via `template_ai_service.summarize_episode` | Yes — stored to `project.episode_summary` after real call | FLOWING |

---

### Behavioral Spot-Checks (Test Suite)

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 21 phase-69 tests pass | `cd backend && PYTHONPATH=. ./venv/bin/python -m pytest app/tests/test_episode_summary.py -q` | `21 passed, 8 warnings in 0.20s` | PASS |
| by_index source read verified | `-k by_index` tests included in full run | Pass (3 tests in `TestReadEpisodeTextByIndex`) | PASS |
| initial generation endpoint verified | `-k initial` tests included in full run | Pass (4 tests in `TestEpisodeSummaryEndpoint` + `TestSummarizeEpisodeService`) | PASS |
| lazy_regen end-to-end verified | `-k lazy_regen` tests included in full run | Pass (1 test in `TestLazyRegenEndToEnd`) | PASS |
| regen_failure degrades gracefully | `-k regen_failure` tests included | Pass (2 tests — helper-level + end-to-end) | PASS |
| preserves_fresh SC-3 | `-k preserves_fresh` tests included | Pass (3 tests in `TestRegenerateStalePriorsHelper`) | PASS |
| existence_gate skips summary-less priors | `-k existence_gate` tests included | Pass (1 test asserting whitespace-only prior is skipped) | PASS |

---

### Probe Execution

No `probe-*.sh` files declared for this phase. Step 7c: SKIPPED (no probe scripts declared or conventionally present for a Python-only backend phase — the test suite is the verification mechanism).

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| ESUM-01 | 69-01-PLAN.md | When an episode is completed, the AI generates and stores a summary (`episode_summary`) | SATISFIED | `POST /api/projects/{id}/episode-summary` (projects.py:144) generates via `summarize_episode`, stores, clears stale flag, commits; 12 ESUM-01 tests pass |
| ESUM-03 | 69-02-PLAN.md | A stale episode summary is regenerated before it is used as context for later episodes (lazy regeneration) | SATISFIED | `regenerate_stale_priors` (episode_summary.py:37) wired into `run_wizard` at line 143 before `build_bible_context` at line 146; 9 ESUM-03 tests pass including end-to-end composition test and structural wiring assertion |

**Orphaned requirements check:** REQUIREMENTS.md traceability table maps ESUM-01 and ESUM-03 to Phase 69. No other v10.0 ESUM requirements (ESUM-02 is Phase 67 — complete) are mapped to Phase 69. No orphaned requirements.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | No debt markers (TBD/FIXME/XXX), no stub returns (return null/[]/{}), no empty handlers, no hardcoded empty data in phase-69 modified files | — | — |

One `placeholder` string at `template_ai_service.py:674` is a dictionary key lookup in field config data — not a stub comment. Not flagged.

---

### Human Verification Required

(none)

All observable truths are verifiable programmatically. The test suite covers the full behavioral surface: source-text reconstruction by episode_index, bounded prose generation parameters, owner-scoping, stale-flag semantics, existence-gate, failure degradation, connected-mode gate, ordering constraint (structural source inspection), and the full regen→read composition. No UI, no real-time, no external service integration in scope for this phase.

---

### Gaps Summary

No gaps. All 9 must-have truths verified, all 5 artifacts confirmed substantive and wired, all 4 key links confirmed, both requirement IDs (ESUM-01, ESUM-03) satisfied, test suite 21/21 green, no debt markers.

---

_Verified: 2026-06-17_
_Verifier: Claude (gsd-verifier)_
