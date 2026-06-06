# backend/app/tests/test_craft_guidance.py

"""
Tests for screenwriting-craft guidance injection into script writing
(Phase 48, CRAFT-01/02/03).

Phase 46 added strict-layout rules and Phase 47 added a conditional character /
voice block. Phase 48 adds a DISTINCT, UNCONDITIONAL `## Screenwriting Craft`
section to every per-scene SCRIPT-WRITING prompt, naming the four craft
dimensions (CRAFT-01):
  - subtext in dialogue (CRAFT-03)            -> anchor "on-the-nose" / "subtext"
  - action-line economy (CRAFT-02)            -> anchor "economical"
  - show, don't tell (CRAFT-02)               -> anchors "show, don't tell" +
                                                 "no internal or unfilmable description"
  - page pacing / white space                 -> anchor "white space"

The craft block is UNCONDITIONAL (D-48-02/D-48-04): it appears in every scene
prompt including the first/single scene and the no-characters path. Its anchors
MUST NOT collide with the continuity markers ("Story so far" / "Previous scene")
nor the voice anchor ("distinct, consistent voice") that other suites assert
ABSENT in first-scene / no-character runs.

Scaffold copied verbatim from test_character_voice_injection.py: the scene-writing
call uses json_mode=False and the side-effect routes scene-vs-synopsis calls by the
positive SCENE_MARKER in the user prompt. template_ai_service is a module-level
singleton patched via app.services.template_ai_service.chat_completion.
"""

import asyncio

from unittest.mock import patch, AsyncMock

from app.services.template_ai_service import template_ai_service


# Positive, unambiguous discriminator for a scene-writing call (template_ai_service.py).
SCENE_MARKER = "YOUR TASK: Write scene"

# The stable anchor substrings the craft block injects (Phase 48, D-48-02).
# Lowercase compare like test_character_voice_injection.py does for VOICE.
CRAFT_HEADER = "## Screenwriting Craft"     # exact heading the block uses
SUBTEXT_ANCHOR = "on-the-nose"              # CRAFT-03 lever
ECONOMY_ANCHOR = "economical"               # CRAFT-02 lever
SHOW_DONT_TELL_ANCHOR = "show, don't tell"
UNFILMABLE_ANCHOR = "no internal or unfilmable description"  # CRAFT-02 success-criterion phrase
PACING_ANCHOR = "white space"               # pacing/white-space dimension

# Continuity markers asserted ABSENT in a first/single scene (no-regression contract).
SYNOPSIS_MARKER = "Story so far"
PREV_SCENE_MARKER = "Previous scene"
# Voice anchor (present only with characters) used by the composition test.
VOICE_INSTRUCTION_ANCHOR = "distinct, consistent voice"


def _make_config(num_scenes, characters=None):
    """Minimal config for _generate_scripts; optionally carries _characters."""
    cfg = {
        "episodes": [
            {"summary": f"Scene {i + 1} summary"} for i in range(num_scenes)
        ]
    }
    if characters is not None:
        cfg["_characters"] = characters
    return cfg


def _scene_writer(content, title="A Scene"):
    """A NATIVE plain-text screenplay string (Phase 46): leading TITLE line, blank
    line, then the body with real newlines."""
    return f"TITLE: {title}\n\n{content}"


class _MockChat:
    """Side-effect callable routing scene vs synopsis calls by prompt content.

    Records each scene call's prompt in self.scene_prompts (routed by
    SCENE_MARKER); every other call is the synopsis-update else-branch.
    """

    def __init__(self, scene_contents, synopsis_text="SYNOPSIS_PROSE"):
        self.scene_contents = scene_contents
        self.synopsis_text = synopsis_text
        self.scene_prompts = []
        self.synopsis_calls = 0
        self._scene_idx = 0

    def __call__(self, *args, **kwargs):
        messages = kwargs.get("messages", [])
        user_msg = next(
            (m["content"] for m in messages if m.get("role") == "user"), ""
        )
        if SCENE_MARKER in user_msg:
            idx = self._scene_idx
            self.scene_prompts.append(user_msg)
            self._scene_idx += 1
            content = self.scene_contents[idx]
            return _scene_writer(content, title=f"Scene {idx + 1}")
        else:
            self.synopsis_calls += 1
            return self.synopsis_text


def _run(config):
    return asyncio.run(
        template_ai_service._generate_scripts(config, "PROJECT CONTEXT", {})
    )


# Two characters whose dicts mirror the _get_character_data shape.
_CHARACTERS = [
    {"item_type": "protagonist", "name": "MAYA", "personality": "wry, terse"},
    {"item_type": "antagonist", "name": "VICTOR", "personality": "formal, cold"},
]


def test_craft01_all_four_dimensions_present():
    """CRAFT-01: the (first/single) scene prompt contains the craft header and an
    anchor for ALL FOUR craft dimensions."""
    mock = _MockChat(scene_contents=["SCENE ONE TEXT"])
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        _run(_make_config(1))

    assert len(mock.scene_prompts) == 1
    prompt = mock.scene_prompts[0].lower()
    assert CRAFT_HEADER.lower() in prompt
    assert SUBTEXT_ANCHOR in prompt
    assert ECONOMY_ANCHOR in prompt
    assert SHOW_DONT_TELL_ANCHOR in prompt
    assert PACING_ANCHOR in prompt


def test_craft02_show_dont_tell_and_economy_levers():
    """CRAFT-02: the prompt carries the concrete 'no internal or unfilmable
    description' lever AND an 'economical' action-economy anchor."""
    mock = _MockChat(scene_contents=["SCENE ONE TEXT"])
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        _run(_make_config(1))

    prompt = mock.scene_prompts[0].lower()
    assert UNFILMABLE_ANCHOR in prompt
    assert ECONOMY_ANCHOR in prompt


def test_craft03_subtext_anchor_present():
    """CRAFT-03: the prompt instructs subtext via an 'on-the-nose' / 'subtext'
    anchor."""
    mock = _MockChat(scene_contents=["SCENE ONE TEXT"])
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        _run(_make_config(1))

    prompt = mock.scene_prompts[0].lower()
    assert SUBTEXT_ANCHOR in prompt or "subtext" in prompt


def test_sc4_craft_composes_with_continuity_and_voice():
    """SC#4: in a 2-scene run WITH characters, the later-scene prompt carries the
    craft block, the Phase 45 continuity block, and the Phase 47 voice block
    simultaneously — under a loose bloat-guard length bound."""
    mock = _MockChat(scene_contents=["FIRST SCENE BODY", "second scene body"])
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        _run(_make_config(2, characters=_CHARACTERS))

    assert len(mock.scene_prompts) == 2
    later = mock.scene_prompts[1]
    lower = later.lower()
    # Craft block (Phase 48)
    assert CRAFT_HEADER.lower() in lower
    # Continuity block (Phase 45)
    assert SYNOPSIS_MARKER in later
    assert PREV_SCENE_MARKER in later
    # Voice block (Phase 47)
    assert VOICE_INSTRUCTION_ANCHOR in lower
    # Loose bloat guard
    assert len(later) < 20000
    # Tight bloat guard: the craft block must appear exactly once (catches
    # accidental duplication that the loose length bound would miss).
    assert lower.count(CRAFT_HEADER.lower()) == 1


def test_craft_always_on_no_continuity_regression():
    """Always-on / no regression: a single-scene NO-characters run still carries
    the craft header, while the continuity markers stay ABSENT (proves the
    unconditional craft block does not regress test_first_scene_has_no_continuity_block)."""
    mock = _MockChat(scene_contents=["SCENE ONE TEXT"])
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        _run(_make_config(1))

    assert len(mock.scene_prompts) == 1
    prompt = mock.scene_prompts[0]
    assert CRAFT_HEADER in prompt
    assert SYNOPSIS_MARKER not in prompt
    assert PREV_SCENE_MARKER not in prompt


def test_craft_block_present_in_generate_scripts_source():
    """Pin the production prompt independent of mock routing: the actual source of
    the per-scene prompt builder carries the craft header and the four dimension
    anchors (mirror test_character_voice_injection.py:230-237).

    Phase 49 (D-49-01) extracted the per-scene prompt body out of
    _generate_scripts into the shared _generate_one_scene helper (used by both the
    batch loop and regenerate_single_scene). The craft block lives there now, so
    this source-pin inspects _generate_one_scene — the single production source of
    the scene prompt."""
    import inspect

    src = inspect.getsource(template_ai_service._generate_one_scene)
    assert CRAFT_HEADER in src
    assert SUBTEXT_ANCHOR in src
    assert ECONOMY_ANCHOR in src
    assert SHOW_DONT_TELL_ANCHOR in src
    assert UNFILMABLE_ANCHOR in src
    assert PACING_ANCHOR in src
