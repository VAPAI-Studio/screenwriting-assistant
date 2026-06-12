"""Tests for screenwriting MCP tools (Phase 58): screenplay_read + screenplay_write
(MCPW-01/02) and the heading splitter, owner-scoped.

screenplay_generate_scene (MCPW-03) is the long-running tool tested in
test_mcp_jobs.py.
"""

import hashlib
import uuid

import pytest
from types import SimpleNamespace
from sqlalchemy.orm import sessionmaker

from app.mcp_server.server import mcp
from app.mcp_server.session import mcp_session, set_session_factory_override
from app.mcp_server.tools.screenwriting import _split_by_headings
from app.models.database import (
    ApiKey as ApiKeyModel, User as UserModel, Project as ProjectModel,
    ScreenplayContent, TemplateType,
)


@pytest.fixture(autouse=True)
def _mcp_uses_test_db(test_engine):
    factory = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    set_session_factory_override(factory)
    yield
    set_session_factory_override(None)


def _ctx(token):
    request = SimpleNamespace(headers={"authorization": f"Bearer {token}"})
    return SimpleNamespace(request_context=SimpleNamespace(request=request))


def _fn(name):
    return mcp._tool_manager.get_tool(name).fn


def _seed_user_project():
    with mcp_session() as db:
        uid = str(uuid.uuid4())
        db.add(UserModel(id=uid, email=f"sw_{uid[:8]}@x.com", hashed_password="h", display_name="SW"))
        db.flush()
        token = f"sa_sw_{uuid.uuid4().hex}"
        db.add(ApiKeyModel(user_id=uid, name="k", key_prefix=token[:8],
                           key_hash=hashlib.sha256(token.encode()).hexdigest()))
        pid = str(uuid.uuid4())
        db.add(ProjectModel(id=pid, owner_id=uid, title="SW Project",
                            template=TemplateType.SHORT_MOVIE, template_config={}))
        db.commit()
        return uid, token, pid


# ---- splitter (pure) ----

def test_split_two_scenes_by_headings():
    text = "INT. KITCHEN - DAY\nMaya cooks.\n\nEXT. STREET - NIGHT\nJake walks."
    scenes = _split_by_headings(text)
    assert len(scenes) == 2
    assert scenes[0]["title"].startswith("INT. KITCHEN")
    assert "Maya cooks." in scenes[0]["content"]
    assert scenes[1]["episode_index"] == 1


def test_split_no_heading_is_one_untitled_scene():
    scenes = _split_by_headings("just some prose with no slugline")
    assert len(scenes) == 1
    assert scenes[0]["title"] == "Untitled"
    assert "just some prose" in scenes[0]["content"]


def test_split_empty_is_no_scenes():
    assert _split_by_headings("") == []
    assert _split_by_headings("   \n  ") == []


# ---- write/read tools ----

@pytest.mark.anyio
async def test_write_then_read_roundtrip_and_staleness():
    uid, token, pid = _seed_user_project()
    ctx = _ctx(token)

    # Seed an existing breakdown element so the staleness flag is exercised
    # (the helper only flips stale when a breakdown already exists — Phase 54).
    from app.models.database import BreakdownElement, BreakdownCategory
    with mcp_session() as db:
        db.add(BreakdownElement(project_id=pid, name="Knife", category=BreakdownCategory.PROP))
        db.commit()

    text = "INT. ROOM - DAY\nA sits.\n\nEXT. PARK - DAY\nB runs."
    written = _fn("screenplay_write")(ctx, project_id=pid, text=text)
    assert written["data"]["scene_count"] == 2

    # read back
    read = _fn("screenplay_read")(ctx, project_id=pid)
    assert len(read["scenes"]) == 2
    assert read["scenes"][0]["title"].startswith("INT. ROOM")

    # ScreenplayContent rows were (re)created; breakdown marked stale (it exists)
    with mcp_session() as db:
        rows = db.query(ScreenplayContent).filter(ScreenplayContent.project_id == pid).count()
        assert rows == 2
        proj = db.query(ProjectModel).filter(ProjectModel.id == pid).first()
        assert proj.breakdown_stale is True


@pytest.mark.anyio
async def test_write_is_idempotent_no_duplicate_rows():
    uid, token, pid = _seed_user_project()
    ctx = _ctx(token)
    text = "INT. A - DAY\none\n\nINT. B - DAY\ntwo"
    _fn("screenplay_write")(ctx, project_id=pid, text=text)
    _fn("screenplay_write")(ctx, project_id=pid, text=text)  # second save
    with mcp_session() as db:
        rows = db.query(ScreenplayContent).filter(ScreenplayContent.project_id == pid).count()
        assert rows == 2  # replaced, not accumulated


@pytest.mark.anyio
async def test_write_read_owner_scoped():
    uid_a, token_a, pid = _seed_user_project()
    uid_b, token_b, _ = _seed_user_project()
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _fn("screenplay_read")(_ctx(token_b), project_id=pid)
    assert exc.value.status_code == 404

    with pytest.raises(HTTPException):
        _fn("screenplay_write")(_ctx(token_b), project_id=pid, text="INT. X - DAY\nhi")
