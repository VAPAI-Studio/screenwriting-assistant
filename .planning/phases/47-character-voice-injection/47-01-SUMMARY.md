---
phase: 47-character-voice-injection
plan: 01
subsystem: api
tags: [openai, prompts, screenwriting, character-voice, wizards, fastapi]

# Dependency graph
requires:
  - phase: 45-continuity-aware-generation
    provides: "_generate_scripts running synopsis + prev-scene continuity block (carries voice across scenes)"
  - phase: 46-native-screenplay-output
    provides: "_generate_scripts native json_mode=False output + TITLE-line parser + SCENE_MARKER contract"
provides:
  - "Character voice profiles routed into the script-writing prompt in _generate_scripts (not only scene planning)"
  - "Explicit distinct/consistent-voice instruction in every per-scene script prompt"
  - "script_writer_wizard now injects config['_characters'] like scene_wizard"
affects: [phase-48-craft-guidance, phase-49-side-by-side-compare]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Reuse _build_character_section (empty-list-safe) to inject character context into AI prompts"
    - "Conditional prompt block (character_block) collapses to '' so the empty path stays byte-identical to the prior phase"

key-files:
  created:
    - backend/app/tests/test_character_voice_injection.py
  modified:
    - backend/app/api/endpoints/wizards.py
    - backend/app/services/template_ai_service.py

key-decisions:
  - "D-47-01: broaden the run_wizard injection guard to wizard_type in ('scene_wizard', 'script_writer_wizard') — reuse the proven config-passthrough path, no new plumbing"
  - "D-47-02: reuse _build_character_section as-is; supply voice EMPHASIS via prompt instruction text rather than a new formatter"
  - "D-47-03: no structured voice store — derive/carry voice via the Phase 45 continuity block; the instruction directs the model to keep voice consistent with earlier scenes"
  - "D-47-04: empty/absent _characters collapses character_block to '' → prompt byte-identical to Phase 46; injection never fails a scene"
  - "Anchor substring chosen: 'distinct, consistent voice' (case-insensitive in tests)"
  - "Wizards-path test uses a focused unit check of the guard logic + a source-mirror assertion (test_wizard_injection.py tests the agent-review middleware, NOT this guard, so a route-level analog was deliberately avoided)"

patterns-established:
  - "Conditional prompt-block-or-empty-string keeps no-data paths byte-identical to the prior phase"
  - "Source-mirror assertion (inspect.getsource) guards a focused unit check from diverging from production"

requirements-completed: [VOICE-01, VOICE-02, VOICE-03]

# Metrics
duration: 4min
completed: 2026-06-06
---

# Phase 47 Plan 01: Character Voice Injection Summary

**Character profiles now reach the script-writing prompt in `_generate_scripts` with an explicit distinct/consistent-voice instruction, so generated dialogue distinguishes characters — backend-only, preserving the Phase 45 continuity and Phase 46 native-output contracts exactly.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-06-06T11:51:48Z
- **Completed:** 2026-06-06T11:55:29Z
- **Tasks:** 3
- **Files modified:** 3 (2 production, 1 new test)

## Accomplishments
- Broadened the `wizards.py` `run_wizard` injection guard so `config["_characters"]` is injected for `script_writer_wizard` as well as `scene_wizard` (D-47-01). The persisted `WizardRun(config=request.config)` split is preserved — `_characters` lives only on the in-memory background-task config.
- `_generate_scripts` now reads `characters = config.get("_characters", [])`, builds the section once via the reused `_build_character_section`, and injects a `character_block` (the `## Characters` section + a `## Character Voice` instruction) additively after `## Project Context`, before the continuity block and the `YOUR TASK: Write scene` marker. The voice instruction directs each named character to have a DISTINCT, CONSISTENT voice and, where no explicit cue exists, to derive one and keep it consistent with earlier scenes (carried by the Phase 45 continuity block).
- Added `test_character_voice_injection.py` (8 tests) proving names + the voice instruction reach the script prompt, that the no-character path produces no block, and that the broadened wizard guard injects `_characters` for `script_writer_wizard`.

## Voice-instruction substring (anchor)

The fixed, test-asserted phrase injected into every script prompt with characters:

> Give each named character a **DISTINCT, CONSISTENT voice** — distinct vocabulary, rhythm, formality, and verbal tics — so that two characters in the same scene never sound interchangeable. Where a character has no explicit voice cues, establish a voice for them and keep it consistent with how they have already spoken in earlier scenes (visible via the previous-scene text and the running synopsis above).

Tests assert the case-insensitive anchor `"distinct, consistent voice"` and the carry-forward clause `"consistent with how they have already spoken in earlier scenes"`.

## Task Commits

1. **Task 1: Inject _characters for script_writer_wizard in wizards.py** - `cb216eb` (feat)
2. **Task 2: Read _characters and inject character-voice section in _generate_scripts** - `1f938cc` (feat)
3. **Task 3: Add test_character_voice_injection.py** - `536edbd` (test)

## Files Created/Modified
- `backend/app/api/endpoints/wizards.py` - Broadened the injection guard to `wizard_type in ("scene_wizard", "script_writer_wizard")`; comment updated. `_get_character_data` and `apply_wizard_result_to_db` untouched; persisted-row split preserved.
- `backend/app/services/template_ai_service.py` - `_generate_scripts` reads `_characters`, builds `character_section` once, and injects a conditional `character_block` (section + voice instruction) into each per-scene prompt. Empty/absent `_characters` → `character_block = ""` → byte-identical Phase 46 prompt.
- `backend/app/tests/test_character_voice_injection.py` - New; 8 tests covering VOICE-01 (names), VOICE-03/02 (voice instruction + carry-forward), D-47-04 (empty/absent → no block, empty == absent byte-identical), D-47-01 (guard fires for script_writer_wizard, source-mirror assertion).

## Contract Preservation (Phase 45 / Phase 46)
- `YOUR TASK: Write scene` literal SCENE_MARKER intact (line 371); the character block lands BEFORE the continuity block + marker, never altering the marker substring.
- `chat_completion(..., json_mode=False)` native channel unchanged (line 403).
- Return contract `{"screenplays": [...], "synopsis": synopsis}` unchanged.
- Success-only continuity advance and the `[Generation failed: {str(e)}]` except branch unchanged.
- TITLE-line parse + summary fallback unchanged.
- No migration, no frontend change, no new pip package.

## Verification

All three plan-level suites green:

| Suite | Result |
|-------|--------|
| `test_character_voice_injection.py` | **8 passed** |
| `test_continuity_generation.py` (no regression) | **10 passed** |
| `test_wizard_injection.py` (no regression) | **3 passed** |

Source assertions confirmed: broadened guard in `wizards.py:138`; `config.get("_characters"` in `_generate_scripts`; `character_section`/`character_block` built + injected; SCENE_MARKER intact; `json_mode=False` intact.

## Requirements → changes
- **VOICE-01** (profiles reach the script prompt) — Task 1 (guard) + Task 2 (`_generate_scripts` reads `_characters`, names appear in prompt). Tested.
- **VOICE-02** (derive/carry voice when none explicit) — Task 2 voice instruction's carry-forward clause + the Phase 45 continuity block as carrier (D-47-03). Tested via instruction substring.
- **VOICE-03** (characters distinguishable) — Task 2 distinct-voice instruction. Tested.
- **D-47-01** — Task 1 guard. Tested. **D-47-02** — reuse `_build_character_section`. **D-47-03** — continuity-carried voice. **D-47-04** — empty/absent collapse, tested byte-identical.

## Decisions Made
- Combined the character section and voice instruction into one conditional `character_block` variable that collapses to `""` when no characters exist. This guarantees D-47-04 byte-identicality (an earlier draft using two separate f-string slots added an extra blank line on the empty path — caught and corrected before committing Task 2).
- Wizards-path test (D-47-01) uses plan option (a): a focused unit check of the guard logic plus an `inspect.getsource` source-mirror assertion, per the plan-checker warning that `test_wizard_injection.py` is not a usable route-level analog (it tests the agent-review middleware).

## Deviations from Plan

None - plan executed exactly as written. (One in-flight correction to keep the empty path byte-identical was made and verified before the Task 2 commit; it is the implementation of D-47-04 as specified, not a deviation.)

## Issues Encountered
- The initial Task 2 prompt edit used two separate f-string slots (`{character_section}` and `{voice_instruction}`), which produced one extra blank line on the empty path — not byte-identical to Phase 46. Resolved by merging both into a single conditional `character_block` that yields `""` when empty, restoring byte-identicality. Verified by `test_empty_characters_prompt_byte_identical_to_no_characters` and the unmodified continuity suite.
- The full backend suite shows **4 pre-existing failures** unrelated to this plan (`test_session_isolation.py::test_orchestrate_uses_session_factory`, three in `test_yolo_integration.py`). Confirmed pre-existing by reverting both production files to the pre-phase-47 baseline (commit `aa623f3`) and reproducing the identical 4 failures. Out of scope; logged to `deferred-items.md`. Not touched.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Character voices now reach script generation — ready for Phase 48 (craft guidance: subtext, action economy) and Phase 49 (side-by-side compare / EVAL-01).
- No blockers introduced. The 4 pre-existing YOLO/session-isolation failures are tracked in `deferred-items.md` and should be triaged separately.

## Known Stubs
None — no stubbed data paths or placeholders introduced.

## Self-Check: PASSED
- `backend/app/tests/test_character_voice_injection.py` — FOUND
- `backend/app/api/endpoints/wizards.py` (guard broadened) — FOUND
- `backend/app/services/template_ai_service.py` (character_block injected) — FOUND
- Commit `cb216eb` (Task 1) — FOUND
- Commit `1f938cc` (Task 2) — FOUND
- Commit `536edbd` (Task 3) — FOUND

---
*Phase: 47-character-voice-injection*
*Completed: 2026-06-06*
