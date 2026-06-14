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
