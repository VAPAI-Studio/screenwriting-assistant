# backend/app/tests/test_character_voice_injection.py

"""
Tests for character-voice injection into script writing (Phase 47, VOICE-01/02/03).

Phase 45 routed character profiles into _generate_scenes only. Phase 47 routes
them into _generate_scripts too, so each per-scene SCRIPT-WRITING prompt now
carries:
  - every provided character's NAME (VOICE-01),
  - an explicit DISTINCT/CONSISTENT-voice instruction (VOICE-03),
  - guidance to derive + carry a voice forward when none is explicit, leaning on
    the Phase 45 continuity block (VOICE-02).

With _characters empty/absent, the script prompt has NO character block and is
byte-identical to Phase 46 (D-47-04).

Scaffold copied from test_continuity_generation.py: the scene-writing call uses
json_mode=False and the side-effect routes scene-vs-synopsis calls by the
positive SCENE_MARKER in the user prompt. template_ai_service is a module-level
singleton patched via app.services.template_ai_service.chat_completion.
"""

import asyncio

from unittest.mock import patch, AsyncMock

from app.services.template_ai_service import template_ai_service
from app.api.endpoints import wizards


# Positive, unambiguous discriminator for a scene-writing call (template_ai_service.py).
SCENE_MARKER = "YOUR TASK: Write scene"

# The stable distinct/consistent-voice anchor injected by _generate_scripts (Task 2).
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
        # Prompt caching (Phase 1) split the scene prompt into a stable system
        # prefix (craft/layout/characters/outline) and a volatile user tail
        # (continuity + this scene's task). Record the FULL prompt (all system
        # blocks + the user tail) so anchor assertions see both halves; route
        # scene-vs-synopsis by the user tail where SCENE_MARKER lives.
        full_prompt = "\n".join(
            (m["content"] if isinstance(m["content"], str) else str(m["content"]))
            for m in messages
        )
        if SCENE_MARKER in user_msg:
            idx = self._scene_idx
            self.scene_prompts.append(full_prompt)
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


def test_voice01_character_names_reach_script_prompt():
    """VOICE-01: each provided character's NAME appears in the script-writing prompt."""
    mock = _MockChat(scene_contents=["SCENE ONE TEXT"])
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        _run(_make_config(1, characters=_CHARACTERS))

    assert len(mock.scene_prompts) == 1
    prompt = mock.scene_prompts[0]
    assert "MAYA" in prompt
    assert "VICTOR" in prompt
    # The character section header is present when characters exist.
    assert "## Characters" in prompt


def test_voice03_distinct_voice_instruction_present():
    """VOICE-03/VOICE-02: an explicit distinct/consistent-voice instruction is in
    the prompt (covers distinctness AND derive/carry-forward when no explicit cue)."""
    mock = _MockChat(scene_contents=["SCENE ONE TEXT"])
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        _run(_make_config(1, characters=_CHARACTERS))

    prompt = mock.scene_prompts[0].lower()
    # Distinctness instruction (VOICE-03).
    assert VOICE_INSTRUCTION_ANCHOR in prompt
    # Derive + carry-forward when no explicit cue (VOICE-02).
    assert "consistent with how they have already spoken in earlier scenes" in prompt


def test_voice03_instruction_on_every_scene_prompt():
    """The voice instruction is present in EVERY scene prompt, not only the first."""
    mock = _MockChat(scene_contents=["s1", "s2", "s3"])
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        _run(_make_config(3, characters=_CHARACTERS))

    assert len(mock.scene_prompts) == 3
    for prompt in mock.scene_prompts:
        assert "MAYA" in prompt and "VICTOR" in prompt
        assert VOICE_INSTRUCTION_ANCHOR in prompt.lower()


def test_no_regression_characters_absent_has_no_block():
    """D-47-04: with _characters absent, no character block / voice instruction."""
    mock = _MockChat(scene_contents=["SCENE ONE TEXT"])
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        _run(_make_config(1))  # no characters kwarg

    prompt = mock.scene_prompts[0]
    assert "## Characters" not in prompt
    assert "## Character Voice" not in prompt
    assert VOICE_INSTRUCTION_ANCHOR not in prompt.lower()


def test_no_regression_characters_empty_list_has_no_block():
    """D-47-04: an empty _characters list yields no block (byte-identical to Phase 46)."""
    mock = _MockChat(scene_contents=["SCENE ONE TEXT"])
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        _run(_make_config(1, characters=[]))

    prompt = mock.scene_prompts[0]
    assert "## Characters" not in prompt
    assert "## Character Voice" not in prompt
    assert VOICE_INSTRUCTION_ANCHOR not in prompt.lower()


def test_empty_characters_prompt_byte_identical_to_no_characters():
    """D-47-04: empty-list and absent _characters produce the identical prompt."""
    mock_absent = _MockChat(scene_contents=["SCENE ONE TEXT"])
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock_absent,
    ):
        _run(_make_config(1))

    mock_empty = _MockChat(scene_contents=["SCENE ONE TEXT"])
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock_empty,
    ):
        _run(_make_config(1, characters=[]))

    assert mock_absent.scene_prompts[0] == mock_empty.scene_prompts[0]


def test_d4701_script_writer_wizard_injects_characters():
    """D-47-01: the run_wizard injection guard fires _characters for
    script_writer_wizard exactly as for scene_wizard.

    Focused unit check of the guard logic itself (test_wizard_injection.py tests
    the agent-review middleware, not this guard). We patch _get_character_data to
    a sentinel and exercise the broadened condition for each wizard type.
    """
    sentinel = [{"item_type": "protagonist", "name": "MAYA"}]

    def _injects_for(wizard_type):
        with patch.object(
            wizards, "_get_character_data", return_value=sentinel
        ):
            config = dict({"episodes": []})
            # Mirror the broadened guard in run_wizard.
            if wizard_type in ("scene_wizard", "script_writer_wizard"):
                config["_characters"] = wizards._get_character_data(None, "pid")
            return config.get("_characters")

    assert _injects_for("script_writer_wizard") == sentinel
    assert _injects_for("scene_wizard") == sentinel
    # A non-character wizard must NOT get _characters injected.
    assert _injects_for("idea_wizard") is None


def test_d4701_guard_source_includes_script_writer_wizard():
    """D-47-01: the actual run_wizard source carries the broadened guard, proving
    the focused unit check above mirrors production (not a divergent copy)."""
    import inspect

    src = inspect.getsource(wizards.run_wizard)
    assert 'in ("scene_wizard", "script_writer_wizard")' in src
    assert 'config["_characters"] = _get_character_data(db, project.id)' in src
