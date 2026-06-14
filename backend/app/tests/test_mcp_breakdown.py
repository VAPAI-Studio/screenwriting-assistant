"""Tests for breakdown MCP tools (Phase 59): breakdown_read (category-scoped,
appearances) + breakdown_extract (long-running, job-id). Owner-scoped.
"""

import hashlib
import uuid

import pytest
from types import SimpleNamespace
from sqlalchemy.orm import sessionmaker

from app.mcp_server.server import mcp
from app.mcp_server.session import mcp_session, set_session_factory_override
from app.models.database import (
    ApiKey as ApiKeyModel, User as UserModel, Project as ProjectModel,
    BreakdownElement, BreakdownCategory, TemplateType,
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


def _seed(with_elements=True):
    with mcp_session() as db:
        uid = str(uuid.uuid4())
        db.add(UserModel(id=uid, email=f"bd_{uid[:8]}@x.com", hashed_password="h", display_name="BD"))
        db.flush()
        token = f"sa_bd_{uuid.uuid4().hex}"
        db.add(ApiKeyModel(user_id=uid, name="k", key_prefix=token[:8],
                           key_hash=hashlib.sha256(token.encode()).hexdigest()))
        pid = str(uuid.uuid4())
        db.add(ProjectModel(id=pid, owner_id=uid, title="BD", template=TemplateType.SHORT_MOVIE, template_config={}))
        if with_elements:
            db.add(BreakdownElement(project_id=pid, name="Maya", category=BreakdownCategory.CHARACTER))
            db.add(BreakdownElement(project_id=pid, name="Knife", category=BreakdownCategory.PROP))
        db.commit()
        return uid, token, pid


@pytest.mark.anyio
async def test_breakdown_read_all_and_by_category():
    uid, token, pid = _seed()
    ctx = _ctx(token)

    all_el = _fn("breakdown_read")(ctx, project_id=pid)
    assert len(all_el["elements"]) == 2
    names = {e["name"] for e in all_el["elements"]}
    assert names == {"Maya", "Knife"}

    props = _fn("breakdown_read")(ctx, project_id=pid, category="prop")
    assert len(props["elements"]) == 1
    assert props["elements"][0]["name"] == "Knife"
    assert props["elements"][0]["category"] == "prop"


@pytest.mark.anyio
async def test_breakdown_read_rejects_bad_category():
    uid, token, pid = _seed()
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        _fn("breakdown_read")(_ctx(token), project_id=pid, category="not_a_category")


@pytest.mark.anyio
async def test_breakdown_read_owner_scoped():
    uid_a, token_a, pid = _seed()
    uid_b, token_b, _ = _seed()
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        _fn("breakdown_read")(_ctx(token_b), project_id=pid)
    assert exc.value.status_code == 404


@pytest.mark.anyio
async def test_breakdown_extract_returns_job(monkeypatch):
    """breakdown_extract returns a job_id immediately (AI extraction mocked)."""
    import app.mcp_server.tools.breakdown as bd
    from app.mcp_server.jobs import registry, DONE

    uid, token, pid = _seed(with_elements=False)

    async def fake_extract(db, project_id, bible_context=None):
        return SimpleNamespace(id=uuid.uuid4(), status="completed", element_count=3)

    monkeypatch.setattr(bd.breakdown_service, "extract", fake_extract)

    res = _fn("breakdown_extract")(_ctx(token), project_id=pid)
    # _fn returns a coroutine for async tools
    out = await res
    assert "job_id" in out
    job_id = out["job_id"]

    import asyncio
    for _ in range(100):
        job = await registry.get(job_id, uid)
        if job.status == DONE:
            break
        await asyncio.sleep(0.01)
    job = await registry.get(job_id, uid)
    assert job.status == DONE
    assert job.result["element_count"] == 3
