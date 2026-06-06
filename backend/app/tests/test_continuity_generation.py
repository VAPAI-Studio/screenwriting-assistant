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

As of Phase 46 (FMT-01/FMT-02, D-46-01), the scene-writing call uses
json_mode=False and returns a NATIVE plain-text screenplay whose first line is
`TITLE: <title>` followed by the screenplay body (real newlines, no JSON). The
synopsis-update call also uses json_mode=False. Because json_mode no longer
distinguishes the two calls, the side_effect routes by the POSITIVE scene
marker in the user prompt: a message containing "YOUR TASK: Write scene" is a
scene call; every other call is treated as the synopsis-update (else-branch).
We deliberately do NOT route on "story so far"/"running synopsis" — those also
appear inside later scene prompts' continuity block, so they are ambiguous.
"""

import asyncio

from unittest.mock import patch, AsyncMock

from app.services.template_ai_service import template_ai_service


# Markers the continuity block injects into a later scene prompt. Their ABSENCE
# proves no continuity block (first/single scene); their PRESENCE proves it.
SYNOPSIS_MARKER = "Story so far"
PREV_SCENE_MARKER = "Previous scene"

# Positive, unambiguous discriminator for a scene-writing call (template_ai_service:352).
SCENE_MARKER = "YOUR TASK: Write scene"


def _make_config(num_scenes):
    """Minimal config accepted by _generate_scripts: a list of scene dicts."""
    return {
        "episodes": [
            {"summary": f"Scene {i + 1} summary"} for i in range(num_scenes)
        ]
    }


def _scene_writer(content, title="A Scene"):
    """A NATIVE plain-text screenplay string as the scene-writing call now returns
    it (Phase 46): a leading `TITLE: <title>` line, a blank line, then the body
    with REAL newlines — not a json.dumps blob."""
    return f"TITLE: {title}\n\n{content}"


class _MockChat:
    """Side-effect callable that routes scene vs synopsis calls by prompt content.

    Both calls are now json_mode=False, so routing is by the positive scene
    marker "YOUR TASK: Write scene" in the user message (every other call is the
    synopsis-update else-branch). Records each scene call's prompt and json_mode
    so tests can assert the scene call ran with json_mode=False. Optionally raises
    on a chosen scene index.
    """

    def __init__(self, scene_contents, synopsis_text="SYNOPSIS_PROSE", fail_scene_index=None):
        self.scene_contents = scene_contents
        self.synopsis_text = synopsis_text
        self.fail_scene_index = fail_scene_index
        self.scene_prompts = []      # prompts of scene-writing calls (routed by SCENE_MARKER)
        self.scene_json_modes = []   # json_mode kwarg recorded per scene call (must be False)
        self.synopsis_calls = 0      # count of synopsis-update (else-branch) calls
        self._scene_idx = 0

    def __call__(self, *args, **kwargs):
        # Synchronous side_effect: AsyncMock awaits the call itself and uses this
        # return value. An async side_effect would double-wrap into a coroutine.
        messages = kwargs.get("messages", [])
        user_msg = next(
            (m["content"] for m in messages if m.get("role") == "user"), ""
        )
        if SCENE_MARKER in user_msg:
            # Scene-writing call (native output, json_mode=False).
            idx = self._scene_idx
            self.scene_prompts.append(user_msg)
            self.scene_json_modes.append(kwargs.get("json_mode", False))
            self._scene_idx += 1
            if self.fail_scene_index is not None and idx == self.fail_scene_index:
                raise RuntimeError("boom")
            content = self.scene_contents[idx]
            return _scene_writer(content, title=f"Scene {idx + 1}")
        else:
            # Synopsis-update call (else-branch).
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


# ---------------------------------------------------------------------------
# Phase 46 FMT assertions — native output (json_mode=False), no JSON encoding,
# TITLE-line parse with summary fallback (FMT-01, FMT-02, D-46-01).
# ---------------------------------------------------------------------------


def test_scene_call_uses_native_json_mode_false():
    """FMT-02 / D-46-01: the scene-writing call runs with json_mode=False."""
    mock = _MockChat(scene_contents=["SCENE BODY"])
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        _run(_make_config(1))

    assert mock.scene_json_modes == [False], (
        "scene call must run with json_mode=False (native channel)"
    )


def test_native_content_has_real_newlines_no_json_encoding():
    """FMT-01: a multi-line native body lands in content with real newlines and
    no JSON string-encoding (no literal \\n escape, no surrounding JSON braces)."""
    body = "INT. ROOM - DAY\n\nA man enters.\n\nMAN\nHello."
    mock = _MockChat(scene_contents=[body])
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        result = _run(_make_config(1))

    content = result["screenplays"][0]["content"]
    # Real newline present (native multi-line text).
    assert "\n" in content
    # NOT JSON-escaped: the literal two-character backslash-n must be absent.
    assert "\\n" not in content
    # No JSON wrapping: content is not a JSON object/string blob.
    assert not content.lstrip().startswith("{")
    assert '"content":' not in content
    # The body survives verbatim.
    assert content == body


def test_title_parsed_from_title_line():
    """D-46-01: `TITLE: X` first line is parsed off as the title; body is the rest."""
    mock = _MockChat(scene_contents=["the body"])
    # _scene_writer emits `TITLE: Scene 1\n\nthe body` for the first scene.
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        result = _run(_make_config(1))

    item = result["screenplays"][0]
    assert item["title"] == "Scene 1"
    assert item["content"] == "the body"


def test_title_falls_back_to_summary_when_absent():
    """D-46-01: native output lacking any TITLE line never fails — title falls
    back to the scene summary, whole text becomes content."""

    class _NoTitleMock(_MockChat):
        def __call__(self, *args, **kwargs):
            messages = kwargs.get("messages", [])
            user_msg = next(
                (m["content"] for m in messages if m.get("role") == "user"), ""
            )
            if SCENE_MARKER in user_msg:
                self.scene_prompts.append(user_msg)
                self.scene_json_modes.append(kwargs.get("json_mode", False))
                self._scene_idx += 1
                # Native body with NO TITLE: line.
                return "INT. ROOM - DAY\n\nNo title line here."
            self.synopsis_calls += 1
            return self.synopsis_text

    mock = _NoTitleMock(scene_contents=["unused"])
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        result = _run(_make_config(1))

    item = result["screenplays"][0]
    # Summary fallback: _make_config gives scene 1 the summary "Scene 1 summary".
    assert item["title"] == "Scene 1 summary"
    # The whole native text (no TITLE line stripped) is the content.
    assert item["content"] == "INT. ROOM - DAY\n\nNo title line here."
