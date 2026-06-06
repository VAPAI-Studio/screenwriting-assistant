---
phase: 46-format-fidelity-native-vs-json-mode
plan: 01
subsystem: api
tags: [openai, anthropic, screenplay-generation, prompt-engineering, native-output, json-mode, fastapi]

# Dependency graph
requires:
  - phase: 45-continuity-aware-generation
    provides: "_generate_scripts sequential loop with running-synopsis + prev-scene continuity threading and the {screenplays, synopsis} return contract"
provides:
  - "Native (json_mode=False) screenplay generation for the scene-writing call — output preserves industry-standard formatting instead of being degraded by JSON string-encoding (FMT-01, FMT-02)"
  - "TITLE-line parser with scene-summary fallback that derives the per-screenplay title without JSON-wrapping the body (D-46-01)"
  - "Strengthened scene prompt asserting explicit industry-standard layout rules (D-46-02)"
affects: [character-voice, craft-guidance, output-side-by-side-compare, breakdown, shotlist]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Native-prose generation channel (json_mode=False) mirroring _update_synopsis for any LLM call whose output is human-formatted text rather than a machine-parsed object"
    - "Inline TITLE:-line parser with graceful summary fallback — never fail a unit of work over a missing/empty parse field"
    - "Self-defending native parser: tolerate a stray leading/trailing code fence the provider won't strip in native mode (fence-stripping is json_mode-gated in ai_provider.py)"

key-files:
  created: []
  modified:
    - "backend/app/services/template_ai_service.py — _generate_scripts scene call migrated to native output + TITLE parser"
    - "backend/app/tests/test_continuity_generation.py — native mock shape, marker-based routing, FMT assertions"

key-decisions:
  - "Adopted native screenplay output for the scene body and parsed the title off a TITLE: line, falling back to the scene summary (D-46-01) — never failing a scene over a missing title"
  - "Routed the test mock by the positive 'YOUR TASK: Write scene' marker (not json_mode, not 'story so far'/'running synopsis' which are ambiguous) since both scene and synopsis calls now use json_mode=False"
  - "Verified intent via a precise method-slice source assertion because the plan's verify slices on the first '_generate_scripts' occurrence (the call site), which sweeps in unrelated methods"

patterns-established:
  - "Native-output channel for human-formatted LLM text: json_mode=False, strip(), tolerate fence, no json.loads"
  - "Parse-with-fallback for optional structured fields extracted from native LLM text"

requirements-completed: [FMT-01, FMT-02]

# Metrics
duration: 3 min
completed: 2026-06-06
---

# Phase 46 Plan 01: Format Fidelity (Native vs JSON Mode) Summary

**Migrated the scene-writing generation call from JSON-wrapped `{title, content}` (json_mode=True) to native plain-text screenplay output (json_mode=False) with a TITLE-line parser and summary fallback, so industry-standard formatting is no longer degraded by JSON string-encoding — while preserving the Phase 45 continuity and return contract byte-for-byte.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-06-06T03:45:55Z
- **Completed:** 2026-06-06T03:48:51Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Scene-writing `chat_completion` call now runs `json_mode=False` (native channel), mirroring the proven `_update_synopsis` native-prose call (FMT-02, D-46-01).
- The scene body lands in `content` as native multi-line text with real newlines and no surrounding JSON braces — JSON string-encoding (`\n` escaping) no longer degrades formatting (FMT-01).
- Title is parsed off a leading `TITLE:` line (case-insensitive, fence-tolerant); when absent/empty it falls back to the scene `summary` and the scene never fails over a missing title (D-46-01).
- Scene prompt strengthened with explicit industry-standard layout rules (scene heading on its own line, present-tense action, CAPS character cues, parentheticals on their own line, dialogue beneath, blank line between elements) and the "Return a JSON object" tail removed (D-46-02).
- Phase 45 contract preserved exactly: per-screenplay `{title, content, episode_index}`, top-level `{screenplays, synopsis}`, success-only continuity advance, and the `[Generation failed: ...]` except branch (D-46-03).
- All 5 existing continuity tests still pass; 4 new FMT assertions added; `test_wizard_injection.py` and `test_bible_injection.py` remain green.

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate the scene-writing call to native output + TITLE-line parser** — `0418b9a` (feat)
2. **Task 2: Update continuity tests for native shape + add FMT assertions** — `3cd36ee` (test)

**Plan metadata:** committed with this SUMMARY (docs: complete plan)

_Note: This is a `type: execute` plan with per-task `tdd="true"`. Task 1's verify is a source assertion (not the suite), and Task 2 rewrote the mocks then ran the suite — so implementation-then-test ordering produced clean atomic commits without a separate RED commit._

## Files Created/Modified
- `backend/app/services/template_ai_service.py` — `_generate_scripts` scene call switched to `json_mode=False`; system prompt and tail no longer request JSON; native parser strips a stray code fence, splits a leading `TITLE:` line, and falls back to `summary`; preserved the success-only continuity advance, the `[Generation failed: ...]` except branch, and the `{screenplays, synopsis}` return.
- `backend/app/tests/test_continuity_generation.py` — `_scene_writer` returns a native `TITLE: ...\n\n<body>` string (real newlines, no `json.dumps`); `_MockChat` routes scene-vs-synopsis by the positive `"YOUR TASK: Write scene"` marker and records each scene call's `json_mode`; added 4 FMT tests (json_mode=False, native newlines without JSON escaping/braces, TITLE parse, summary fallback); module docstring updated.

## Decisions Made
- **Native output + TITLE-line title (D-46-01):** the scene body is generated natively and the title is parsed off a `TITLE:` first line; missing/empty title falls back to the scene summary so a scene never fails on a parse miss.
- **Mock routing by positive scene marker:** because both calls are now `json_mode=False`, the mock routes on `"YOUR TASK: Write scene"` (present only in the scene prompt) rather than `json_mode` or the ambiguous `"story so far"`/`"running synopsis"` strings (which also appear in later scene prompts' continuity block).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Plan/verification source-assertion slices on the wrong `_generate_scripts` occurrence**
- **Found during:** Task 1 (running the task `<verify>` automated check)
- **Issue:** The plan's verify uses `src.split('_generate_scripts')[1]`, which splits on the FIRST occurrence of the string `_generate_scripts` — the call site at line 75, not the method definition at line 305. The resulting slice spans lines 75–439 and sweeps in unrelated methods (e.g. lines 120, 240) that legitimately contain `"Return valid JSON only"`, so the `assert 'Return valid JSON only' not in body` fails even though the scene method is correct.
- **Fix:** Verified the plan's actual intent with a precise slice on the method definition: `src.split('async def _generate_scripts')[1].split('async def fill_blanks')[0]`. Against that scene-method slice, all four intent assertions pass — `json_mode=False` present, `Return valid JSON only` absent, `result = json.loads` absent, `TITLE` present. No production code change was needed; the implementation already satisfies the requirement. The imprecision is in the verify tooling string, not the code.
- **Files modified:** none (verification-tooling observation only)
- **Verification:** precise method-slice assertion prints `OK`; full continuity + wizard + bible suites green.
- **Committed in:** n/a (no code change)

---

**Total deviations:** 1 (1 blocking — verification-tooling slice imprecision, no code change required)
**Impact on plan:** No scope creep. The scene method behaves exactly as specified; only the plan's verify-script slice was too coarse. Intent fully verified via a precise method slice.

## Issues Encountered
None — planned work proceeded cleanly. The only friction was the verify-script slice imprecision documented above as a deviation.

## Known Stubs
None — no placeholder values, no unwired data sources. The native parser and prompt changes are fully wired into the existing `_generate_scripts` path.

## Threat Flags
None — backend-only output-channel change. No new endpoint, no new input source, no new auth surface, no new dependency. `git diff` confirms `requirements.txt` is unchanged; T-46-SC package-legitimacy gate not triggered. The native parser treats model text as opaque (`(text or "").strip()`, fence tolerance, no `json.loads`/`eval`/`exec`), satisfying T-46-01.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Native generation channel is the single, committed scene-writing shape (D-46-04: reasoned adoption, no runtime A/B toggle). Ready for Phase 47 (character voice) and Phase 48 (craft guidance), which build on this prompt/output path.
- Phase 49 (output side-by-side compare, EVAL-01) can now compare the cumulative native output against the prior JSON-wrapped baseline.
- No blockers.

## Self-Check: PASSED
- `backend/app/services/template_ai_service.py` — FOUND (modified, scene method uses `json_mode=False`, native parser present)
- `backend/app/tests/test_continuity_generation.py` — FOUND (native mock + 4 FMT tests)
- `.planning/phases/46-format-fidelity-native-vs-json-mode/46-01-SUMMARY.md` — FOUND (this file)
- Commit `0418b9a` — FOUND in git log
- Commit `3cd36ee` — FOUND in git log
- Verification: continuity 9 passed; wizard injection 3 passed; bible injection 13 passed; source method-slice assertion OK; requirements.txt unchanged

---
*Phase: 46-format-fidelity-native-vs-json-mode*
*Completed: 2026-06-06*
