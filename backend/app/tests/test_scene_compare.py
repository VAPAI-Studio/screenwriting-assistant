# backend/app/tests/test_scene_compare.py

"""
Phase 49 — Side-by-side quality compare (EVAL-01) backend tests.

Two layers:
  1. Service layer: template_ai_service.regenerate_single_scene reuses the SAME
     improved per-scene prompt as _generate_scripts (continuity + voice + craft +
     native TITLE), generating ONE scene by episode_index from supplied
     synopsis/prev_scene_text WITHOUT advancing global continuity (D-49-05).
  2. Endpoint layer: POST /api/wizards/regenerate-scene returns the new scene as a
     PREVIEW and writes nothing (D-49-02); POST /api/wizards/keep-scene-version
     persists screenplays[episode_index] into the screenplay_editor PhaseData +
     the matching ScreenplayContent row and marks breakdown/shotlist stale, while
     leaving the global synopsis untouched (D-49-05). Both endpoints are
     owner-scoped (404 for a non-owner), mirroring run_wizard.

Tests must pass in ISOLATION (no reliance on suite ordering — see
.planning/v6.0-PREEXISTING-TEST-CONCERN.md).

Service mocking reuses the test_continuity_generation pattern: patch
app.services.template_ai_service.chat_completion (AsyncMock, side_effect=mock),
routing scene calls by the SCENE_MARKER "YOUR TASK: Write scene".
"""

import asyncio
import uuid

from unittest.mock import patch, AsyncMock

import pytest

from app.models import database
from app.services.template_ai_service import template_ai_service


# ---------------------------------------------------------------------------
# Service-layer fixtures / helpers (mirrors test_continuity_generation.py)
# ---------------------------------------------------------------------------

SYNOPSIS_MARKER = "Story so far"
PREV_SCENE_MARKER = "Previous scene"
VOICE_MARKER = "distinct, consistent voice"
CRAFT_MARKER = "## Screenwriting Craft"
CRAFT_SUBMARKER = "on-the-nose"
TITLE_MARKER = "TITLE:"
SCENE_MARKER = "YOUR TASK: Write scene"


def _scene_writer(content, title="A Scene"):
    return f"TITLE: {title}\n\n{content}"


class _MockChat:
    """Records each scene call's prompt + json_mode; routes by SCENE_MARKER."""

    def __init__(self, scene_text="REGENERATED SCENE BODY", title="Regen Title"):
        self.scene_text = scene_text
        self.title = title
        self.scene_prompts = []
        self.scene_json_modes = []

    def __call__(self, *args, **kwargs):
        messages = kwargs.get("messages", [])
        user_msg = next(
            (m["content"] for m in messages if m.get("role") == "user"), ""
        )
        if SCENE_MARKER in user_msg:
            self.scene_prompts.append(user_msg)
            self.scene_json_modes.append(kwargs.get("json_mode", False))
            return _scene_writer(self.scene_text, title=self.title)
        # synopsis-update branch (should NOT be hit by regenerate_single_scene)
        return "SYNOPSIS_PROSE"


def _character():
    return {"item_type": "character", "name": "Alex", "description": "A weary detective"}


def _regen_config():
    return {
        "episodes": [
            {"summary": "Scene 1 — the inciting incident"},
            {"summary": "Scene 2 — the confrontation"},
        ],
        "_characters": [_character()],
    }


def _run_regen(config, episode_index, synopsis, prev_scene_text):
    return asyncio.run(
        template_ai_service.regenerate_single_scene(
            config, "PROJECT CONTEXT", episode_index, synopsis, prev_scene_text
        )
    )


def test_regenerate_returns_single_parsed_dict():
    """regenerate_single_scene returns ONE {title,content,episode_index} dict with the
    requested index and a title+content parsed from native TITLE output."""
    mock = _MockChat(scene_text="THE BODY", title="My Scene")
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        result = _run_regen(_regen_config(), 1, "PRIOR SYNOPSIS", "PRIOR SCENE")

    assert result["episode_index"] == 1
    assert result["title"] == "My Scene"
    assert result["content"] == "THE BODY"
    assert "error" not in result
    # Exactly one scene call; no synopsis advance (single call total).
    assert len(mock.scene_prompts) == 1


def test_regenerate_non_first_scene_has_all_improved_anchors():
    """A non-first regenerate (index 1, synopsis + prev_scene + characters) carries
    every improved-path anchor: continuity, voice, craft, native TITLE."""
    mock = _MockChat()
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        _run_regen(_regen_config(), 1, "PRIOR SYNOPSIS", "PRIOR SCENE")

    prompt = mock.scene_prompts[0]
    assert SYNOPSIS_MARKER in prompt
    assert PREV_SCENE_MARKER in prompt
    assert "PRIOR SYNOPSIS" in prompt
    assert "PRIOR SCENE" in prompt
    # Voice anchor is upper-cased in the prompt ("DISTINCT, CONSISTENT voice");
    # compare lowercase like the existing voice suite does.
    assert VOICE_MARKER in prompt.lower()
    assert CRAFT_MARKER in prompt
    assert CRAFT_SUBMARKER in prompt
    assert TITLE_MARKER in prompt
    # The "YOUR TASK: Write scene 2 of 2" marker uses the requested index+1.
    assert "Write scene 2 of 2" in prompt


def test_regenerate_first_scene_has_no_continuity_block():
    """A first-scene regenerate (index 0, empty synopsis + empty prev_scene) omits
    the continuity block — matching _generate_scripts' first-scene behavior."""
    mock = _MockChat()
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        _run_regen(_regen_config(), 0, "", "")

    prompt = mock.scene_prompts[0]
    assert SYNOPSIS_MARKER not in prompt
    assert PREV_SCENE_MARKER not in prompt
    # Craft is unconditional even for the first scene.
    assert CRAFT_MARKER in prompt


def test_regenerate_scene_call_uses_json_mode_false():
    """The scene-writing call runs with json_mode=False (native plain text)."""
    mock = _MockChat()
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        _run_regen(_regen_config(), 1, "PRIOR SYNOPSIS", "PRIOR SCENE")

    assert mock.scene_json_modes == [False]


def test_regenerate_out_of_range_raises():
    """An episode_index outside the episodes list raises ValueError."""
    mock = _MockChat()
    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ):
        with pytest.raises(ValueError):
            _run_regen(_regen_config(), 5, "", "")


def test_regenerate_failure_branch_shape():
    """When chat_completion raises, regenerate returns the failure-branch dict shape
    ({episode_index, title=summary, content '[Generation failed: ...]', error})."""

    def _boom(*args, **kwargs):
        raise RuntimeError("kaboom")

    with patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=_boom,
    ):
        result = _run_regen(_regen_config(), 1, "PRIOR SYNOPSIS", "PRIOR SCENE")

    assert result["episode_index"] == 1
    assert result["title"] == "Scene 2 — the confrontation"
    assert result["content"].startswith("[Generation failed:")
    assert "error" in result


# ---------------------------------------------------------------------------
# Endpoint-layer fixtures / helpers (mirrors test_shotlist_staleness.py)
# ---------------------------------------------------------------------------

MOCK_USER_ID = "12345678-1234-5678-1234-567812345678"
OTHER_USER_ID = "99999999-9999-9999-9999-999999999999"


def _create_owner_project(client, db_session, mock_auth_headers, title="Scene Compare Project"):
    """Create a project through the API so owner_id matches the mock user under
    SQLite (mirrors test_shotlist_staleness._create_project_via_api). Returns a
    lightweight object exposing `.id`."""
    resp = client.post(
        "/api/projects/",
        json={"title": title, "framework": "three_act"},
        headers=mock_auth_headers,
    )
    assert resp.status_code == 200, f"Project creation failed: {resp.json()}"
    project_id = resp.json()["id"]

    # The v1 create endpoint leaves `template` unset; the regenerate path needs a
    # template to build project context. Set the only available template.
    proj = db_session.query(database.Project).filter(
        database.Project.id == project_id
    ).first()
    proj.template = "short_movie"
    db_session.commit()

    class _P:
        pass
    p = _P()
    p.id = project_id
    return p


def _create_other_user_project(db_session, title="Other User Project"):
    """Create a project owned by a DIFFERENT user (direct ORM) for 404 tests."""
    project = database.Project(
        id=str(uuid.uuid4()),
        title=title,
        framework="three_act",
        owner_id=OTHER_USER_ID,
    )
    db_session.add(project)
    db_session.commit()
    return project


def _seed_screenplay_editor(db_session, project_id):
    """Seed a 2-scene screenplay_editor PhaseData + synopsis + matching
    ScreenplayContent rows, plus a scene_list with 2 ListItems and a character."""
    screenplays = [
        {"title": "Old Scene 1", "content": "OLD BODY 1", "episode_index": 0},
        {"title": "Old Scene 2", "content": "OLD BODY 2", "episode_index": 1},
    ]
    pd = database.PhaseData(
        id=str(uuid.uuid4()),
        project_id=project_id,
        phase="write",
        subsection_key="screenplay_editor",
        content={"screenplays": screenplays, "synopsis": "ORIGINAL SYNOPSIS"},
    )
    db_session.add(pd)

    for sp in screenplays:
        db_session.add(database.ScreenplayContent(
            id=str(uuid.uuid4()),
            project_id=project_id,
            content=sp["content"],
            formatted_content=sp,
        ))

    # scene_list ListItems (input to regenerate config.episodes)
    scene_pd = database.PhaseData(
        id=str(uuid.uuid4()),
        project_id=project_id,
        phase="scenes",
        subsection_key="scene_list",
        content={},
    )
    db_session.add(scene_pd)
    db_session.flush()
    for i, summ in enumerate(["Scene 1 input", "Scene 2 input"]):
        db_session.add(database.ListItem(
            id=str(uuid.uuid4()),
            phase_data_id=scene_pd.id,
            item_type="scene",
            sort_order=i,
            content={"summary": summ},
        ))

    # character ListItem (story/characters)
    char_pd = database.PhaseData(
        id=str(uuid.uuid4()),
        project_id=project_id,
        phase="story",
        subsection_key="characters",
        content={},
    )
    db_session.add(char_pd)
    db_session.flush()
    db_session.add(database.ListItem(
        id=str(uuid.uuid4()),
        phase_data_id=char_pd.id,
        item_type="character",
        sort_order=0,
        content={"name": "Alex", "description": "A weary detective"},
    ))
    db_session.commit()
    return pd


def _seed_breakdown_and_shot(db_session, project_id):
    db_session.add(database.BreakdownElement(
        id=str(uuid.uuid4()),
        project_id=project_id,
        category="prop",
        name="Briefcase",
        description="",
    ))
    db_session.add(database.Shot(
        id=str(uuid.uuid4()),
        project_id=project_id,
        shot_number=1,
        fields={},
        sort_order=0,
        source="user",
    ))
    db_session.commit()


def _patch_scene_chat():
    """Patch chat_completion so a regenerate scene call returns deterministic native text."""
    mock = _MockChat(scene_text="NEW REGEN BODY", title="New Title")
    return patch(
        "app.services.template_ai_service.chat_completion",
        new_callable=AsyncMock,
        side_effect=mock,
    ), mock


def test_regenerate_endpoint_returns_preview_and_does_not_persist(
    client, db_session, mock_auth_headers
):
    """regenerate-scene returns {title,content,episode_index} and writes nothing:
    no new ScreenplayContent, stored screenplays[] unchanged, no stale flags."""
    project = _create_owner_project(client, db_session, mock_auth_headers)
    _seed_screenplay_editor(db_session, project.id)
    _seed_breakdown_and_shot(db_session, project.id)

    before_sc = db_session.query(database.ScreenplayContent).filter(
        database.ScreenplayContent.project_id == project.id
    ).count()

    ctx, _mock = _patch_scene_chat()
    with ctx:
        resp = client.post(
            "/api/wizards/regenerate-scene",
            json={"project_id": str(project.id), "phase": "write", "episode_index": 1},
            headers=mock_auth_headers,
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["episode_index"] == 1
    assert body["title"] == "New Title"
    assert body["content"] == "NEW REGEN BODY"

    db_session.expire_all()
    after_sc = db_session.query(database.ScreenplayContent).filter(
        database.ScreenplayContent.project_id == project.id
    ).count()
    assert after_sc == before_sc  # no new ScreenplayContent

    pd = db_session.query(database.PhaseData).filter(
        database.PhaseData.project_id == project.id,
        database.PhaseData.subsection_key == "screenplay_editor",
    ).first()
    assert pd.content["screenplays"][1]["content"] == "OLD BODY 2"  # unchanged

    proj = db_session.query(database.Project).filter(
        database.Project.id == project.id
    ).first()
    assert not proj.breakdown_stale
    assert not proj.shotlist_stale


def test_keep_scene_version_persists_and_marks_stale(
    client, db_session, mock_auth_headers
):
    """keep-scene-version replaces screenplays[1] + the matching ScreenplayContent,
    flips breakdown/shotlist stale, and leaves the global synopsis untouched."""
    project = _create_owner_project(client, db_session, mock_auth_headers)
    _seed_screenplay_editor(db_session, project.id)
    _seed_breakdown_and_shot(db_session, project.id)

    resp = client.post(
        "/api/wizards/keep-scene-version",
        json={
            "project_id": str(project.id),
            "phase": "write",
            "episode_index": 1,
            "title": "Kept Title",
            "content": "KEPT BODY",
        },
        headers=mock_auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["episode_index"] == 1

    db_session.expire_all()
    pd = db_session.query(database.PhaseData).filter(
        database.PhaseData.project_id == project.id,
        database.PhaseData.subsection_key == "screenplay_editor",
    ).first()
    assert pd.content["screenplays"][1]["title"] == "Kept Title"
    assert pd.content["screenplays"][1]["content"] == "KEPT BODY"
    assert pd.content["screenplays"][1]["episode_index"] == 1
    # Other slot + synopsis untouched (D-49-05).
    assert pd.content["screenplays"][0]["content"] == "OLD BODY 1"
    assert pd.content["synopsis"] == "ORIGINAL SYNOPSIS"

    # Matching ScreenplayContent row (by formatted_content.episode_index) updated.
    rows = db_session.query(database.ScreenplayContent).filter(
        database.ScreenplayContent.project_id == project.id
    ).all()
    matched = [r for r in rows if (r.formatted_content or {}).get("episode_index") == 1]
    assert len(matched) == 1
    assert matched[0].content == "KEPT BODY"
    assert matched[0].formatted_content["title"] == "Kept Title"

    proj = db_session.query(database.Project).filter(
        database.Project.id == project.id
    ).first()
    assert proj.breakdown_stale is True
    assert proj.shotlist_stale is True


def test_keep_scene_version_updates_newest_duplicate_row(
    client, db_session, mock_auth_headers
):
    """WR-01 regression: the batch-generate path appends ScreenplayContent rows and
    never deletes them, so a re-generated project holds duplicate rows per
    episode_index. keep-scene-version must update the NEWEST matching row (the one
    the breakdown/shotlist services read), not a stale earlier duplicate."""
    project = _create_owner_project(client, db_session, mock_auth_headers)
    _seed_screenplay_editor(db_session, project.id)

    # Simulate a later re-generation: append a NEWER duplicate row for episode 1.
    # Set explicit created_at values so the "newest-first" ordering is exercised
    # deterministically (SQLite func.now() is only second-resolution, so we cannot
    # rely on wall-clock spacing to distinguish near-simultaneous rows).
    from datetime import datetime, timedelta, timezone
    base = datetime.now(timezone.utc)
    # Backdate the seeded episode-1 row and forward-date the new one.
    seeded_ep1 = next(
        r for r in db_session.query(database.ScreenplayContent).filter(
            database.ScreenplayContent.project_id == project.id
        ).all()
        if (r.formatted_content or {}).get("episode_index") == 1
    )
    seeded_ep1.created_at = base - timedelta(minutes=5)
    newer = database.ScreenplayContent(
        id=str(uuid.uuid4()),
        project_id=project.id,
        content="NEWER BODY 2",
        formatted_content={"title": "Newer Scene 2", "content": "NEWER BODY 2", "episode_index": 1},
        created_at=base,
    )
    db_session.add(newer)
    db_session.commit()
    newer_id = newer.id

    resp = client.post(
        "/api/wizards/keep-scene-version",
        json={
            "project_id": str(project.id),
            "phase": "write",
            "episode_index": 1,
            "title": "Kept Title",
            "content": "KEPT BODY",
        },
        headers=mock_auth_headers,
    )
    assert resp.status_code == 200, resp.text

    db_session.expire_all()
    ep1_rows = [
        r for r in db_session.query(database.ScreenplayContent).filter(
            database.ScreenplayContent.project_id == project.id
        ).all()
        if (r.formatted_content or {}).get("episode_index") == 1
    ]
    # The NEWEST row was updated; the older duplicate was left untouched.
    by_id = {r.id: r for r in ep1_rows}
    assert by_id[newer_id].content == "KEPT BODY"
    older = [r for r in ep1_rows if r.id != newer_id]
    assert len(older) == 1
    assert older[0].content == "OLD BODY 2"


def test_regenerate_endpoint_non_owner_404(client, db_session, mock_auth_headers):
    """A project owned by a different user returns 404 on regenerate-scene."""
    project = _create_other_user_project(db_session)
    _seed_screenplay_editor(db_session, project.id)

    ctx, _mock = _patch_scene_chat()
    with ctx:
        resp = client.post(
            "/api/wizards/regenerate-scene",
            json={"project_id": str(project.id), "phase": "write", "episode_index": 1},
            headers=mock_auth_headers,
        )
    assert resp.status_code == 404


def test_keep_scene_version_non_owner_404(client, db_session, mock_auth_headers):
    """A project owned by a different user returns 404 on keep-scene-version."""
    project = _create_other_user_project(db_session)
    _seed_screenplay_editor(db_session, project.id)

    resp = client.post(
        "/api/wizards/keep-scene-version",
        json={
            "project_id": str(project.id),
            "phase": "write",
            "episode_index": 1,
            "title": "X",
            "content": "Y",
        },
        headers=mock_auth_headers,
    )
    assert resp.status_code == 404
