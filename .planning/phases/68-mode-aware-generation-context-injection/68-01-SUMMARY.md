---
phase: 68-mode-aware-generation-context-injection
plan: 01
subsystem: api
tags: [continuity, prompt-context, sqlalchemy, ai-generation, episode-summary]

# Dependency graph
requires:
  - phase: 67-continuity-data-model-migration
    provides: "shows.continuity_mode VARCHAR column, ContinuityMode str-enum, Project.episode_summary / episode_summary_stale columns"
provides:
  - "Mode-branched build_bible_context: connected mode injects a '### Prior Episodes (for continuity)' block from prior-episode summaries"
  - "episode_number-ascending, most-recent-8 prior-episode ordering (PRIOR_EPISODE_CAP=8)"
  - "Stale-summary tagging with '(summary may be out of date)' marker"
  - "Empty/whitespace prior-summary graceful skipping; anthology/standalone/show_id-NULL unchanged"
affects: [69-auto-episode-summary, 71-mode-aware-review]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mode branch lives in the single provider-agnostic build_bible_context helper; zero generation-loop changes"
    - "Prior episodes ordered by integer episode_number.asc() (never positional) — recurring v6.0/v7.0 bug avoided"
    - "VARCHAR continuity_mode compared to ContinuityMode.CONNECTED.value (string), never the enum object"

key-files:
  created: []
  modified:
    - backend/app/utils/bible_context.py
    - backend/app/tests/test_bible_injection.py

key-decisions:
  - "Prior-episode query scoped strictly to the project's own show_id (T-68-01 info-disclosure mitigation)"
  - "PRIOR_EPISODE_CAP=8 count cap bounds prompt size on long connected seasons (T-68-03)"
  - "Stale summaries injected WITH a marker rather than skipped (D-STALE); only null/empty/whitespace skipped"
  - "Empty-bible-but-non-empty-priors still emits the Prior Episodes block (None only when both empty)"
  - "Prior-episode assembly extracted to a private _build_prior_episodes_block helper for readability"

patterns-established:
  - "Connected-mode prior-episode injection: filter(show_id, episode_number < current, episode_summary isnot None).order_by(episode_number.asc()), strip-gate, tail-slice cap"

requirements-completed: [SCONT-02, SCONT-03, SCONT-04]

# Metrics
duration: 4min
completed: 2026-06-17
---

# Phase 68 Plan 01: Mode-Aware Generation Context Injection Summary

**build_bible_context now branches on show.continuity_mode — connected episodes get an episode_number-ordered, 8-capped, stale-tagged "Prior Episodes" continuity block while anthology/standalone/film paths stay bible-only.**

## Performance

- **Duration:** ~4 min
- **Tasks:** 2 (TDD: RED tests, then GREEN implementation)
- **Files modified:** 2

## Accomplishments
- SCONT-02: connected-mode context injects prior-episode summaries ordered by `episode_number` ascending, capped to the most-recent 8, with stale summaries tagged `(summary may be out of date)` and empty/whitespace summaries skipped.
- SCONT-03/04: anthology and standalone shows fall through to bible-only; `show_id=NULL` films still return `None`.
- Restructured the empty-bible early-return so a connected show with an empty bible but non-empty priors still emits the Prior Episodes block.
- Added `TestContinuityModeInjection` (9 cases) including an ordering test that inserts rows out of `episode_number` order and would fail under positional ordering.

## Task Commits

1. **Task 1: Write failing TestContinuityModeInjection cases** - `4751a7b` (test)
2. **Task 2: Implement mode-branched prior-episode injection** - `91603a7` (feat)

_TDD: Task 1 committed the RED tests (5 connected cases failing, 4 today's-behavior cases passing); Task 2 turned them GREEN._

## Files Created/Modified
- `backend/app/utils/bible_context.py` - Added `ContinuityMode` import, `PRIOR_EPISODE_CAP=8`, `STALE_SUMMARY_MARKER`, a `_build_prior_episodes_block` helper, and the connected-mode branch in `build_bible_context` (priors computed before the empty-bible early-return).
- `backend/app/tests/test_bible_injection.py` - Added `TestContinuityModeInjection` with 9 cases (connected injection, episode_number ordering, anthology/standalone bible-only, show_id-NULL None, graceful degradation, stale-with-marker, most-recent-8 cap, VARCHAR-string-value guard).

## Decisions Made
- Extracted the prior-episode assembly into a private `_build_prior_episodes_block` helper (readability; the main function stays a flat parts-list builder). The plan described inline logic; extracting a helper is a stylistic refinement with identical behavior — not a behavioral deviation.
- Prior-episode entries rendered as `**Episode {n}: {title}**[marker]\n{summary}` so the stale marker sits on the per-episode header line, letting the test assert it is associated with the stale entry only.

## Deviations from Plan
None - plan executed exactly as written (the helper extraction noted above is a structural refinement within the single edit-site file, with no behavioral change).

## Issues Encountered
None. RED achieved on first run (5 connected cases failed for the expected reason: no Prior Episodes block); GREEN achieved on first implementation run (22/22 in the file).

## Verification
- `pytest app/tests/test_bible_injection.py -q` → 22 passed.
- `pytest app/tests/ -q` → 460 passed, 5 failed — exactly the documented pre-existing failures (test_mcp_foundation, test_session_isolation, test_yolo_integration), no phase-68 regressions.
- No diffs in `template_ai_service.py`, `openai_service.py`, or `ai_provider.py` (verified via `git status backend/app/services/`).

## Threat Surface
No new threat surface beyond the plan's `<threat_model>`. The prior-episode query is scoped to `Project.show_id == str(show.id)` (T-68-01), capped at 8 (T-68-03); no new free-text input path (T-68-02); no package installs (T-68-SC).

## Next Phase Readiness
- Phase 69 (auto episode summary + lazy regeneration) will write/regenerate the `episode_summary` text this phase reads; the stale marker is the seam where lazy regen will clear `episode_summary_stale` before this read.
- No blockers.

---
*Phase: 68-mode-aware-generation-context-injection*
*Completed: 2026-06-17*

## Self-Check: PASSED
- FOUND: backend/app/utils/bible_context.py
- FOUND: backend/app/tests/test_bible_injection.py
- FOUND: 68-01-SUMMARY.md
- FOUND commit: 4751a7b (test)
- FOUND commit: 91603a7 (feat)
