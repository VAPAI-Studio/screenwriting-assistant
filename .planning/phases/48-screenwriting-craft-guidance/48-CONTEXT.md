# Phase 48: Screenwriting Craft Guidance - Context

**Gathered:** 2026-06-06
**Status:** Ready for planning
**Mode:** Autonomous smart-discuss (user unattended; grey areas decided by Claude with codebase-grounded rationale, recorded below for review)

<domain>
## Phase Boundary

The screenplay-generation prompt in `_generate_scripts` includes explicit craft guidance covering the four named craft dimensions (CRAFT-01): subtext in dialogue, action-line economy, show-don't-tell, and page pacing / white space. The resulting output has visual/economical action lines (CRAFT-02) and dialogue carrying subtext rather than on-the-nose intention statements (CRAFT-03). The craft guidance composes with the Phase 45 continuity block and Phase 47 character-voice block without bloating the prompt past token limits (SC#4).

**In scope:**
- Add a dedicated craft-guidance section to the per-scene prompt in `_generate_scripts`, distinct from the Phase 46 layout rules.
- Keep it concise so it composes with continuity + voice within the existing 4000-token output budget and a reasonable prompt size.

**Out of scope (deferred / other phases):**
- No automated craft scoring / linting of generated output (that quality judgment is the Phase 49 EVAL-01 side-by-side compare, not here — CRAFT-02/03 are delivered as prompt mechanism + human judgement, the tests assert the guidance is PRESENT and well-formed, not that the LLM obeyed it).
- No new model/dependency, no DB change, no frontend change.
- Phase 46 layout rules stay as-is (craft is additive, not a rewrite of layout).
</domain>

<decisions>
## Implementation Decisions

### D-48-01 — Add a distinct `## Screenwriting Craft` section, not more layout bullets (DECIDED: separate craft block)
**Grey area:** Phase 46 already added layout rules and a couple of craft-adjacent nudges ("action lines are present-tense, visual, describe only what can be seen or heard"). Do we extend those bullets or add a separate craft block?
**Decision:** Add a SEPARATE, clearly-labeled craft-guidance block (e.g. `## Screenwriting Craft`) to the prompt, distinct from the existing layout bullets. Rationale: SC#1 requires the prompt to *explicitly* cover the four craft dimensions by name; a dedicated section makes that coverage auditable (the tests can assert each dimension's anchor phrase is present) and keeps the layout-vs-craft concerns readable. The pre-existing "present-tense, visual, only what can be seen" layout bullet stays; the craft block goes deeper on the four dimensions. Where there is mild overlap (show-don't-tell ≈ the visual-action bullet), the craft block frames it as a craft principle ("reveal character and emotion through action and behavior, not narration") rather than a layout rule.

### D-48-02 — The four craft dimensions, concretely (DECIDED: subtext / action economy / show-don't-tell / pacing & white space)
**Decision:** The craft block must name and instruct all four CRAFT-01 dimensions with concrete, model-actionable phrasing:
1. **Subtext (CRAFT-03):** characters pursue goals indirectly; dialogue implies wants rather than declaring them; avoid on-the-nose lines that state intentions/emotions outright.
2. **Action-line economy (CRAFT-02):** action lines are lean (a few lines max per block), present tense, concrete verbs, no filler.
3. **Show, don't tell:** convey emotion/character through visible behavior and action, not internal/unfilmable description (no "she feels…", "he realizes…", "remembers that…").
4. **Page pacing / white space:** vary rhythm; break dense action into shorter beats; let white space carry tension; don't wall-of-text.
Exact wording is Claude's Discretion for the planner, but each of the four must be unambiguously present with a stable anchor substring the tests can assert (mirrors the Phase 47 "distinct, consistent voice" anchor pattern). The "no internal/unfilmable description" instruction is the concrete lever for CRAFT-02's "no internal or unfilmable description" success criterion.

### D-48-03 — Keep it tight; compose within token budget (DECIDED: concise static block, no per-scene bloat)
**Grey area:** SC#4 — craft guidance must not bloat the prompt past token limits when combined with continuity + voice.
**Decision:** The craft block is a CONCISE static instruction (target: a short labeled section, on the order of the Phase 47 voice block, not paragraphs per dimension). It is the same for every scene (not regenerated/expanded per scene), so it adds a fixed, bounded cost. The continuity synopsis is already word-capped (Phase 45 D-03) and only one prev-scene is injected verbatim (Phase 45 D-01), so the dominant variable-size inputs are already bounded; a fixed craft block does not threaten the budget. The `max_tokens=4000` output budget is unchanged. No dynamic/computed craft text.

### D-48-04 — Preserve all prior contracts (DECIDED: additive only)
**Decision:** The craft block is injected ADDITIVELY into the existing prompt f-string alongside `{project_context}`, `{character_block}` (Phase 47), the layout rules (Phase 46), and `{continuity_block}` (Phase 45). PRESERVE EXACTLY: the `"YOUR TASK: Write scene"` literal marker; the Phase 46 native-output shape (`json_mode=False`, `TITLE:` first line + parser); the per-screenplay `{title, content, episode_index}`; the `{screenplays, synopsis}` return; success-only continuity advance; the `[Generation failed: ...]` except branch. No behavioral change to any path other than the added craft text in the prompt. The craft block is unconditional (always present — unlike the character block which is conditional on `_characters`), because craft guidance applies to every scene including the first/single scene.
</decisions>

<code_context>
## Existing Code Insights

- `_generate_scripts` (template_ai_service.py:305-462) builds the per-scene prompt f-string (~360-393). Current order: `## Project Context` → `{character_block}` (Phase 47) → runtime → scene outline → `{continuity_block}` (Phase 45) → `## YOUR TASK: Write scene` marker → scene data → custom guidance → the Phase 46 layout-rules + native-output `TITLE:` instructions block (lines ~378-392).
- Phase 46 layout rules live in the prompt tail (lines ~378-388): heading on own line, present-tense visual action, CAPS cues, parentheticals, dialogue placement, blank lines between elements, pacing. The craft block should sit near these (a natural home is just before or after the layout bullets, clearly labeled `## Screenwriting Craft`), so layout + craft read together but stay distinct.
- Phase 47 voice block (lines ~347-358) is the pattern to mirror for a labeled, anchor-bearing instruction section — note its "asserted anchor" comment convention (line ~350) that documents the exact substring the tests assert; replicate that convention for the craft anchors.
- `max_tokens=4000` at the scene call (~line 401); `temperature=0.7`. Unchanged.
- Tests: `test_continuity_generation.py` (10), `test_character_voice_injection.py` (8), `test_wizard_injection.py` (3) all green and must stay green. The craft block is UNCONDITIONAL, so unlike the voice block it WILL appear in the first-scene prompt too — the continuity test `test_first_scene_has_no_continuity_block` asserts absence of the *continuity* markers ("Story so far"/"Previous scene"), NOT absence of craft text, so adding an always-on craft section does not break it. VERIFY this when planning: ensure the craft anchors do not collide with the continuity/voice marker strings the other suites assert on.
- Pre-existing test-isolation concern (see .planning/v6.0-PREEXISTING-TEST-CONCERN.md): some yolo/session-isolation tests are order-sensitive; this is NOT caused by phases 45-47 and is out of scope here. Phase 48 tests must pass in isolation like the other phase suites.
</code_context>

<specifics>
## Specific Ideas

- Surgical, backend-only, SINGLE production touch point: `_generate_scripts` prompt in `template_ai_service.py`. (No wizards.py change — craft guidance needs no new data; it is static prompt text.)
- Add a new test module `backend/app/tests/test_craft_guidance.py` (reuse the `_MockChat`/`_make_config`/`SCENE_MARKER` scaffold). Assert:
  1. CRAFT-01: the scene prompt contains the craft section and an anchor for EACH of the four dimensions (subtext, action economy / "economical", show-don't-tell, pacing / white space).
  2. CRAFT-02: the prompt contains the "no internal or unfilmable description" lever (or equivalent anchor).
  3. CRAFT-03: the prompt contains the subtext / "not on-the-nose" anchor.
  4. SC#4 / composition: the craft block coexists with the continuity block and the voice block in a multi-scene + characters run (assert all three present in a later-scene prompt) and the prompt is not absurdly large (a loose upper-bound length assertion is acceptable as a bloat guard).
  5. Always-on: the craft section appears even in the first/single-scene prompt (it is unconditional), while the continuity markers remain absent there (no regression to `test_first_scene_has_no_continuity_block`).
- Keep test_continuity_generation.py (10), test_character_voice_injection.py (8), test_wizard_injection.py (3) green.
- No migration, no frontend change, no new dependency. Preserve all Phase 45/46/47 contracts.
</specifics>

<deferred>
## Deferred Ideas

- Automated scoring of subtext / action economy in generated output — belongs with Phase 49 (EVAL-01) side-by-side compare.
- User-configurable craft intensity / per-project craft toggles — not requested; out of scope.
- Genre-specific craft profiles — out of scope; the static guidance is genre-neutral.
</deferred>
