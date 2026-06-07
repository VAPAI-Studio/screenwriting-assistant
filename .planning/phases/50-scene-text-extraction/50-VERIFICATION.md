---
phase: 50-scene-text-extraction
verified: 2026-06-07T00:00:00Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
re_verification: # No previous VERIFICATION.md existed — initial verification
---

# Phase 50: Scene-Scoped Fidelity Verification Report

**Phase Goal:** Make breakdown extraction reliably scene-scoped — give the AI explicit per-scene structure to attribute each element to the correct scene(s), with on-screen-only rules preserved (BFID-01 verified, BFID-02 built, BFID-03 preserved).
**Verified:** 2026-06-07
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | BFID-01 (verified): full screenplay text of every scene reaches the AI prompt | ✓ VERIFIED | `breakdown_service.py:188` `screenplay_texts=[sc.content for sc in screenplays if sc.content]`; aligned path emits full scene text `by_index[i]` at `:278`; fallback emits full `text` at `:295`. Asserted by test `test_aligned_prompt_emits_per_scene_indexed_text` (full scene texts present, lines 504-506) and `test_graceful_fallback_on_count_mismatch` (`## Screenplay Content` present, line 588). Both paths carry full text, not summaries. |
| 2 | BFID-02 (built): aligned path presents each scene's full text under explicit 1-based `### Scene {i+1}` header in same index space as `_map_scene_indices_to_ids` | ✓ VERIFIED | `_build_user_prompt` `:276-279` emits `### Scene {i+1}: {summary}` + `by_index[i]` for each scene under strict full-coverage gate `:265-267`. `_map_scene_indices_to_ids` `:469` `zero_based = scene_index - 1` confirms shared 1-based space. Single AI call preserved (`_call_ai_extraction:311`). Test `test_aligned_attribution_maps_to_scene_ids` proves scene_index 1/3 → scene_ids[0]/[2]. |
| 3 | BFID-03 (preserved): on-screen-only RULES remain verbatim in EXTRACTION_SYSTEM_PROMPT | ✓ VERIFIED | `breakdown_service.py:86` "PHYSICALLY PRESENT ON SCREEN"; `:90` "Do NOT extract elements merely mentioned in dialogue or backstory". Asserted by `test_on_screen_only_rules_preserved` (lines 557-559). |
| 4 | ScreenplayContent query in `_build_extraction_context` deterministically ordered | ✓ VERIFIED | `:131-136` `.order_by(ScreenplayContent.created_at.desc(), ScreenplayContent.id.desc())` — matches wizards.py:keep_scene_version. Was previously unordered. |
| 5 | Alignment NEVER crashes extraction; count-mismatch falls back gracefully and extract() still completes | ✓ VERIFIED | `_align_screenplay_to_scenes:215-242` wrapped in try/except returning `{}` on any exception (`:239-241`); builder strict gate `:265-267` drops aligned path on any gap. Behavioral proof: `test_graceful_fallback_on_count_mismatch` runs extract() on 1-row/3-scene fixture → `run.status == "completed"` (line 583), no crash; prompt uses fallback (no `### Scene`, line 589). |
| 6 | Existing pipeline preserved: dedup, upsert (user_modified/is_deleted), reconcile, staleness clear, audit, models byte-for-byte | ✓ VERIFIED | `_deduplicate_elements:318`, `_upsert_elements:347` (SYNC-01/02 honored `:380-390`), `_reconcile_scene_links:419` (preserves source="user" `:440-446`), staleness clear `:565-571`, `_record_run:480` audit, `ExtractedElement`/`ExtractionResponse` models `:42-60` unchanged. Regression suites green (48 passed). |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `backend/app/services/breakdown_service.py` | Deterministic SC ordering + `_align_screenplay_to_scenes` + per-scene indexed prompt w/ graceful fallback | ✓ VERIFIED | `_align_screenplay_to_scenes` present (`:195`), `scene_texts_by_index` field (`:77`), deterministic order_by (`:131-136`), `### Scene` header (`:277`). All wired into `_build_extraction_context` → `_build_user_prompt`. |
| `backend/app/tests/test_breakdown_service.py` | 4 Phase-50 tests + aligned fixture | ✓ VERIFIED | `_setup_project_with_aligned_screenplay` (`:121`, 3 SC rows w/ episode_index); tests at `:490, :516, :552, :565`. All assert real behavior (not trivial). 12 passed in isolation. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `_build_extraction_context` | `_build_user_prompt` | `ExtractionContext.scene_texts_by_index` | ✓ WIRED | Set at `:183-185, :192`; consumed at `:264`. |
| `ScreenplayContent.formatted_content.episode_index` | scene_summaries order | `_align_screenplay_to_scenes` (episode_index match + positional fallback, never raise) | ✓ WIRED | `:218-232`; positional fallback from end of newest-first list `:232`; try/except never raises `:239`. |
| `_build_user_prompt` `### Scene {i+1}` headers | `_map_scene_indices_to_ids` | shared 1-based scene_index space | ✓ WIRED | Prompt header `i+1` (`:277`) matches `scene_index - 1` mapping (`:469`). Proven end-to-end by attribution test. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `_build_user_prompt` aligned path | `by_index[i]` | `ScreenplayContent.content` via `_align_screenplay_to_scenes` | Yes — real DB query (`:131`), real episode_index join | ✓ FLOWING |
| `_build_user_prompt` fallback path | `ctx.screenplay_texts` | `[sc.content for sc in screenplays]` (`:188`) | Yes — real DB content | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Service tests (incl. aligned prompt, attribution, fallback no-crash) | `pytest app/tests/test_breakdown_service.py -x -q` | 12 passed | ✓ PASS |
| Regression: API + staleness | `pytest app/tests/test_breakdown_api.py app/tests/test_staleness.py -q` | 48 passed | ✓ PASS |
| New tests in isolation | `pytest app/tests/test_breakdown_service.py -q` | 12 passed | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| BFID-01 | 50-01 | Extract against full scene text, not summaries (verify) | ✓ SATISFIED | Full text reaches prompt in both paths (Truth 1). Verified, not rebuilt per RESCOPE-NOTE. |
| BFID-02 | 50-01 | Scene-scoped attribution: per-scene indexed prompt structure (build) | ✓ SATISFIED | Aligned `### Scene {i+1}` structure in shared index space (Truth 2). |
| BFID-03 | 50-01 | On-screen-only rules preserved | ✓ SATISFIED | EXTRACTION_SYSTEM_PROMPT rules verbatim (Truth 3). |

### Decision Verification

| Decision | Requirement | Status | Evidence |
| --- | --- | --- | --- |
| D-50-01 | Graceful fallback never crashes; strict full-coverage gate | ✓ VERIFIED | try/except `:239`, strict gate `:265-267`, behavioral test (Truth 5). |
| D-50-02 | Single `chat_completion_structured` call, NOT per-scene | ✓ VERIFIED | One call in `_call_ai_extraction:311` (temp 0.15, max_tokens 8000); no per-scene loop. |
| D-50-03 | dedup/upsert/reconcile/staleness/audit + models preserved | ✓ VERIFIED | Truth 6; diff touches only prompt builder + new helper. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `breakdown_service.py` | 452 | `_reconcile_scene_links` writes `context=""` | ℹ️ Info | Expected — threading `scene_appearances[].context` is explicitly Phase 51 work (RESCOPE-NOTE line 32). NOT a Phase 50 gap. |

No debt markers (TODO/FIXME/XXX/TBD/HACK) found in modified service file.

### Migration / Dependency Check

- No migration / alembic files touched (diff `c2922bb~1..71796dc` name-only scan: none).
- No requirements/pyproject/package files touched.
- No schema change: `ExtractedElement`/`ExtractionResponse`/`ExtractedSceneAppearance` models unchanged; only an in-memory dataclass field (`scene_texts_by_index`) added.
- Commits `c2922bb` (feat) and `71796dc` (test) exist; combined diff = 2 files, +284/-3.

### Human Verification Required

None. All truths are verifiable programmatically via source inspection + automated tests, and all checks passed. The change is backend prompt-structure only with full behavioral test coverage including the no-crash fallback safety net.

### Gaps Summary

No gaps. All 6 must-haves verified against actual source (not SUMMARY claims). BFID-01 mechanism confirmed (full text in both prompt paths), BFID-02 per-scene indexed structure built in the correct shared 1-based index space and proven end-to-end by an attribution test, BFID-03 rules preserved verbatim. The determinism gap is closed; the alignment helper never raises and the strict full-coverage gate provably degrades to the concatenated form on the single-row/3-scene mismatch fixture with `run.status == "completed"`. D-50-01/02/03 all honored. No schema change, no migration, no new dependency. Both verification suites pass (12 + 48 = 60 total). The `context=""` write is intentional Phase 51 scope, not a regression.

---

_Verified: 2026-06-07_
_Verifier: Claude (gsd-verifier)_
