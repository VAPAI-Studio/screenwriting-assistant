# backend/app/tests/test_continuity_generation.py

"""
Tests for continuity-aware screenplay generation (Phase 45, CONT-01/02/03).

_generate_scripts threads a running prose synopsis ("story so far") plus the
full verbatim text of the immediately preceding scene through its sequential
loop, injecting both into each later scene prompt while leaving the first /
single scene prompt continuity-free. After each SUCCESSFUL scene, one extra
chat_completion call regenerates the synopsis. A failed scene must not advance
continuity state.

Mocking pattern (from test_bible_injection.py):
  @patch("app.services.template_ai_service.chat_completion", new_callable=AsyncMock)
  template_ai_service is a module-level singleton.

Scene-writing calls use json_mode=True (return JSON {"title","content"});
synopsis-update calls use json_mode=False (return plain prose). The test
side_effect routes on the json_mode kwarg.
"""

import asyncio
import json

from unittest.mock import patch, AsyncMock

from app.services.template_ai_service import template_ai_service


# Markers the continuity block injects into a later scene prompt. Their ABSENCE
# proves no continuity block (first/single scene); their PRESENCE proves it.
SYNOPSIS_MARKER = "Story so far"
PREV_SCENE_MARKER = "Previous scene"


def _make_config(num_scenes):
    """Minimal config accepted by _generate_scripts: a list of scene dicts."""
    return {
        "episodes": [
            {"summary": f"Scene {i + 1} summary"} for i in range(num_scenes)
        ]
    }


def _scene_writer(content, title="A Scene"):
    """A JSON string as the scene-writing chat_completion would return it."""
    return json.dumps({"title": title, "content": content})


class _MockChat:
    """Side-effect callable that routes scene vs synopsis calls by json_mode.

    Records every call's prompt (the user message) and how many synopsis-update
    calls fired. Optionally raises on a chosen scene index.
    """

    def __init__(self, scene_contents, synopsis_text="SYNOPSIS_PROSE", fail_scene_index=None):
        self.scene_contents = scene_contents
        self.synopsis_text = synopsis_text
        self.fail_scene_index = fail_scene_index
        self.scene_prompts = []      # prompts of scene-writing (json_mode=True) calls
        self.synopsis_calls = 0      # count of synopsis-update (json_mode=False) calls
        self._scene_idx = 0

    def __call__(self, *args, **kwargs):
        # Synchronous side_effect: AsyncMock awaits the call itself and uses this
        # return value. An async side_effect would double-wrap into a coroutine.
        json_mode = kwargs.get("json_mode", False)
        messages = kwargs.get("messages", [])
        user_msg = next(
            (m["content"] for m in messages if m.get("role") == "user"), ""
        )
        if json_mode:
            # Scene-writing call
            idx = self._scene_idx
            self.scene_prompts.append(user_msg)
            self._scene_idx += 1
            if self.fail_scene_index is not None and idx == self.fail_scene_index:
                raise RuntimeError("boom")
            content = self.scene_contents[idx]
            return _scene_writer(content, title=f"Scene {idx + 1}")
        else:
            # Synopsis-update call
            self.synopsis_calls += 1
            return self.synopsis_text


def _run(config):
    return asyncio.run(
        template_ai_service._generate_scripts(config, "PROJECT CONTEXT", {})
    )


def test_first_scene_has_no_continuity_block():
    """D-05 / success criterion 4: first/single scene prompt has no continuity block."""
    mock = _MockChat(scene_contents=["SCENE ONE TEXT"])
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        _run(_make_config(1))

    assert len(mock.scene_prompts) == 1
    first_prompt = mock.scene_prompts[0]
    assert SYNOPSIS_MARKER not in first_prompt
    assert PREV_SCENE_MARKER not in first_prompt


def test_later_scene_includes_prior_scene_and_synopsis():
    """CONT-01/CONT-02: a later prompt carries the prior scene's full text + synopsis."""
    mock = _MockChat(
        scene_contents=["FIRST SCENE VERBATIM BODY", "second scene body"],
        synopsis_text="THE RUNNING SYNOPSIS PROSE",
    )
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        _run(_make_config(2))

    assert len(mock.scene_prompts) == 2
    second_prompt = mock.scene_prompts[1]
    # The full verbatim text of the immediately preceding scene (CONT-01)
    assert "FIRST SCENE VERBATIM BODY" in second_prompt
    # The running synopsis text (CONT-02)
    assert "THE RUNNING SYNOPSIS PROSE" in second_prompt
    # And both labeled continuity sections are present
    assert SYNOPSIS_MARKER in second_prompt
    assert PREV_SCENE_MARKER in second_prompt


def test_synopsis_update_called_after_each_success():
    """CONT-02: one synopsis-update per successful scene; return has top-level synopsis."""
    mock = _MockChat(
        scene_contents=["s1", "s2", "s3"],
        synopsis_text="FINAL_SYNOPSIS",
    )
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        result = _run(_make_config(3))

    assert mock.synopsis_calls == 3  # one per successful scene
    assert "synopsis" in result
    assert result["synopsis"] == "FINAL_SYNOPSIS"


def test_failed_scene_does_not_advance_continuity():
    """Failed-scene handling: error placeholder is not injected downstream and the
    failed scene triggers no synopsis-update."""
    # Scene index 1 (the middle scene) fails.
    mock = _MockChat(
        scene_contents=["scene one body", "UNUSED", "scene three body"],
        synopsis_text="SYN",
        fail_scene_index=1,
    )
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        result = _run(_make_config(3))

    assert len(mock.scene_prompts) == 3
    third_prompt = mock.scene_prompts[2]
    # The error placeholder from the failed scene must NOT poison the next prompt.
    assert "[Generation failed" not in third_prompt
    # Scene 3 still sees the last GOOD scene (scene 1), not the failed scene 2.
    assert "scene one body" in third_prompt
    # Only scenes 1 and 3 succeeded → exactly 2 synopsis-update calls.
    assert mock.synopsis_calls == 2
    # The failed scene still appears in output with the placeholder (degraded, not dropped).
    failed_item = result["screenplays"][1]
    assert "[Generation failed" in failed_item["content"]


def test_per_screenplay_contract_unchanged():
    """Return-contract guard: every screenplay item keeps title/content/episode_index."""
    mock = _MockChat(scene_contents=["a", "b"])
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        result = _run(_make_config(2))

    assert "screenplays" in result
    assert len(result["screenplays"]) == 2
    for i, item in enumerate(result["screenplays"]):
        assert "title" in item
        assert "content" in item
        assert "episode_index" in item
        assert item["episode_index"] == i
