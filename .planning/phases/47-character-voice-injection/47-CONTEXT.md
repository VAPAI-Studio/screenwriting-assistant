# Phase 47: Character Voice Injection - Context

**Gathered:** 2026-06-06
**Status:** Ready for planning
**Mode:** Autonomous smart-discuss (user unattended; grey areas decided by Claude with codebase-grounded rationale, recorded below for review)

<domain>
## Phase Boundary

Each character speaks in a distinct, consistent voice in generated dialogue because their voice profile reaches the **script-writing** prompt in `_generate_scripts`, not only the scene-planning prompt in `_generate_scenes` (VOICE-01). When a character has no explicit voice, a consistent voice is derived and carried forward across scenes rather than defaulting to a uniform style (VOICE-02). In a multi-character scene, dialogue is distinguishable — two characters do not sound interchangeable (VOICE-03).

**In scope:**
- Inject character ListItems (`PhaseData phase="story", subsection_key="characters"`) into the `script_writer_wizard` config path, the same way `scene_wizard` already does (`wizards.py:138-139`).
- Build a character-voice section into each scene-writing prompt in `_generate_scripts` (reusing/extending the existing `_build_character_section` helper, which `_generate_scenes` already uses).
- Make voice consistency hold across separate scene generations using the existing Phase 45 continuity mechanism (running synopsis + prev-scene text already threaded through `_generate_scripts`).

**Out of scope (deferred / other phases):**
- No new DB column / "voice" field on the character model, no migration. There is currently no dedicated `voice`/`diction` field on character ListItems; voice is derived from the existing character fields (name, description, personality, role, etc.) the user already authored.
- No new UI for editing voice profiles (no frontend change this phase).
- Craft guidance (subtext, action economy) is Phase 48; side-by-side compare is Phase 49.
</domain>

<decisions>
## Implementation Decisions

### D-47-01 — Inject `_characters` into the script_writer_wizard config (DECIDED: mirror the scene_wizard injection)
**Grey area:** How do character profiles reach `_generate_scripts`? Today `wizards.py:138` injects `config["_characters"] = _get_character_data(...)` ONLY when `request.wizard_type == "scene_wizard"`.
**Decision:** Extend that injection to also fire for `script_writer_wizard`. Concretely, change the guard so `_characters` is populated for both `scene_wizard` and `script_writer_wizard` (e.g. `if request.wizard_type in ("scene_wizard", "script_writer_wizard")`). `_get_character_data` already returns the right shape (`[{item_type, **content}]`) and the `config` dict already flows run_wizard → _run_wizard_background → wizard_generate → _generate_scripts unchanged. Rationale: reuses the exact, proven data path; no new query, no new plumbing. This is the literal mechanism Success Criterion 1 names ("from PhaseData story.characters ListItems … into the script-writing prompt").

### D-47-02 — Build a character-voice block in `_generate_scripts` prompts (DECIDED: reuse + extend `_build_character_section`)
**Grey area:** How are voices represented in the script prompt, and where?
**Decision:** In `_generate_scripts`, read `characters = config.get("_characters", [])` and build a character section using the existing `_build_character_section` helper (template_ai_service.py:163) — possibly a voice-focused variant that foregrounds voice/diction cues. Inject it into each scene-writing prompt (the prompt f-string around line 340-373), in addition to (not replacing) the existing `project_context` and continuity block. The section must instruct the model to give each named character a distinct, recognizable voice (vocabulary, rhythm, formality, verbal tics) and to keep that voice consistent. Rationale: `_build_character_section` is already the codebase's canonical character-to-prompt formatter and is already battle-tested in `_generate_scenes`. Reusing it keeps scene-planning and script-writing character framing consistent. Whether to add a small voice-emphasis variant vs. reuse as-is is **Claude's Discretion** for the planner — but the script prompt MUST surface per-character voice guidance, not just list characters.

### D-47-03 — Derive/carry voice when none is explicitly defined (DECIDED: prose-derived voice carried by the continuity synopsis)
**Grey area:** VOICE-02 — characters with no explicit voice field. Where does a "derived voice" live and how does it persist across scenes?
**Decision:** No new structured voice store. Voice for an under-specified character is derived implicitly from their existing character fields + how they were first written, and carried forward by the Phase 45 running synopsis + previous-scene-full-text already injected into every later `_generate_scripts` prompt. The prompt instructs the model: where a character has no explicit voice cues, establish a consistent voice for them and keep it consistent with how they have already spoken in earlier scenes (which the model can see via the prev-scene text and synopsis). Rationale: a structured per-character voice ledger is the heavier alternative and mirrors the D-04 decision from Phase 45 (prose carries continuity, no structured ledger) — stay consistent with that architecture. Distinctiveness (VOICE-03) and cross-scene consistency (SC#4) are delivered by (a) the explicit "make each character distinct" instruction and (b) the continuity context the character has already-spoken lines in.

### D-47-04 — Failure / contract behavior unchanged (DECIDED: preserve Phase 45/46 contract)
**Decision:** No change to the return contract (`{screenplays:[{title,content,episode_index}], synopsis}`), the success-only continuity advance, the `[Generation failed: ...]` except branch, or the native-output (json_mode=False) shape from Phase 46. When `_characters` is empty/absent, the prompt simply omits the character-voice block (no behavior change vs. today). Character injection must never make a scene fail — an empty character list yields an empty section, exactly as `_build_character_section([])` already returns "".
</decisions>

<code_context>
## Existing Code Insights

- `wizards.py:136-139` injects `config["_characters"] = _get_character_data(db, project.id)` for `scene_wizard` only — the single line to extend for `script_writer_wizard`.
- `_get_character_data` (wizards.py:44-57) returns `[{item_type, **(li.content or {})}]` from `PhaseData(phase="story", subsection_key="characters")` ListItems ordered by sort_order.
- `config` flows verbatim from run_wizard → `_run_wizard_background` → `template_ai_service.wizard_generate(config=config, ...)` → `_generate_scripts(config, ...)`. So `config.get("_characters")` is available inside `_generate_scripts` once injected.
- `_build_character_section(characters)` (template_ai_service.py:163-175) formats a `## Characters` block with `### {item_type}: {name}` + bulleted fields; returns "" for an empty list. Already consumed by `_generate_scenes` (line 194).
- `_generate_scripts` (template_ai_service.py:305-437) builds the per-scene prompt f-string (~340-373) with `project_context`, runtime, scene outline, the Phase 45 continuity block, and the Phase 46 native-output instructions. The character-voice block injects here.
- Phase 45 continuity: `synopsis` + `prev_scene_text` already threaded and injected — the carrier for cross-scene voice consistency (VOICE-02, SC#4).
- Tests: `test_continuity_generation.py` patches `app.services.template_ai_service.chat_completion`; `_make_config` builds the episodes config. New tests should add `_characters` to the config and assert the scene prompt contains each character's name/voice cue. `test_wizard_injection.py` covers the wizards.py apply/run path — keep green.
</code_context>

<specifics>
## Specific Ideas

- Surgical, backend-only. Two production touch points: `wizards.py` (extend the `_characters` injection guard to include `script_writer_wizard`) and `template_ai_service.py:_generate_scripts` (read `_characters`, build + inject a voice section, add the distinct-voice instruction).
- Tests to add/extend (likely a new `test_character_voice_injection.py` or additions to the continuity module):
  1. Script-writing prompt contains each provided character's name (VOICE-01) — proves voices reach `_generate_scripts`, not just `_generate_scenes`.
  2. The prompt carries an explicit "distinct / consistent voice" instruction (VOICE-03).
  3. With `_characters` empty/absent, the prompt has no character block and behavior matches Phase 46 (no regression; the continuity tests must still pass).
  4. (wizards path) `script_writer_wizard` now gets `_characters` injected into config — assert `_get_character_data` is invoked for that wizard type (or that the config passed to the background task includes `_characters`).
- No migration. No frontend change. No new dependency. Preserve the Phase 46 native-output contract.
</specifics>

<deferred>
## Deferred Ideas

- A dedicated structured `voice`/`diction` field on the character model + UI to edit it — heavier; not required (voice derives from existing fields + continuity). Revisit only if prose-derived voice proves insufficient.
- A per-character voice "ledger" persisted across runs — same rationale as Phase 45's no-structured-ledger decision; the continuity synopsis carries it.
- Automated distinctiveness scoring / eval of dialogue separation — belongs with Phase 49 (EVAL-01) side-by-side compare, not here.
</deferred>
