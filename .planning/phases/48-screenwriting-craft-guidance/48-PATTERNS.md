# Phase 48: Screenwriting Craft Guidance - Pattern Map

**Mapped:** 2026-06-06
**Files analyzed:** 2 (1 modified, 1 new)
**Analogs found:** 2 / 2 (both exact, in-codebase)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/app/services/template_ai_service.py` (`_generate_scripts` prompt) | service (prompt builder) | transform (config → prompt → LLM → screenplay) | the Phase 47 `character_block` + Phase 46 layout-rules tail, SAME function, SAME f-string | exact (in-file) |
| `backend/app/tests/test_craft_guidance.py` (new) | test | transform (mock LLM, capture prompt, assert anchors) | `test_character_voice_injection.py` / `test_continuity_generation.py` | exact |

---

## Pattern Assignments

### `backend/app/services/template_ai_service.py` — `_generate_scripts` (service, transform)

**Analog:** the same function. Three prior injection patterns already live in this exact f-string; the craft block is additive and mirrors them. DO NOT restructure the function — only add static text.

The prompt f-string is `template_ai_service.py:360-392`. Current injection order:
`## Project Context` → `{character_block}` (Phase 47) → runtime → `## Total scenes` → `## Full scene outline` → `{continuity_block}` (Phase 45) → `## YOUR TASK: Write scene` marker → scene data → custom guidance → Phase 46 layout-rules + native `TITLE:` tail.

#### Pattern 1 — Labeled, anchor-bearing instruction block (THE craft analog)

**Source:** Phase 47 character/voice block, `template_ai_service.py:347-358`

```python
# Character block — section + an explicit distinct/consistent-voice
# instruction. Emitted ONLY when characters exist; the empty/absent path
# collapses to "" so the prompt is byte-identical to Phase 46 (D-47-04).
# The anchor substring "distinct, consistent voice" is what the tests assert.
character_block = (
    f"""{character_section}

## Character Voice
Give each named character a DISTINCT, CONSISTENT voice — distinct vocabulary, rhythm, formality, and verbal tics — ..."""
    if character_section
    else ""
)
```

**Copy this convention, with ONE deliberate difference (D-48-04):**
- KEEP: the `## <Heading>` on its own line, the prose-instruction body, and especially the **"asserted anchor" comment** (line 350) that documents the exact substring the tests assert on. Phase 48 must carry a comment listing each of the four craft anchor substrings.
- CHANGE: the craft block is **UNCONDITIONAL** — it is NOT wrapped in an `if ... else ""` guard. It is a plain string literal inserted into the f-string for every scene (including the first/single scene), because craft applies to every scene. There is no config gate analogous to `if character_section`.

#### Pattern 2 — Where the block sits (distinct from layout)

**Source:** Phase 46 layout-rules + native-output tail, `template_ai_service.py:379-392`

```python
Write a proper screenplay for THIS scene using strict industry-standard layout:
- The scene heading (INT./EXT. LOCATION - TIME) is on its OWN line.
- Action lines are present-tense, visual, and describe only what can be seen or heard.
- Character cues are in ALL CAPS on their own line above the dialogue.
...
- Pace this scene for its role in the overall {runtime_target or 'short film'} runtime.
- Distribute the total runtime naturally across scenes — not all scenes need equal screen time.

Output the screenplay NATIVELY as plain text (NOT JSON, no markdown code fences).
The FIRST line MUST be exactly:
TITLE: <a short title for this scene>
...
```

**Placement (D-48-01):** Add the `## Screenwriting Craft` block as a SEPARATE labeled section near the layout rules — recommended just BEFORE the `Write a proper screenplay...` layout bullets (i.e. after the custom-guidance line ~377, before line 379), or immediately after the layout bullets and before the `Output the screenplay NATIVELY...` instruction. It must read as a distinct concern from layout. The pre-existing layout bullet "Action lines are present-tense, visual, and describe only what can be seen or heard" (line 381) STAYS; the craft block goes deeper on the four dimensions and frames show-don't-tell as a craft principle, not a layout rule.

**Preserve EXACTLY (D-48-04):** the `## YOUR TASK: Write scene` literal (line 371 — used by SCENE_MARKER routing in all 3 test suites), `json_mode=False` (line 403), `max_tokens=4000` (line 402), `temperature=0.7` (line 401), the `TITLE:` first-line + parser (lines 420-441), the per-screenplay `{title, content, episode_index}` (443-447), the `{screenplays, synopsis}` return (462), success-only continuity advance (451-452), the `[Generation failed: ...]` except branch (453-460).

#### The four required craft dimensions (D-48-02) — each needs a STABLE anchor substring

The wording is the planner's discretion, but each dimension must be unambiguously present with a stable anchor the test asserts on. The four:

1. **Subtext (CRAFT-03):** dialogue implies wants rather than declaring them; avoid lines that state intentions/emotions outright. Suggested anchor: a phrase containing **"on-the-nose"** (e.g. "avoid on-the-nose dialogue") and/or **"subtext"**.
2. **Action-line economy (CRAFT-02):** lean action blocks, present tense, concrete verbs, no filler. Suggested anchor: a phrase containing **"economical"** (or "economy").
3. **Show, don't tell:** convey emotion/character through visible behavior, NOT internal/unfilmable description. Suggested anchor: a phrase containing **"show, don't tell"** AND the concrete lever **"no internal or unfilmable description"** (CRAFT-02's explicit success-criterion phrase).
4. **Page pacing / white space:** vary rhythm, break dense action into shorter beats, let white space carry tension, no wall-of-text. Suggested anchor: a phrase containing **"white space"** and/or **"pacing"**.

---

### `backend/app/tests/test_craft_guidance.py` (test, transform)

**Analog:** `test_character_voice_injection.py` (closest — same in-prompt-anchor assertion style) and `test_continuity_generation.py` (the canonical scaffold both copy from).

**Reuse the scaffold verbatim** — copy these from `test_character_voice_injection.py:23-96`:

- Imports: `import asyncio`, `from unittest.mock import patch, AsyncMock`, `from app.services.template_ai_service import template_ai_service`.
- `SCENE_MARKER = "YOUR TASK: Write scene"` (the positive routing discriminator).
- `_make_config(num_scenes, characters=None)` (lines 38-47) — keep the optional `_characters` kwarg so the composition test (SC#4) can pass characters.
- `_scene_writer(content, title)` (lines 50-53) — `f"TITLE: {title}\n\n{content}"` native shape.
- `class _MockChat` (lines 56-83) — routes scene-vs-synopsis by `SCENE_MARKER`, records `self.scene_prompts`. (Phase 48 does NOT need `fail_scene_index`; the simpler `_MockChat` from `test_character_voice_injection.py` is sufficient.)
- `_run(config)` (lines 86-89) — `asyncio.run(template_ai_service._generate_scripts(config, "PROJECT CONTEXT", {}))`.
- `_CHARACTERS` fixture (lines 93-96) for the composition test.

**Anchor constants to define at module top (mirror line 35 convention):**

```python
SCENE_MARKER = "YOUR TASK: Write scene"
# The stable anchor substrings the craft block injects (Phase 48, D-48-02).
# Lowercase compare like test_character_voice_injection.py does for VOICE.
CRAFT_HEADER = "## Screenwriting Craft"     # exact heading the block uses
SUBTEXT_ANCHOR = "on-the-nose"              # CRAFT-03 lever
ECONOMY_ANCHOR = "economical"               # CRAFT-02 lever
SHOW_DONT_TELL_ANCHOR = "show, don't tell"
UNFILMABLE_ANCHOR = "no internal or unfilmable description"  # CRAFT-02 success-criterion phrase
PACING_ANCHOR = "white space"               # pacing/white-space dimension
```

**Test-assertion pattern** — copy the lowercase-prompt assertion style from `test_character_voice_injection.py:117-148`:

```python
def test_craft01_all_four_dimensions_present():
    mock = _MockChat(scene_contents=["SCENE ONE TEXT"])
    with patch("app.services.template_ai_service.chat_completion",
               new_callable=AsyncMock, side_effect=mock):
        _run(_make_config(1))
    prompt = mock.scene_prompts[0].lower()
    assert CRAFT_HEADER.lower() in prompt
    assert SUBTEXT_ANCHOR in prompt
    assert ECONOMY_ANCHOR in prompt
    assert SHOW_DONT_TELL_ANCHOR in prompt
    assert PACING_ANCHOR in prompt
```

**Tests to write (from CONTEXT specifics, lines 60-66):**
1. CRAFT-01: header + all four dimension anchors in the (first/single) scene prompt.
2. CRAFT-02: `UNFILMABLE_ANCHOR` ("no internal or unfilmable description") present.
3. CRAFT-03: `SUBTEXT_ANCHOR` ("on-the-nose" / subtext) present.
4. SC#4 / composition: multi-scene + `_characters` run — a LATER-scene prompt (e.g. `scene_prompts[1]` of a 2-scene run) contains the craft anchors AND the continuity markers (`"Story so far"`, `"Previous scene"`) AND the voice anchor (`"distinct, consistent voice"`) simultaneously. Add a loose bloat-guard upper-bound on `len(prompt)` (e.g. `< 20000`).
5. Always-on: the craft header appears in the first/single-scene prompt while `"Story so far"` and `"Previous scene"` are ABSENT there (proves unconditional craft does not regress `test_first_scene_has_no_continuity_block`).

---

## Shared Patterns

### Anchor-comment convention (the load-bearing project idiom)

**Source:** `template_ai_service.py:350` — `# The anchor substring "distinct, consistent voice" is what the tests assert.`
**Apply to:** the new craft block.

Every test-asserted prompt substring is documented in an inline comment beside where it is emitted, so a future edit that changes the wording sees the contract. Replicate this: above/within the craft block, comment the exact four anchor substrings the tests pin.

### Mock-by-prompt-marker test scaffold

**Source:** `test_continuity_generation.py:60-105` (canonical), copied into `test_character_voice_injection.py:56-89`.
**Apply to:** `test_craft_guidance.py`.

`template_ai_service` is a module-level singleton; patch `app.services.template_ai_service.chat_completion` with `AsyncMock(side_effect=_MockChat(...))`. The `_MockChat.__call__` is SYNCHRONOUS (AsyncMock awaits the call and uses the return value — an async side_effect would double-wrap into a coroutine). Route scene calls by `SCENE_MARKER` in the user message; everything else is the synopsis-update branch.

### Native-output contract (do not break)

**Source:** `test_continuity_generation.py:220-256` (`json_mode=False`, real newlines, no JSON encoding).
**Apply to:** nothing new — just DO NOT touch lines 396-462. Phase 48 adds prompt text only.

---

## CRITICAL: Anchor-collision guard (must not break the 21 green tests)

The craft block is UNCONDITIONAL, so it lands in EVERY scene prompt — including the first-scene prompt and the no-characters prompt. The chosen craft anchor substrings MUST NOT collide with strings other suites assert on, or those suites break:

| Existing asserted string | Suite / line | Craft must NOT contain it |
|--------------------------|--------------|---------------------------|
| `"Story so far"` | `test_continuity_generation.py:37,120` (asserts ABSENT in first scene) | craft text must not contain "Story so far" |
| `"Previous scene"` | `test_continuity_generation.py:38,121` (asserts ABSENT in first scene) | craft text must not contain "Previous scene" |
| `"distinct, consistent voice"` | `test_character_voice_injection.py:35,164,180` (asserts ABSENT when no characters) | craft text must not contain "distinct, consistent voice" |
| `"## Characters"` / `"## Character Voice"` | `test_character_voice_injection.py:162-163,178-179` (assert ABSENT when no characters) | craft heading must be `## Screenwriting Craft`, distinct from these |
| `"## YOUR TASK: Write scene"` | SCENE_MARKER, all 3 suites | leave the literal untouched |

Verified clear at map time: `grep` for `Screenwriting Craft`, `on-the-nose`, `unfilmable`, `white space` in `template_ai_service.py` returns nothing — none of the proposed craft anchors currently exist anywhere in the prompt, so they are safe, non-colliding additions. The suggested anchors above ("on-the-nose", "economical", "show, don't tell", "no internal or unfilmable description", "white space") are all distinct from every row in this table.

Also note `test_empty_characters_prompt_byte_identical_to_no_characters` (`test_character_voice_injection.py:183-201`) asserts the absent-vs-empty `_characters` prompts are IDENTICAL — an unconditional craft block (same text in both) preserves this, since it is added equally to both paths. Do NOT make the craft block depend on `characters`/`character_section`.

---

## No Analog Found

None. Both files have exact in-codebase analogs.

## Metadata

**Analog search scope:** `backend/app/services/template_ai_service.py` (in-file analogs for Phases 45/46/47), `backend/app/tests/test_character_voice_injection.py`, `backend/app/tests/test_continuity_generation.py`, `backend/app/tests/test_wizard_injection.py`.
**Files scanned:** 4
**Pattern extraction date:** 2026-06-06
