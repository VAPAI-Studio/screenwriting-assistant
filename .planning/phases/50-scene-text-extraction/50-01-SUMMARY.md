---
phase: 50-scene-text-extraction
plan: 01
subsystem: api
tags: [breakdown, extraction, openai, prompt-engineering, fastapi, sqlalchemy]

# Dependency graph
requires:
  - phase: 49-single-scene-regenerate
    provides: ScreenplayContent.formatted_content.episode_index as the per-scene join key (v6.0), kept by keep_scene_version
  - phase: 11 (breakdown skeleton/pipeline)
    provides: ExtractionContext, _build_user_prompt, _map_scene_indices_to_ids, extract() pipeline
provides:
  - Scene-scoped extraction user prompt — each scene's full text under its own 1-based "### Scene {i+1}" header in the same index space as ExtractedSceneAppearance.scene_index
  - _align_screenplay_to_scenes helper (episode_index match + positional fallback, never raises)
  - Deterministic ScreenplayContent ordering in _build_extraction_context (closes the no-order_by determinism gap)
  - Strict full-coverage gate selecting aligned vs concatenated-fallback prompt form
affects: [phase-51-context-threading, phase-52-categories, phase-53-reextraction-hardening]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Robust index-alignment with graceful fallback (copied from wizards.py:keep_scene_version) applied to the breakdown prompt builder"
    - "Strict full-coverage gate in the prompt builder chooses aligned-vs-fallback without ever crashing extraction"

key-files:
  created: []
  modified:
    - backend/app/services/breakdown_service.py
    - backend/app/tests/test_breakdown_service.py

key-decisions:
  - "[Phase 50] Aligned per-scene prompt taken ONLY under a strict full-coverage gate (every scene mapped to exactly one non-empty text); any gap/ambiguity falls back to the unchanged concatenated ## Scenes + ## Screenplay Content form"
  - "[Phase 50] _align_screenplay_to_scenes copies the wizards.py episode_index-then-positional join (rows newest-first, positional index from the end); wrapped so it NEVER raises — extraction must always complete (T-50-01)"
  - "[Phase 50] ScreenplayContent query made deterministic (created_at.desc, id.desc), matching keep_scene_version, closing the prior no-order_by determinism gap"
  - "[Phase 50] Single chat_completion_structured call (temp 0.15, max_tokens 8000), EXTRACTION_SYSTEM_PROMPT on-screen-only rules, and the entire downstream pipeline (dedup/upsert/reconcile/staleness/audit) preserved verbatim (D-50-02/D-50-03)"

patterns-established:
  - "Per-scene indexed prompt structure: '### Scene {i+1}: {summary}' + that scene's full text, in the shared 1-based scene_index space consumed by _map_scene_indices_to_ids"
  - "Alignment helpers that feed AI prompts degrade gracefully (return partial/empty mapping) rather than raising, with a builder-side coverage gate"

requirements-completed: [BFID-01, BFID-02, BFID-03]

# Metrics
duration: ~8min
completed: 2026-06-07
---

# Phase 50 Plan 01: Scene-Scoped Fidelity Summary

**Restructured breakdown extraction so each scene's full text is presented under its own 1-based `### Scene {i+1}` header (same index space as scene_appearances), with an episode_index alignment helper that gracefully falls back to the concatenated prompt — single AI call and on-screen-only rules preserved verbatim.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-06-07
- **Completed:** 2026-06-07
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- BFID-02 delivered: the extraction user prompt now emits each scene's FULL text under its own explicit 1-based `### Scene {i+1}: {summary}` header (aligned path), removing the prior `## Scenes` summary vs separate `## Screenplay Content` blob alignment ambiguity that mis-attributed `scene_index` on longer scripts.
- Added `_align_screenplay_to_scenes` (episode_index match, positional fallback from the end of the newest-first list, skips empty content) copied from the `wizards.py:keep_scene_version` join; it NEVER raises (T-50-01 mitigation).
- Closed the determinism gap: the `ScreenplayContent` query in `_build_extraction_context` is now ordered `created_at.desc(), id.desc()`.
- BFID-03 guarded: `EXTRACTION_SYSTEM_PROMPT` on-screen-only rules unchanged and asserted in a test.
- Graceful fallback proven: count-mismatch (1 SC row, no episode_index, 3 scenes) completes extraction with the unchanged concatenated form (no crash).

## Task Commits

Each task committed atomically:

1. **Task 1: deterministic SC ordering + alignment helper + per-scene prompt restructure** — `c2922bb` (feat)
2. **Task 2: Phase 50 tests (aligned prompt, attribution mapping, BFID-03 guard, graceful fallback)** — `71796dc` (test)

_Note: Task 1 is `tdd="true"` but its `<verify>` is a source/AST assertion; the behavioral tests live in Task 2 per the plan's structure._

## Files Created/Modified
- `backend/app/services/breakdown_service.py` — Added `scene_texts_by_index` to `ExtractionContext`; deterministic `order_by` on the ScreenplayContent query; new `_align_screenplay_to_scenes` helper; restructured `_build_user_prompt` with a strict full-coverage gate (aligned `### Scene {i+1}` form vs concatenated fallback). Downstream pipeline untouched.
- `backend/app/tests/test_breakdown_service.py` — Added `_setup_project_with_aligned_screenplay` fixture (3 SC rows with `episode_index`) and four tests: aligned prompt shape (BFID-02), attribution mapping (BFID-02), on-screen-only rule guard (BFID-03), graceful fallback (D-50-01).

## Decisions Made
None beyond the plan — D-50-01/02/03 followed as specified (see key-decisions in frontmatter for the concrete choices the plan delegated to the executor, e.g. the strict full-coverage gate and the never-raise wrapper).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None. All planned tasks completed on the first pass; verification and the full regression gate passed.

## Verification Results

- `pytest app/tests/test_breakdown_service.py -x -q` → **12 passed** (8 pre-existing + 4 new).
- `pytest app/tests/test_breakdown_api.py app/tests/test_staleness.py -q` (regression gate) → green; combined full gate **60 passed, 0 failed**.
- The 4 new tests pass in isolation → **4 passed** (no reliance on suite ordering).
- Source assertions (Task 1 AST check): `_align_screenplay_to_scenes` present, `scene_texts_by_index` present, `ScreenplayContent.created_at` ordering present, `### Scene` header present → OK.
- No schema change, no migration, no new dependency.

## Known Stubs
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- BFID-01/02/03 complete; scene-scoped attribution is now reliable for v6.0+ generated scripts (rows carry `episode_index`); older rows degrade safely to the concatenated form.
- Phase 51 can now thread the per-appearance `context` string through scene links/UI (currently discarded) on top of the more reliable attribution.

## Self-Check: PASSED

- FOUND: backend/app/services/breakdown_service.py
- FOUND: backend/app/tests/test_breakdown_service.py
- FOUND: .planning/phases/50-scene-text-extraction/50-01-SUMMARY.md
- FOUND commit: c2922bb (Task 1)
- FOUND commit: 71796dc (Task 2)

---
*Phase: 50-scene-text-extraction*
*Completed: 2026-06-07*
