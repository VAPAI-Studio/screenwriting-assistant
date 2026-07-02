# backend/app/tests/test_screenplay_critique.py

"""
Tests for the Phase 3 screenplay quality loop in template_ai_service:
  - _critique_scene: scores a scene against the 5-axis rubric (parses JSON,
    validates axis ints, returns None on malformed output).
  - _weak_axes: selects axes below the threshold, worst first.
  - _rewrite_scene: rewrites a scene body from critique notes (parses native).
  - _polish_screenplay: whole-script pass; replaces only revised scenes by index.
  - _generate_scripts orchestration: critique+rewrite fires when an axis is weak,
    is skipped when all axes are strong, and is fully bypassed when the flag is off.

The scene-writing call is routed by the SCENE_MARKER in the user prompt (same
convention as the other scene suites). Critique/polish calls use json_mode=True
and carry no SCENE_MARKER, so the mock routes them by their own markers.
"""

import asyncio

import pytest
from unittest.mock import patch, AsyncMock

from app.config import settings
from app.services.template_ai_service import template_ai_service


SCENE_MARKER = "YOUR TASK: Write scene"
CRITIQUE_MARKER = "scoring a single screenplay scene against a fixed rubric"
REWRITE_MARKER = "revising one scene of a screenplay"
POLISH_MARKER = "final polish pass over a COMPLETE screenplay"

STRONG = '{"subtext": 5, "scene_turn": 5, "escalation": 5, "voice_distinction": 5, "tone_identity": 5, "notes": {}}'
WEAK_SUBTEXT = '{"subtext": 2, "scene_turn": 5, "escalation": 5, "voice_distinction": 5, "tone_identity": 4, "notes": {"subtext": "too on-the-nose"}}'


def _scene_writer(content, title="A Scene"):
    return f"TITLE: {title}\n\n{content}"


def _make_config(num_scenes):
    return {"episodes": [{"summary": f"Scene {i + 1} summary"} for i in range(num_scenes)]}


def _run(config):
    return asyncio.run(
        template_ai_service._generate_scripts(config, "PROJECT CONTEXT", {})
    )


class _LoopMock:
    """Routes the four call kinds by marker and records per-kind call counts.

    scene_returns / critique_returns / rewrite_returns are lists consumed in
    order per kind; polish_return is a single JSON string.
    """

    def __init__(self, scene_returns, critique_returns=None, rewrite_returns=None,
                 polish_return='{"revisions": []}', synopsis_text="SYN"):
        self.scene_returns = scene_returns
        self.critique_returns = critique_returns or []
        self.rewrite_returns = rewrite_returns or []
        self.polish_return = polish_return
        self.synopsis_text = synopsis_text
        self.counts = {"scene": 0, "critique": 0, "rewrite": 0, "polish": 0, "synopsis": 0}

    def __call__(self, *args, **kwargs):
        messages = kwargs.get("messages", [])
        blob = "\n".join(
            (m["content"] if isinstance(m["content"], str) else str(m["content"]))
            for m in messages
        )
        user_msg = next((m["content"] for m in messages if m.get("role") == "user"), "")
        if CRITIQUE_MARKER in blob:
            i = self.counts["critique"]
            self.counts["critique"] += 1
            return self.critique_returns[i] if i < len(self.critique_returns) else STRONG
        if REWRITE_MARKER in blob:
            i = self.counts["rewrite"]
            self.counts["rewrite"] += 1
            body = self.rewrite_returns[i] if i < len(self.rewrite_returns) else "REWRITTEN BODY"
            return _scene_writer(body, title="Rewritten")
        if POLISH_MARKER in blob:
            self.counts["polish"] += 1
            return self.polish_return
        if SCENE_MARKER in user_msg:
            i = self.counts["scene"]
            self.counts["scene"] += 1
            body = self.scene_returns[i] if i < len(self.scene_returns) else "SCENE BODY"
            return _scene_writer(body, title=f"Scene {i + 1}")
        # else: synopsis-update
        self.counts["synopsis"] += 1
        return self.synopsis_text


@pytest.fixture(autouse=True)
def _enable_loop(monkeypatch):
    """Ensure the loop is ON with a known threshold for these tests."""
    monkeypatch.setattr(settings, "SCREENPLAY_CRITIQUE_ENABLED", True)
    monkeypatch.setattr(settings, "SCREENPLAY_CRITIQUE_THRESHOLD", 4)
    monkeypatch.setattr(settings, "SCREENPLAY_POLISH_ENABLED", True)


# ---- _critique_scene ----

def test_critique_parses_valid_rubric():
    mock = _LoopMock(scene_returns=[], critique_returns=[WEAK_SUBTEXT])
    with patch("app.services.template_ai_service.chat_completion",
               new_callable=AsyncMock, side_effect=mock):
        result = asyncio.run(
            template_ai_service._critique_scene("SCENE TEXT", {"summary": "s"}, "", "CTX")
        )
    assert result["subtext"] == 2
    assert result["scene_turn"] == 5
    assert result["notes"]["subtext"] == "too on-the-nose"


def test_critique_returns_none_on_malformed():
    bad = '{"subtext": "not-an-int", "scene_turn": 5}'
    mock = _LoopMock(scene_returns=[], critique_returns=[bad])
    with patch("app.services.template_ai_service.chat_completion",
               new_callable=AsyncMock, side_effect=mock):
        result = asyncio.run(
            template_ai_service._critique_scene("SCENE TEXT", {"summary": "s"}, "", "CTX")
        )
    assert result is None


# ---- _weak_axes ----

def test_weak_axes_selects_below_threshold_worst_first():
    critique = {"subtext": 2, "scene_turn": 4, "escalation": 1, "voice_distinction": 5, "tone_identity": 3}
    weak = template_ai_service._weak_axes(critique, threshold=4)
    # escalation (1) worst, then subtext (2), then tone_identity (3); 4 and 5 excluded.
    assert weak == ["escalation", "subtext", "tone_identity"]


def test_weak_axes_empty_when_all_strong():
    critique = {"subtext": 4, "scene_turn": 5, "escalation": 4, "voice_distinction": 5, "tone_identity": 4}
    assert template_ai_service._weak_axes(critique, threshold=4) == []


# ---- orchestration in _generate_scripts ----

def test_rewrite_fires_when_axis_weak():
    """A weak axis triggers exactly one rewrite; the scene body is the rewrite."""
    mock = _LoopMock(
        scene_returns=["ORIGINAL BODY"],
        critique_returns=[WEAK_SUBTEXT],
        rewrite_returns=["IMPROVED BODY"],
    )
    with patch("app.services.template_ai_service.chat_completion",
               new_callable=AsyncMock, side_effect=mock):
        result = _run(_make_config(1))

    assert mock.counts["critique"] == 1
    assert mock.counts["rewrite"] == 1
    scene = result["screenplays"][0]
    assert scene["content"] == "IMPROVED BODY"
    assert scene.get("rewritten") is True
    # Rubric scores surfaced for _meta.
    assert result["rubric_scores"][0]["rewrote_axes"] == ["subtext"]


def test_no_rewrite_when_all_axes_strong():
    """All-strong critique → no rewrite call; original body kept."""
    mock = _LoopMock(scene_returns=["ORIGINAL BODY"], critique_returns=[STRONG])
    with patch("app.services.template_ai_service.chat_completion",
               new_callable=AsyncMock, side_effect=mock):
        result = _run(_make_config(1))

    assert mock.counts["critique"] == 1
    assert mock.counts["rewrite"] == 0
    scene = result["screenplays"][0]
    assert scene["content"] == "ORIGINAL BODY"
    assert "rewritten" not in scene


def test_flag_off_bypasses_loop_entirely():
    """With the critique flag off, no critique/rewrite/polish calls happen and
    the result carries no rubric_scores (single-pass behavior)."""
    mock = _LoopMock(scene_returns=["ORIGINAL BODY"], critique_returns=[WEAK_SUBTEXT])
    with patch.object(settings, "SCREENPLAY_CRITIQUE_ENABLED", False), \
         patch.object(settings, "SCREENPLAY_POLISH_ENABLED", False), \
         patch("app.services.template_ai_service.chat_completion",
               new_callable=AsyncMock, side_effect=mock):
        result = _run(_make_config(1))

    assert mock.counts["critique"] == 0
    assert mock.counts["rewrite"] == 0
    assert mock.counts["polish"] == 0
    assert "rubric_scores" not in result
    assert result["screenplays"][0]["content"] == "ORIGINAL BODY"


# ---- _polish_screenplay ----

def test_polish_replaces_only_revised_scene_by_index():
    """The polish pass replaces only the scene(s) it returns, keyed by index."""
    mock = _LoopMock(
        scene_returns=["BODY ONE", "BODY TWO"],
        critique_returns=[STRONG, STRONG],
        polish_return='{"revisions": [{"episode_index": 1, "content": "POLISHED TWO"}]}',
    )
    with patch("app.services.template_ai_service.chat_completion",
               new_callable=AsyncMock, side_effect=mock):
        result = _run(_make_config(2))

    assert mock.counts["polish"] == 1
    sp = result["screenplays"]
    assert sp[0]["content"] == "BODY ONE"          # untouched
    assert sp[1]["content"] == "POLISHED TWO"       # replaced by index
    assert sp[1].get("polished") is True


def test_polish_skipped_for_single_scene():
    """Fewer than 2 good scenes → nothing cross-scene to polish; no polish call."""
    mock = _LoopMock(scene_returns=["ONLY BODY"], critique_returns=[STRONG])
    with patch("app.services.template_ai_service.chat_completion",
               new_callable=AsyncMock, side_effect=mock):
        result = _run(_make_config(1))

    assert mock.counts["polish"] == 0
    assert result["screenplays"][0]["content"] == "ONLY BODY"
