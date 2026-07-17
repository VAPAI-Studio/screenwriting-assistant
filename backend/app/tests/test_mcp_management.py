"""Tests for management MCP tools (Phase 57): project_list/get/create + show
reads, owner-scoped (MCPP-01..03, MCPF-04).

Calls the registered tools' underlying functions with a fake Context carrying a
real sa_ bearer header, against the app DB. No live model, no MCP transport.
"""

import hashlib
import uuid
from types import SimpleNamespace

import pytest

from sqlalchemy.orm import sessionmaker

from app.mcp_server.server import mcp
from app.mcp_server.session import mcp_session, set_session_factory_override
from app.models.database import ApiKey as ApiKeyModel, User as UserModel


@pytest.fixture(autouse=True)
def _mcp_uses_test_db(test_engine):
    """Point mcp_session() at the shared sqlite test engine for these tests, so
    the tools (and our seeding) hit the same DB regardless of suite ordering."""
    factory = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    set_session_factory_override(factory)
    yield
    set_session_factory_override(None)


def _seed_user_and_key():
    # Seed through the SAME session the tools use (mcp_session/app SessionLocal)
    # so test and tool always agree on which DB they hit, regardless of suite
    # ordering or fixtures that rebind other engines.
    with mcp_session() as db:
        uid = str(uuid.uuid4())
        db.add(UserModel(id=uid, email=f"mg_{uid[:8]}@x.com", hashed_password="h", display_name="MG"))
        db.flush()
        token = f"sa_mg_{uuid.uuid4().hex}"
        db.add(ApiKeyModel(
            user_id=uid, name="k", key_prefix=token[:8],
            key_hash=hashlib.sha256(token.encode()).hexdigest(),
        ))
        db.commit()
        return uid, token


def _ctx(token):
    """A minimal stand-in for mcp Context exposing request_context.request.headers."""
    request = SimpleNamespace(headers={"authorization": f"Bearer {token}"})
    return SimpleNamespace(request_context=SimpleNamespace(request=request))


def _fn(name):
    return mcp._tool_manager.get_tool(name).fn


@pytest.mark.anyio
async def test_project_create_list_get_roundtrip():
    uid, token = _seed_user_and_key()
    ctx = _ctx(token)

    created = _fn("project_create")(ctx, title="My MCP Film", framework="three_act")
    pid = created["data"]["project_id"]
    assert created["data"]["title"] == "My MCP Film"
    assert created["data"]["framework"] == "three_act"

    listed = _fn("project_list")(ctx)
    assert any(p["project_id"] == pid for p in listed["projects"])

    got = _fn("project_get")(ctx, project_id=pid)
    assert got["data"]["project_id"] == pid


@pytest.mark.anyio
async def test_project_create_rejects_bad_input():
    uid, token = _seed_user_and_key()
    ctx = _ctx(token)
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        _fn("project_create")(ctx, title="x")  # too short
    with pytest.raises(HTTPException):
        _fn("project_create")(ctx, title="Valid Title", framework="not_a_framework")


@pytest.mark.anyio
async def test_project_get_is_owner_scoped():
    uid_a, token_a = _seed_user_and_key()
    uid_b, token_b = _seed_user_and_key()
    from fastapi import HTTPException

    created = _fn("project_create")(_ctx(token_a), title="A's Project", framework="three_act")
    pid = created["data"]["project_id"]

    # User B cannot read user A's project.
    with pytest.raises(HTTPException) as exc:
        _fn("project_get")(_ctx(token_b), project_id=pid)
    assert exc.value.status_code == 404

    # And it doesn't appear in B's list.
    listed_b = _fn("project_list")(_ctx(token_b))
    assert all(p["project_id"] != pid for p in listed_b["projects"])


@pytest.mark.anyio
async def test_invalid_token_rejected():
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        _fn("project_list")(_ctx("sa_not_a_real_key"))


# --- Series creation over MCP (Phase: agent-autonomous series) --------------

@pytest.mark.anyio
async def test_show_bible_season_slot_roundtrip():
    """An agent can build a series end to end over MCP: create show, write the
    full bible (incl. new engine fields + structured cast), create a season and
    a slot, and read the bible back with every field."""
    uid, token = _seed_user_and_key()
    ctx = _ctx(token)

    show = _fn("show_create")(ctx, title="Neon Heist", continuity_mode="connected")
    show_id = show["data"]["show_id"]

    _fn("bible_write")(
        ctx, show_id=show_id,
        central_premise="A crew that only steals what was already stolen.",
        story_engine="Each week a new mark with dirty money walks in.",
        series_questions="Will Ada go straight? Who is the inside man?",
        regular_cast=[
            {"name": "Ada", "role": "the planner", "arc": "loyalty tested"},
            {"name": "", "role": "", "arc": ""},  # dropped
            "junk",  # dropped
        ],
        tone_style="Neon-noir.",
    )

    bible = _fn("show_read_bible")(ctx, show_id=show_id)["data"]
    assert bible["central_premise"].startswith("A crew that only steals")
    assert bible["story_engine"]
    assert bible["series_questions"]
    assert len(bible["regular_cast"]) == 1
    assert bible["regular_cast"][0]["name"] == "Ada"
    assert bible["tone_style"] == "Neon-noir."

    season = _fn("season_create")(ctx, show_id=show_id, title="Season One")
    season_id = season["data"]["season_id"]
    assert season["data"]["number"] == 1

    slot = _fn("slot_create")(ctx, season_id=season_id, title="Pilot", logline="The job that starts it.")
    assert slot["data"]["slot_number"] == 1
    # Second slot auto-increments.
    slot2 = _fn("slot_create")(ctx, season_id=season_id, title="Fallout")
    assert slot2["data"]["slot_number"] == 2


@pytest.mark.anyio
async def test_bible_write_is_partial():
    """bible_write only touches the fields passed; omitted fields are preserved."""
    uid, token = _seed_user_and_key()
    ctx = _ctx(token)
    show_id = _fn("show_create")(ctx, title="Partial Show")["data"]["show_id"]

    _fn("bible_write")(ctx, show_id=show_id, tone_style="Bleak.")
    _fn("bible_write")(ctx, show_id=show_id, central_premise="A premise.")

    bible = _fn("show_read_bible")(ctx, show_id=show_id)["data"]
    assert bible["tone_style"] == "Bleak."          # untouched by second call
    assert bible["central_premise"] == "A premise."


@pytest.mark.anyio
async def test_bible_draft_proposes_without_saving(monkeypatch):
    """bible_draft returns an AI proposal but writes nothing to the show."""
    uid, token = _seed_user_and_key()
    ctx = _ctx(token)
    show_id = _fn("show_create")(ctx, title="Draft Show")["data"]["show_id"]

    from unittest.mock import AsyncMock
    fake = {
        "bible_central_premise": "PROPOSED PREMISE", "bible_story_engine": "",
        "bible_series_questions": "", "bible_regular_cast": [],
        "bible_characters": "", "bible_world_setting": "",
        "bible_season_arc": "", "bible_tone_style": "",
    }
    from app.services import template_ai_service as tas_mod
    monkeypatch.setattr(tas_mod.template_ai_service, "generate_series_bible", AsyncMock(return_value=fake))

    out = await _fn("bible_draft")(ctx, show_id=show_id, logline="seed")
    assert out["data"]["bible_central_premise"] == "PROPOSED PREMISE"
    # Nothing saved: the show's bible is still empty.
    bible = _fn("show_read_bible")(ctx, show_id=show_id)["data"]
    assert bible["central_premise"] == ""


@pytest.mark.anyio
async def test_series_tools_owner_scoped():
    uid_a, token_a = _seed_user_and_key()
    uid_b, token_b = _seed_user_and_key()
    from fastapi import HTTPException

    show_id = _fn("show_create")(_ctx(token_a), title="A's Show")["data"]["show_id"]
    with pytest.raises(HTTPException) as exc:
        _fn("bible_write")(_ctx(token_b), show_id=show_id, tone_style="hijack")
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException):
        _fn("season_create")(_ctx(token_b), show_id=show_id)
