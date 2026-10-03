"""Tests for the development MCP tools: story_develop, scenes_generate and
screenplay_generate — the AI pipeline exposed over MCP so an external agent
develops and writes THROUGH the platform instead of pasting a one-pass script
via screenplay_write.

Every AI call (fill_blanks, generate_cast, wizard_generate) is mocked; the tests
assert the job machinery, the persistence shape (PhaseData / ListItem /
ScreenplayContent / WizardRun) and the REPLACE semantics.
"""

import asyncio
import hashlib
import uuid

import pytest
from types import SimpleNamespace
from sqlalchemy.orm import sessionmaker

from app.mcp_server.server import mcp, _INSTRUCTIONS
from app.mcp_server.session import mcp_session, set_session_factory_override
from app.mcp_server.jobs import registry, DONE, ERROR
import app.mcp_server.tools.development as dev
from app.models.database import (
    ApiKey as ApiKeyModel, User as UserModel, Project as ProjectModel,
    PhaseData, ListItem, ScreenplayContent, WizardRun, TemplateType,
    BreakdownElement, BreakdownCategory,
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
        db.add(UserModel(id=uid, email=f"dev_{uid[:8]}@x.com", hashed_password="h", display_name="DEV"))
        db.flush()
        token = f"sa_dev_{uuid.uuid4().hex}"
        db.add(ApiKeyModel(user_id=uid, name="k", key_prefix=token[:8],
                           key_hash=hashlib.sha256(token.encode()).hexdigest()))
        pid = str(uuid.uuid4())
        db.add(ProjectModel(id=pid, owner_id=uid, title="Dev Project",
                            template=TemplateType.SHORT_MOVIE, template_config={}))
        db.commit()
        return uid, token, pid


async def _wait(job_id, owner_id):
    for _ in range(300):
        got = await registry.get(job_id, owner_id)
        if got.status in (DONE, ERROR):
            return got
        await asyncio.sleep(0.01)
    raise AssertionError("job did not finish")


def _pd(db, pid, phase, key):
    return db.query(PhaseData).filter(
        PhaseData.project_id == pid, PhaseData.phase == phase, PhaseData.subsection_key == key,
    ).first()


def _items(db, pd):
    return db.query(ListItem).filter(ListItem.phase_data_id == pd.id).order_by(ListItem.sort_order).all()


# ---- registration / instructions ----

def test_development_tools_are_registered():
    for name in ("story_develop", "scenes_generate", "screenplay_generate"):
        assert mcp._tool_manager.get_tool(name) is not None


def test_instructions_route_new_screenplays_through_the_pipeline():
    assert "story_develop" in _INSTRUCTIONS
    assert "scenes_generate" in _INSTRUCTIONS
    assert "screenplay_generate" in _INSTRUCTIONS
    assert "NEVER write a new screenplay yourself" in _INSTRUCTIONS
    # screenplay_write is no longer sold as the primary way to create a screenplay.
    assert "primary way to put a screenplay" not in _INSTRUCTIONS
    write_doc = mcp._tool_manager.get_tool("screenplay_write").description
    assert "NOT the way to create a new screenplay" in write_doc


# ---- story_develop ----

@pytest.mark.anyio
async def test_story_develop_fills_core_cast_and_beats(monkeypatch):
    uid, token, pid = _seed_user_project()
    ctx = _ctx(token)
    calls = {"fill": [], "cast": 0}

    async def fake_fill(current_content, subsection_config, project_context):
        key = subsection_config["key"]
        calls["fill"].append(key)
        # The brief must reach the AI through the project context.
        assert "Un operador de tránsito" in project_context
        assert "Development guidance" in project_context
        fields = [c["key"] for c in subsection_config.get("cards", [])]
        return {"content": {f: f"{key}:{f}" for f in fields}}

    async def fake_cast(card_groups, project_context, guidance=""):
        calls["cast"] += 1
        assert "core:logline" in project_context  # core was written before casting
        return {"characters": [
            {"item_type": "protagonist", "name": "Ramona", "dialogue_style": "corta, seca"},
            {"item_type": "antagonist", "name": "Ibáñez", "dialogue_style": "florida"},
            {"item_type": "supporting", "name": "Tito", "role": "testigo", "dialogue_style": "pregunta todo"},
        ]}

    monkeypatch.setattr(dev.template_ai_service, "fill_blanks", fake_fill)
    monkeypatch.setattr(dev.template_ai_service, "generate_cast", fake_cast)

    out = await _fn("story_develop")(
        ctx, project_id=pid,
        brief="Un operador de tránsito descubre que las multas de su barrio se duplican de noche.",
        genre="Drama", runtime_target="8 minutes", guidance="Keep the real event recognizable",
        language="Spanish (Rioplatense)",
    )
    assert out["kind"] == "story_develop"
    job = await _wait(out["job_id"], uid)
    assert job.status == DONE, job.error
    assert calls["fill"] == ["core", "story"]
    assert calls["cast"] == 1
    assert job.result["story_developed"] is True

    with mcp_session() as db:
        idea = _pd(db, pid, "idea", "idea_wizard")
        assert idea.content["initial_idea"].startswith("Un operador")
        assert idea.content["runtime_target"] == "8 minutes"
        core = _pd(db, pid, "story", "core")
        assert core.content["logline"] == "core:logline"
        beats = _pd(db, pid, "story", "story")
        assert beats.content["climax"] == "story:climax"
        chars = _items(db, _pd(db, pid, "story", "characters"))
        assert [c.item_type for c in chars] == ["protagonist", "antagonist", "supporting"]
        assert chars[0].content["name"] == "Ramona"
        assert "item_type" not in chars[0].content
        runs = db.query(WizardRun).filter(WizardRun.project_id == pid, WizardRun.wizard_type == "story_develop").all()
        assert len(runs) == 1 and runs[0].status == "completed"


@pytest.mark.anyio
async def test_story_develop_keeps_existing_cast_unless_overwrite(monkeypatch):
    uid, token, pid = _seed_user_project()
    ctx = _ctx(token)
    with mcp_session() as db:
        pd = PhaseData(project_id=pid, phase="story", subsection_key="characters", content={})
        db.add(pd); db.flush()
        db.add(ListItem(phase_data_id=pd.id, item_type="protagonist", sort_order=0, content={"name": "Old"}))
        db.commit()

    cast_calls = {"n": 0}

    async def fake_fill(current_content, subsection_config, project_context):
        return {"content": {}}

    async def fake_cast(card_groups, project_context, guidance=""):
        cast_calls["n"] += 1
        return {"characters": [{"item_type": "protagonist", "name": "New"}]}

    monkeypatch.setattr(dev.template_ai_service, "fill_blanks", fake_fill)
    monkeypatch.setattr(dev.template_ai_service, "generate_cast", fake_cast)

    out = await _fn("story_develop")(ctx, project_id=pid, brief="x" * 40)
    job = await _wait(out["job_id"], uid)
    assert job.status == DONE, job.error
    assert cast_calls["n"] == 0
    with mcp_session() as db:
        chars = _items(db, _pd(db, pid, "story", "characters"))
        assert [c.content["name"] for c in chars] == ["Old"]

    out = await _fn("story_develop")(ctx, project_id=pid, brief="x" * 40, overwrite=True)
    job = await _wait(out["job_id"], uid)
    assert job.status == DONE, job.error
    assert cast_calls["n"] == 1
    with mcp_session() as db:
        chars = _items(db, _pd(db, pid, "story", "characters"))
        assert [c.content["name"] for c in chars] == ["New"]


@pytest.mark.anyio
async def test_story_develop_rejects_short_brief_and_foreign_project():
    uid, token, pid = _seed_user_project()
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await _fn("story_develop")(_ctx(token), project_id=pid, brief="too short")
    assert exc.value.status_code == 400
    uid2, token2, pid2 = _seed_user_project()
    with pytest.raises(HTTPException) as exc:
        await _fn("story_develop")(_ctx(token2), project_id=pid, brief="x" * 40)
    assert exc.value.status_code == 404


# ---- scenes_generate ----

@pytest.mark.anyio
async def test_scenes_generate_requires_story_then_replaces_scene_list(monkeypatch):
    uid, token, pid = _seed_user_project()
    ctx = _ctx(token)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await _fn("scenes_generate")(ctx, project_id=pid)
    assert exc.value.status_code == 400

    with mcp_session() as db:
        db.add(PhaseData(project_id=pid, phase="idea", subsection_key="idea_wizard", content={"runtime_target": "7 minutes"}))
        db.add(PhaseData(project_id=pid, phase="story", subsection_key="core", content={"logline": "L"}))
        sc = PhaseData(project_id=pid, phase="scenes", subsection_key="scene_list", content={})
        db.add(sc); db.flush()
        db.add(ListItem(phase_data_id=sc.id, item_type="scene", sort_order=0, content={"summary": "STALE"}))
        db.commit()

    seen = {}

    async def fake_wizard(wizard_type, config, project_context, template_id):
        seen.update(wizard_type=wizard_type, config=dict(config), template_id=template_id)
        return {"scenes": [{"summary": "A", "arena": "Kitchen"}, {"summary": "B", "arena": "Street"}]}

    monkeypatch.setattr(dev.template_ai_service, "wizard_generate", fake_wizard)

    out = await _fn("scenes_generate")(ctx, project_id=pid, count="2-3", guidance="tight", language="Spanish")
    job = await _wait(out["job_id"], uid)
    assert job.status == DONE, job.error
    assert seen["wizard_type"] == "scene_wizard"
    assert seen["template_id"] == "short_movie"
    assert seen["config"]["count"] == "2-3"
    assert seen["config"]["runtime_target"] == "7 minutes"  # inherited from the brief
    assert "Spanish" in seen["config"]["custom_guidance"] and "tight" in seen["config"]["custom_guidance"]
    assert job.result["scene_count"] == 2
    assert [s["summary"] for s in job.result["scenes"]] == ["A", "B"]

    with mcp_session() as db:
        items = _items(db, _pd(db, pid, "scenes", "scene_list"))
        assert [i.content["summary"] for i in items] == ["A", "B"]  # STALE replaced
        assert [i.sort_order for i in items] == [0, 1]
        runs = db.query(WizardRun).filter(WizardRun.project_id == pid, WizardRun.wizard_type == "scene_wizard").all()
        assert len(runs) == 1 and runs[0].config["count"] == "2-3"
        assert "_characters" not in runs[0].config


@pytest.mark.anyio
async def test_scenes_generate_job_errors_when_ai_returns_nothing(monkeypatch):
    uid, token, pid = _seed_user_project()
    with mcp_session() as db:
        db.add(PhaseData(project_id=pid, phase="story", subsection_key="core", content={"logline": "L"}))
        db.commit()

    async def fake_wizard(**kwargs):
        return {"scenes": [], "error": "boom"}

    monkeypatch.setattr(dev.template_ai_service, "wizard_generate", fake_wizard)
    out = await _fn("scenes_generate")(_ctx(token), project_id=pid)
    job = await _wait(out["job_id"], uid)
    assert job.status == ERROR
    assert "boom" in job.error


# ---- screenplay_generate ----

@pytest.mark.anyio
async def test_screenplay_generate_requires_scenes_then_replaces_screenplay(monkeypatch):
    uid, token, pid = _seed_user_project()
    ctx = _ctx(token)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await _fn("screenplay_generate")(ctx, project_id=pid)
    assert exc.value.status_code == 400

    with mcp_session() as db:
        sc = PhaseData(project_id=pid, phase="scenes", subsection_key="scene_list", content={})
        db.add(sc); db.flush()
        db.add(ListItem(phase_data_id=sc.id, item_type="scene", sort_order=0, content={"summary": "S1"}))
        db.add(ListItem(phase_data_id=sc.id, item_type="scene", sort_order=1, content={"summary": "S2"}))
        # A pre-existing screenplay row + breakdown element to prove REPLACE + stale.
        db.add(ScreenplayContent(project_id=pid, content="OLD", formatted_content={}))
        db.add(BreakdownElement(project_id=pid, name="Knife", category=BreakdownCategory.PROP))
        db.commit()

    seen = {}

    async def fake_wizard(wizard_type, config, project_context, template_id):
        seen.update(wizard_type=wizard_type, config=dict(config))
        return {
            "screenplays": [
                {"episode_index": 0, "title": "One", "content": "INT. A - DAY\nuno"},
                {"episode_index": 1, "title": "Two", "content": "INT. B - DAY\ndos"},
            ],
            "synopsis": "syn",
            "rubric_scores": [{"episode_index": 0, "scores": {"subtext": 4}}],
        }

    monkeypatch.setattr(dev.template_ai_service, "wizard_generate", fake_wizard)

    out = await _fn("screenplay_generate")(ctx, project_id=pid, runtime_target="9 minutes", guidance="g", language="Spanish")
    assert out["kind"] == "screenplay_generate"
    job = await _wait(out["job_id"], uid)
    assert job.status == DONE, job.error
    assert seen["wizard_type"] == "script_writer_wizard"
    assert [e["summary"] for e in seen["config"]["episodes"]] == ["S1", "S2"]
    assert seen["config"]["runtime_target"] == "9 minutes"
    assert "Spanish" in seen["config"]["custom_guidance"]
    assert job.result["scene_count"] == 2
    assert job.result["failed_scenes"] == []
    assert job.result["scenes"][1]["content"].startswith("INT. B")
    assert job.result["_meta"]["rubric_scores"][0]["scores"]["subtext"] == 4

    with mcp_session() as db:
        rows = db.query(ScreenplayContent).filter(ScreenplayContent.project_id == pid).all()
        assert sorted(r.content for r in rows) == ["INT. A - DAY\nuno", "INT. B - DAY\ndos"]  # OLD gone
        sp = _pd(db, pid, "write", "screenplay_editor")
        assert len(sp.content["screenplays"]) == 2 and sp.content["synopsis"] == "syn"
        proj = db.query(ProjectModel).filter(ProjectModel.id == pid).first()
        assert proj.breakdown_stale is True
        run = db.query(WizardRun).filter(WizardRun.project_id == pid, WizardRun.wizard_type == "script_writer_wizard").first()
        assert run is not None and run.config["runtime_target"] == "9 minutes"
        assert "_doctrine_cards" not in run.config and "episodes" in run.config

    # screenplay_read sees the generated scenes by episode_index.
    read = _fn("screenplay_read")(ctx, project_id=pid, scene_index=1)
    assert read["data"]["title"] == "Two"


@pytest.mark.anyio
async def test_screenplay_generate_reports_failed_scenes(monkeypatch):
    uid, token, pid = _seed_user_project()
    with mcp_session() as db:
        sc = PhaseData(project_id=pid, phase="scenes", subsection_key="scene_list", content={})
        db.add(sc); db.flush()
        db.add(ListItem(phase_data_id=sc.id, item_type="scene", sort_order=0, content={"summary": "S1"}))
        db.commit()

    async def fake_wizard(**kwargs):
        return {"screenplays": [{"episode_index": 0, "title": "S1", "content": "[Generation failed: x]", "error": "x"}]}

    monkeypatch.setattr(dev.template_ai_service, "wizard_generate", fake_wizard)
    out = await _fn("screenplay_generate")(_ctx(token), project_id=pid)
    job = await _wait(out["job_id"], uid)
    assert job.status == DONE, job.error
    assert job.result["failed_scenes"] == [0]
    assert "FAILED" in job.result["summary"]
