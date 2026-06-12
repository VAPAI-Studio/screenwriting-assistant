"""Tests for shotlist MCP tools (Phase 60): shotlist_read, shot_create,
shotlist_generate (long-running). Owner-scoped (MCPS-01/02/03)."""

import hashlib
import uuid

import pytest
from types import SimpleNamespace
from sqlalchemy.orm import sessionmaker

from app.mcp_server.server import mcp
from app.mcp_server.session import mcp_session, set_session_factory_override
from app.models.database import (
    ApiKey as ApiKeyModel, User as UserModel, Project as ProjectModel,
    Shot, TemplateType,
)


@pytest.fixture(autouse=True)
def _mcp_uses_test_db(test_engine):
    set_session_factory_override(sessionmaker(autocommit=False, autoflush=False, bind=test_engine))
    yield
    set_session_factory_override(None)


def _ctx(token):
    return SimpleNamespace(request_context=SimpleNamespace(
        request=SimpleNamespace(headers={"authorization": f"Bearer {token}"})))


def _fn(name):
    return mcp._tool_manager.get_tool(name).fn


def _seed():
    with mcp_session() as db:
        uid = str(uuid.uuid4())
        db.add(UserModel(id=uid, email=f"sl_{uid[:8]}@x.com", hashed_password="h", display_name="SL"))
        db.flush()
        token = f"sa_sl_{uuid.uuid4().hex}"
        db.add(ApiKeyModel(user_id=uid, name="k", key_prefix=token[:8],
                           key_hash=hashlib.sha256(token.encode()).hexdigest()))
        pid = str(uuid.uuid4())
        db.add(ProjectModel(id=pid, owner_id=uid, title="SL", template=TemplateType.SHORT_MOVIE, template_config={}))
        db.commit()
        return uid, token, pid


@pytest.mark.anyio
async def test_shot_create_then_read():
    uid, token, pid = _seed()
    ctx = _ctx(token)
    created = _fn("shot_create")(ctx, project_id=pid, fields={"size": "WIDE", "desc": "establishing"}, shot_number=1)
    assert created["data"]["fields"]["size"] == "WIDE"

    read = _fn("shotlist_read")(ctx, project_id=pid)
    assert read["summary"].startswith("1 shot")
    all_shots = [s for grp in read["scenes"] for s in grp["shots"]]
    assert any(s["fields"].get("size") == "WIDE" for s in all_shots)


@pytest.mark.anyio
async def test_shotlist_owner_scoped():
    uid_a, token_a, pid = _seed()
    uid_b, token_b, _ = _seed()
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        _fn("shotlist_read")(_ctx(token_b), project_id=pid)
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException):
        _fn("shot_create")(_ctx(token_b), project_id=pid, fields={})


@pytest.mark.anyio
async def test_shotlist_generate_returns_job(monkeypatch):
    import app.mcp_server.tools.shotlist as sl
    from app.mcp_server.jobs import registry, DONE

    uid, token, pid = _seed()

    async def fake_generate(db, project_id):
        return SimpleNamespace(model_dump=lambda: {"created": 4})

    monkeypatch.setattr(sl.shotlist_generation_service, "generate", fake_generate)

    out = await _fn("shotlist_generate")(_ctx(token), project_id=pid)
    assert "job_id" in out
    import asyncio
    for _ in range(100):
        job = await registry.get(out["job_id"], uid)
        if job.status == DONE:
            break
        await asyncio.sleep(0.01)
    job = await registry.get(out["job_id"], uid)
    assert job.status == DONE
    assert job.result == {"created": 4}
