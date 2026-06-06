---
phase: 45-continuity-aware-generation
plan: 01
subsystem: api
tags: [openai, anthropic, screenplay-generation, prompt-engineering, continuity, jsonb]

# Dependency graph
requires:
  - phase: prior-script-generation
    provides: _generate_scripts sequential scene loop + chat_completion provider abstraction + screenplay_editor PhaseData persistence
provides:
  - Continuity-aware scene generation (running prose synopsis + verbatim prior-scene text threaded into each later scene prompt)
  - _update_synopsis helper that re-summarizes the whole story-so-far under a word cap via chat_completion
  - Final synopsis persisted into the existing screenplay_editor PhaseData.content JSON (no migration)
affects: [46-format-evaluation, 47-character-voice, 48-craft-guidance, 49-eval-compare]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Continuity threading: running synopsis + prev_scene_text carried through a sequential generation loop, advanced only in the success branch"
    - "Conditional prompt-section injection for continuity (first/single scene gets no block)"
    - "Per-scene re-summarization (regenerate whole synopsis under a word cap, never truncate) via a low-temp json_mode=False chat_completion call"
    - "Graceful AI-call degradation: synopsis-update failure returns prior synopsis, never aborts the run"

key-files:
  created:
    - backend/app/tests/test_continuity_generation.py
  modified:
    - backend/app/services/template_ai_service.py
    - backend/app/api/endpoints/wizards.py

key-decisions:
  - "Synopsis-update call uses json_mode=False, temperature 0.3, max_tokens 700, ~400-word cap (within D-03's 300-500 range) — Claude's Discretion values"
  - "Continuity block is a single conditional f-string injected only when synopsis or prev_scene_text is non-empty (D-05)"
  - "Continuity state advances strictly inside the success branch so a failed scene's [Generation failed] placeholder never reaches the next prompt or the synopsis (D-05)"
  - "Test mock routes scene-writing (json_mode=True) vs synopsis-update (json_mode=False) calls via the json_mode kwarg; side_effect is synchronous so AsyncMock awaits it once (no coroutine double-wrap)"

patterns-established:
  - "Continuity-threading loop: initialize running state empty per run (D-07), inject conditionally, update only on success"
  - "Synopsis persistence rides the existing flag_modified JSONB write — no new column, no migration"

requirements-completed: [CONT-01, CONT-02, CONT-03]

# Metrics
duration: 13 min
completed: 2026-06-06
---

# Phase 45 Plan 01: Continuity-Aware Generation Summary

**Scene-by-scene screenplay generation now threads a running prose synopsis plus the immediately-preceding scene's full verbatim text into each later scene prompt, regenerating the synopsis after each successful scene via a bounded chat_completion call and persisting it into the existing screenplay_editor JSON.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-06-06T03:16:00Z
- **Completed:** 2026-06-06T03:29:09Z
- **Tasks:** 3
- **Files modified:** 3 (2 modified, 1 created)

## Accomplishments
- `_generate_scripts` is continuity-aware: each scene N>0 receives the running "story so far" synopsis plus the full verbatim text of the immediately preceding successful scene (D-01).
- Added `_update_synopsis` helper that re-summarizes the entire synopsis under a ~400-word cap each scene (D-03), prose-only (D-04), through the provider-abstracted `chat_completion` with `json_mode=False` (D-02), graceful-degrading to the prior synopsis on failure.
- First/single scene keeps zero continuity context — behavior identical to before this phase (D-05).
- Continuity state advances only in the success branch, so a failed scene cannot poison `prev_scene_text` or the synopsis (D-05).
- `_generate_scripts` returns `{"screenplays": [...], "synopsis": <str>}` with the per-screenplay `{title, content, episode_index}` contract intact (D-07).
- The wizard apply path persists the returned synopsis into `screenplay_editor` `PhaseData.content` alongside the screenplays via the existing `flag_modified` pattern, with no migration (D-06).
- New test module verifies all four ROADMAP success criteria plus the return-contract guard (5 tests, all passing).

## Task Commits

Each task was committed atomically:

1. **Task 1: Synopsis-update helper + continuity threading** - `fb466cc` (feat)
2. **Task 2: Persist synopsis into screenplay_editor content** - `e034317` (feat)
3. **Task 3: Continuity generation tests** - `770ae95` (test)

**Plan metadata:** committed with this SUMMARY (docs).

_Note: Task 1 carried the inline `tdd="true"` flag; its behavior is verified by the Task 3 test module per the plan's task ordering (Task 1's own `<verify>` is an AST source check, run and passing)._

## Files Created/Modified
- `backend/app/services/template_ai_service.py` - Added `_update_synopsis`; threaded `synopsis`/`prev_scene_text` through the `_generate_scripts` loop with conditional continuity-block injection; updated the return to include a top-level `synopsis`.
- `backend/app/api/endpoints/wizards.py` - `script_writer_wizard` branch now reads `result.get("synopsis", "")` and writes it into `phase_data.content` alongside `screenplays`, keeping `flag_modified`.
- `backend/app/tests/test_continuity_generation.py` - New module: first-scene-no-block, later-scene-includes-prior-and-synopsis, synopsis-update-per-success, failed-scene-no-advance, per-screenplay-contract-unchanged.

## Decisions Made
- Synopsis-update tuning (Claude's Discretion per D-03/CONTEXT line 48-49): `temperature=0.3`, `max_tokens=700`, ~400-word instruction cap — low/stable for summarization, bounded for token cost (mitigates T-45-02).
- Continuity block implemented as one conditional f-string keyed on `(synopsis or prev_scene_text)`, reusing the existing conditional-injection idiom so the first/single-scene prompt is byte-for-byte equivalent to pre-phase behavior.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test mock side_effect made synchronous to avoid coroutine double-wrap**
- **Found during:** Task 3 (test module)
- **Issue:** An `async def __call__` used as an `AsyncMock` `side_effect` produced a `RuntimeWarning: coroutine was never awaited` and a test failure, because `AsyncMock` awaits its call and then receives an un-awaited coroutine from the async side_effect.
- **Fix:** Made `_MockChat.__call__` a regular (synchronous) function returning the string value; `AsyncMock` awaits the call itself once. Added an explanatory comment.
- **Files modified:** backend/app/tests/test_continuity_generation.py
- **Verification:** `pytest app/tests/test_continuity_generation.py -x -q` → 5 passed.
- **Committed in:** 770ae95 (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug, test-harness only)
**Impact on plan:** Test-harness mechanics only; no change to production behavior or plan scope. No scope creep.

## Issues Encountered
None — all production code worked first try; only the test mock needed the side_effect adjustment above.

## Verification Results

- `pytest app/tests/test_continuity_generation.py -x -q` → **5 passed**.
- `pytest app/tests/test_wizard_injection.py -q` → **3 passed** (no regression to the script_writer_wizard apply path).
- `pytest app/tests/test_bible_injection.py -q` (related sanity) → **13 passed**.
- Source check: `_generate_scripts` returns `{"screenplays": ..., "synopsis": ...}`; each item retains `title`/`content`/`episode_index`. PASS.
- Source check: `wizards.py` writes `synopsis` into `screenplay_editor` content with `flag_modified`; no migration file added. PASS.

## User Setup Required
None - no external service configuration required. No new packages installed; `chat_completion` consumed as-is.

## Next Phase Readiness
- Continuity mechanism is in place and self-contained. Phase 46 (FMT) can evaluate native vs json_mode formats over this loop without continuity rework.
- The persisted synopsis is output-only (never reused as a seed, D-07); Phase 49 (EVAL) regenerate/compare may revisit seeding a persisted synopsis if desired.
- No blockers.

## Self-Check: PASSED

- `backend/app/tests/test_continuity_generation.py` exists on disk: FOUND.
- Commits present: `fb466cc`, `e034317`, `770ae95` all in `git log`.
- All five Task 3 tests pass; no-regression check passes.

---
*Phase: 45-continuity-aware-generation*
*Completed: 2026-06-06*
