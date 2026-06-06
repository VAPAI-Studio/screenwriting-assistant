---
phase: 47-character-voice-injection
reviewed: 2026-06-06T12:04:27Z
depth: deep
files_reviewed: 3
files_reviewed_list:
  - backend/app/api/endpoints/wizards.py
  - backend/app/services/template_ai_service.py
  - backend/app/tests/test_character_voice_injection.py
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
status: clean
---

# Phase 47: Code Review Report

**Reviewed:** 2026-06-06T12:04:27Z
**Depth:** deep
**Files Reviewed:** 3
**Status:** clean

## Summary

Phase 47 routes the project's persisted character ListItems into the
`script_writer_wizard` per-scene prompts and adds a distinct/consistent-voice
instruction. The change is small and surgical: a one-token broadening of the
injection guard in `run_wizard`, and a conditional character/voice block in
`_generate_scripts` that reuses the existing empty-safe `_build_character_section`.

I traced every correctness, contract, and security concern raised in the review
brief and found no MEDIUM-or-higher defects. The implementation is correct,
contract-preserving, and adds no new security surface. Two INFO-level
observations are recorded for completeness; neither warrants a change.

### Correctness — verified

- **Guard does not persist `_characters` onto `WizardRun`.**
  `wizards.py:137` builds a copy (`config = dict(request.config)`), mutates only
  that copy at `:139`, and `WizardRun(...)` at `:145` is constructed with the raw
  `config=request.config`. The mutated dict flows only to the background task
  (`:158`). `_characters` is never written to the DB row. Correct.

- **Guard broadening is exact and scoped.**
  `wizards.py:138` matches `("scene_wizard", "script_writer_wizard")` and nothing
  else; `idea_wizard` and others get no `_characters` key (asserted by
  `test_d4701_script_writer_wizard_injects_characters`). The source-mirror test
  (`test_d4701_guard_source_includes_script_writer_wizard`) prevents the focused
  unit check from drifting from production.

- **`_generate_scripts` reads and conditionally injects correctly.**
  `template_ai_service.py:309` reads `config.get("_characters", [])`;
  `:317` builds the section once (it does not vary per scene); `:351-358` emits
  the character/voice block only when `character_section` is truthy. An
  absent/empty list yields `""` from `_build_character_section` (`:165-166`), so
  the block collapses to `""`.

- **Empty/absent path is byte-identical to Phase 46.**
  In the Phase 46 baseline (commit b1c0dff) the template is
  `{project_context}\n\n{runtime...}`. Phase 47 inserts `{character_block}` on
  its own line: `{project_context}\n{character_block}\n{runtime...}`. With
  `character_block == ""` this reduces to `{project_context}\n\n{runtime...}` —
  identical, no stray blank line. Confirmed mechanically by
  `test_empty_characters_prompt_byte_identical_to_no_characters` (passing).

### Contract preservation — verified

- SCENE_MARKER literal `## YOUR TASK: Write scene` intact at
  `template_ai_service.py:371`.
- Character block is additive: it is inserted between Project Context and the
  runtime line (`:364`) and does NOT displace the Phase 45 continuity block
  (still at `:371`, immediately before the scene-task marker) or the Phase 46
  native-output instructions (`:379+`). Both coexist when characters exist
  (`test_voice03_instruction_on_every_scene_prompt`).
- Return shape unchanged: scene objects remain `{title, content, episode_index}`
  and the function still returns `{screenplays, synopsis}`.
- Success-only continuity advance and the `[Generation failed:]` exception branch
  are untouched by this phase.
- `json_mode=False` for the scene-writing call is preserved.

### Security — no new surface

Character data is the user's own already-persisted `ListItem` content. The exact
same data already flows into `_generate_scenes` via the identical
`_build_character_section` (`template_ai_service.py:194`), so Phase 47 introduces
no new injection surface. Values are interpolated as already-evaluated strings
inside the f-string (`{v}` at `:174`); there is no second-pass evaluation,
`eval`, or templating, so brace/markdown content in a character field is rendered
as inert prose — same baseline behavior as the scene path. No CRITICAL/HIGH
concern.

## Info

### IN-01: Character-block construction duplicated between the two generators

**File:** `backend/app/services/template_ai_service.py:347-358` (and `:204-206` in `_generate_scenes`)
**Issue:** `_generate_scripts` builds its character/voice block inline. The
`_build_character_section` helper is correctly reused, but the surrounding
"## Character Voice" instruction is a script-only literal. This is fine for now
(the scene generator deliberately does not carry the voice instruction), so the
duplication is intentional, not a defect.
**Fix:** No change required. If a third generator ever needs the voice
instruction, extract it into a `_build_character_voice_block(section)` helper to
avoid divergence.

### IN-02: Voice-instruction anchor casing is fixed by an implicit contract

**File:** `backend/app/services/template_ai_service.py:355`
**Issue:** The prompt emits `DISTINCT, CONSISTENT voice` (caps) while the test
anchor (`test_character_voice_injection.py:35`) matches the lowercased
`"distinct, consistent voice"` via `.lower()`. The coupling is sound today, but
the contract between prompt wording and the test anchor is implicit — a future
reword (e.g. "distinct and consistent") would silently break VOICE-03 coverage.
**Fix:** No change required. Optionally add a short comment at `:355` noting the
substring is an asserted anchor (a similar note already exists at `:350`).

---

_Reviewed: 2026-06-06T12:04:27Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
