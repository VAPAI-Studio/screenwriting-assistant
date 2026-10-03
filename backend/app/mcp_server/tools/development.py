"""Development MCP tools — the AI pipeline that turns a brief into a screenplay.

Before these tools existed, the only way to get a screenplay into the platform
over MCP was screenplay_write (raw text, no AI). An external agent therefore
had to write the whole script itself in one pass, bypassing everything that
makes the platform's scripts better than a single LLM pass: story development
(core, cast with distinct dialogue styles, beats), the scene wizard's ten
dramatic fields per scene, per-scene generation with running continuity, the
critique + rewrite loop, the book doctrine and the whole-script polish.

These three LONG-RUNNING tools expose that pipeline, one phase each:

  story_develop        brief  -> story core + cast + beats     (story phase)
  scenes_generate      story  -> scene list                    (scenes phase)
  screenplay_generate  scenes -> full screenplay               (write phase)

Each follows the Phase 56 job pattern: validate + load inside a short-lived
session, run the AI with NO session held across awaits (D-56-B), then reopen a
session to persist. Scenes and screenplay are REPLACED on every run (idempotent,
like screenplay_write). A WizardRun row is recorded so the web UI and
screenplay_generate_scene see the same history/config a web-driven run leaves.
"""

import logging
from typing import Dict, List, Optional

from mcp.server.fastmcp import Context
from fastapi import HTTPException
from sqlalchemy.orm.attributes import flag_modified

from ...config import settings
from ...models import database
from ...models.schemas import ContinuityMode
from ...services import doctrine_service
from ...services.template_ai_service import template_ai_service
from ...services.agent_review_middleware import agent_review_middleware
from ...templates import get_template
from ...utils.bible_context import build_bible_context, _build_prior_episodes_block
from ...api.endpoints.wizards import (
    _get_project_context,
    _get_character_data,
    _scene_episodes_for_regen,
    apply_wizard_result_to_db,
)
from ..context import resolve_user, mcp_session
from ..session import get_session_factory
from ..jobs import registry

logger = logging.getLogger(__name__)

STORY_PHASE = "story"
SCENES_PHASE = "scenes"
WRITE_PHASE = "write"
MIN_BRIEF_CHARS = 20


# ---------------------------------------------------------------------------
# helpers (all run inside a caller-owned short-lived session)
# ---------------------------------------------------------------------------

def _owned_project(db, owner_id: str, project_id: str) -> database.Project:
    project = db.query(database.Project).filter(
        database.Project.id == str(project_id),
        database.Project.owner_id == str(owner_id),
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.template:
        raise HTTPException(status_code=400, detail="Project has no template")
    return project


def _template_id(project: database.Project) -> str:
    t = project.template
    return t.value if hasattr(t, "value") else str(t)


def _phase_subsections(template_id: str, phase_id: str) -> List[Dict]:
    """Ordered subsection configs of one phase of a template."""
    for phase in get_template(template_id).get("phases", []):
        if phase.get("id") == phase_id:
            return list(phase.get("subsections", []))
    return []


def _get_or_create_pd(db, project_id, phase: str, key: str) -> database.PhaseData:
    pd = db.query(database.PhaseData).filter(
        database.PhaseData.project_id == project_id,
        database.PhaseData.phase == phase,
        database.PhaseData.subsection_key == key,
    ).first()
    if pd is None:
        pd = database.PhaseData(project_id=project_id, phase=phase, subsection_key=key, content={})
        db.add(pd)
        db.flush()
    return pd


def _merge_pd_content(pd: database.PhaseData, fields: Dict) -> None:
    existing = dict(pd.content or {})
    existing.update({k: v for k, v in fields.items() if v})
    pd.content = existing
    flag_modified(pd, "content")


def _record_run(db, project_id, wizard_type: str, phase: str, config: Dict, result: Dict) -> str:
    """Persist a completed WizardRun so the web UI / regenerate path see this run."""
    run = database.WizardRun(
        project_id=project_id,
        wizard_type=wizard_type,
        phase=phase,
        config={k: v for k, v in config.items() if not k.startswith("_")},
        result=result,
        status="completed",
    )
    db.add(run)
    db.flush()
    return str(run.id)


def _with_language(guidance: str, language: str) -> str:
    guidance = (guidance or "").strip()
    language = (language or "").strip()
    if language:
        line = f"Write ALL output in {language}."
        guidance = f"{guidance}\n{line}" if guidance else line
    return guidance


def _idea_runtime_target(db, project_id) -> str:
    pd = db.query(database.PhaseData).filter(
        database.PhaseData.project_id == project_id,
        database.PhaseData.phase == "idea",
        database.PhaseData.subsection_key == "idea_wizard",
    ).first()
    return str((pd.content or {}).get("runtime_target", "") or "") if pd else ""


def _story_is_developed(db, project_id) -> bool:
    """True when the story phase has any content (core fields, beats or cast)."""
    pds = db.query(database.PhaseData).filter(
        database.PhaseData.project_id == project_id,
        database.PhaseData.phase == STORY_PHASE,
    ).all()
    for pd in pds:
        if any(v for v in (pd.content or {}).values()):
            return True
        if db.query(database.ListItem).filter(database.ListItem.phase_data_id == pd.id).count():
            return True
    return False


def _meta_from_review(result: Dict, review: Dict, doctrine_cards: Optional[List[Dict]] = None) -> Dict:
    if not isinstance(result, dict):
        result = {"output": result}
    meta = result.setdefault("_meta", {})
    meta["agents_consulted"] = review.get("agents_consulted", [])
    meta["review_applied"] = review.get("review_applied", False)
    if doctrine_cards is not None:
        meta["doctrine_used"] = [
            {"name": c.get("name"), "source": c.get("source")} for c in doctrine_cards[:6]
        ]
    return result


# ---------------------------------------------------------------------------
# story_develop
# ---------------------------------------------------------------------------

async def _develop_story(project_id: str, template_id: str, guidance: str, overwrite: bool) -> Dict:
    """Job body: fill every story-phase subsection in template order.

    card_grid / structured_form -> fill_blanks (core, beats, ...)
    repeatable_cards            -> generate_cast (the whole cast in one call)
    Context is rebuilt before each step so core feeds the cast and both feed
    the beats. Sessions are opened only to read/write, never across the AI call.
    """
    report: Dict = {"steps": [], "errors": []}
    guidance_block = f"\n\n## Development guidance\n{guidance}" if guidance else ""

    for sub in _phase_subsections(template_id, STORY_PHASE):
        key = sub["key"]
        pattern = sub.get("ui_pattern", "")

        if pattern in ("card_grid", "structured_form"):
            with mcp_session() as db:
                project = db.query(database.Project).filter(database.Project.id == project_id).first()
                context = _get_project_context(db, project, bible_context=build_bible_context(db, project))
                pd = _get_or_create_pd(db, project_id, STORY_PHASE, key)
                current = {} if overwrite else dict(pd.content or {})
                db.commit()

            result = await template_ai_service.fill_blanks(
                current_content=current,
                subsection_config=sub,
                project_context=context + guidance_block,
            )
            if result.get("error"):
                report["errors"].append({"step": key, "error": result["error"]})
            fields = result.get("content") or {}
            with mcp_session() as db:
                pd = _get_or_create_pd(db, project_id, STORY_PHASE, key)
                if overwrite:
                    pd.content = {}
                _merge_pd_content(pd, fields)
                db.commit()
                filled = [k for k, v in (pd.content or {}).items() if v]
            report["steps"].append({"subsection": key, "fields_filled": filled})
            report[key] = {k: v for k, v in fields.items() if v}

        elif pattern == "repeatable_cards":
            with mcp_session() as db:
                project = db.query(database.Project).filter(database.Project.id == project_id).first()
                context = _get_project_context(db, project, bible_context=build_bible_context(db, project))
                pd = _get_or_create_pd(db, project_id, STORY_PHASE, key)
                existing = db.query(database.ListItem).filter(
                    database.ListItem.phase_data_id == pd.id
                ).order_by(database.ListItem.sort_order).all()
                if existing and overwrite:
                    for li in existing:
                        db.delete(li)
                    existing = []
                db.commit()
                kept = [{"item_type": li.item_type, "name": (li.content or {}).get("name", "")} for li in existing]

            if kept:
                # A cast already exists and overwrite is False: keep it untouched.
                report["steps"].append({"subsection": key, "characters_kept": len(kept)})
                report[key] = kept
                continue

            result = await template_ai_service.generate_cast(
                card_groups=sub.get("card_groups", []),
                project_context=context,
                guidance=guidance,
            )
            if result.get("error"):
                report["errors"].append({"step": key, "error": result["error"]})
            characters = result.get("characters") or []
            with mcp_session() as db:
                pd = _get_or_create_pd(db, project_id, STORY_PHASE, key)
                for i, c in enumerate(characters):
                    content = {k: v for k, v in c.items() if k != "item_type"}
                    db.add(database.ListItem(
                        phase_data_id=pd.id,
                        item_type=c["item_type"],
                        sort_order=i,
                        content=content,
                        status="draft",
                    ))
                db.commit()
            report["steps"].append({"subsection": key, "characters_created": len(characters)})
            report[key] = [{"item_type": c["item_type"], "name": c.get("name", "")} for c in characters]

    with mcp_session() as db:
        project = db.query(database.Project).filter(database.Project.id == project_id).first()
        report["story_developed"] = _story_is_developed(db, project_id)
        _record_run(db, project_id, "story_develop", STORY_PHASE,
                    {"custom_guidance": guidance, "overwrite": overwrite},
                    dict(report))
        db.commit()

    report["summary"] = (
        f"Story developed: {len(report['steps'])} subsection(s) filled"
        + (f", {len(report['errors'])} error(s)" if report["errors"] else "")
        + ". Next: scenes_generate."
    )
    return report


# ---------------------------------------------------------------------------
# scenes_generate
# ---------------------------------------------------------------------------

async def _generate_scenes(project_id: str, template_id: str, config: Dict) -> Dict:
    result = await template_ai_service.wizard_generate(
        wizard_type="scene_wizard", config=config,
        project_context=config.pop("_project_context"), template_id=template_id,
    )
    if not result.get("scenes"):
        raise RuntimeError(f"Scene generation returned no scenes: {result.get('error', 'unknown error')}")

    review = await agent_review_middleware.review_step_output(
        phase=SCENES_PHASE, subsection_key="scene_wizard", raw_output=result,
        owner_id="", session_factory=get_session_factory(), wizard_type="scene_wizard",
    )
    result = _meta_from_review(review["output"], review)

    with mcp_session() as db:
        project = db.query(database.Project).filter(database.Project.id == project_id).first()
        # REPLACE semantics: drop the previous scene list before applying.
        scenes_pd = db.query(database.PhaseData).filter(
            database.PhaseData.project_id == project.id,
            database.PhaseData.phase == SCENES_PHASE,
            database.PhaseData.subsection_key == "scene_list",
        ).first()
        if scenes_pd:
            db.query(database.ListItem).filter(
                database.ListItem.phase_data_id == scenes_pd.id
            ).delete(synchronize_session=False)
            db.flush()
        applied = apply_wizard_result_to_db(db, project, SCENES_PHASE, "scene_wizard", result)
        _record_run(db, project.id, "scene_wizard", SCENES_PHASE, config, result)
        db.commit()

    scenes = result.get("scenes", [])
    return {
        "summary": f"Generated {applied.get('items_created', 0)} scene(s) (previous scene list replaced). Next: screenplay_generate.",
        "scene_count": applied.get("items_created", 0),
        "scenes": [
            {"episode_index": i, "summary": s.get("summary", ""), "arena": s.get("arena", "")}
            for i, s in enumerate(scenes)
        ],
        "_meta": result.get("_meta", {}),
    }


# ---------------------------------------------------------------------------
# screenplay_generate
# ---------------------------------------------------------------------------

async def _generate_screenplay(project_id: str, template_id: str, config: Dict, continuity_context: Optional[str]) -> Dict:
    doctrine_cards = config.get("_doctrine_cards") or []
    result = await template_ai_service.wizard_generate(
        wizard_type="script_writer_wizard", config=config,
        project_context=config.pop("_project_context"), template_id=template_id,
    )
    screenplays = result.get("screenplays") or []
    if not screenplays:
        raise RuntimeError(f"Screenplay generation returned no scenes: {result.get('error', 'unknown error')}")
    rubric_scores = result.get("rubric_scores")

    review = await agent_review_middleware.review_step_output(
        phase=WRITE_PHASE, subsection_key="script_writer_wizard", raw_output=result,
        owner_id="", session_factory=get_session_factory(),
        wizard_type="script_writer_wizard", continuity_context=continuity_context,
    )
    result = _meta_from_review(review["output"], review, doctrine_cards)
    if rubric_scores:
        result["_meta"]["rubric_scores"] = rubric_scores

    with mcp_session() as db:
        project = db.query(database.Project).filter(database.Project.id == project_id).first()
        # REPLACE semantics (same as screenplay_write): no duplicate rows on re-run.
        db.query(database.ScreenplayContent).filter(
            database.ScreenplayContent.project_id == str(project.id)
        ).delete(synchronize_session=False)
        db.flush()
        applied = apply_wizard_result_to_db(db, project, WRITE_PHASE, "script_writer_wizard", result)
        _record_run(db, project.id, "script_writer_wizard", WRITE_PHASE, config,
                    {"_meta": result.get("_meta", {}), "scene_count": applied.get("items_created", 0)})
        db.commit()

    final = result.get("screenplays") or screenplays
    failed = [s.get("episode_index") for s in final if "error" in s]
    return {
        "summary": (
            f"Wrote {applied.get('items_created', 0)} scene(s) (previous screenplay replaced)"
            + (f"; {len(failed)} scene(s) FAILED to generate: {failed}" if failed else "")
            + ". Next: screenplay_read to review, then breakdown_extract."
        ),
        "scene_count": applied.get("items_created", 0),
        "failed_scenes": failed,
        "scenes": [
            {"episode_index": s.get("episode_index", i), "title": s.get("title", ""), "content": s.get("content", "")}
            for i, s in enumerate(final)
        ],
        "synopsis": result.get("synopsis", ""),
        "_meta": result.get("_meta", {}),
    }


# ---------------------------------------------------------------------------
# tool registration
# ---------------------------------------------------------------------------

def register(mcp):
    """Register development tools on the given FastMCP instance."""

    @mcp.tool()
    async def story_develop(
        ctx: Context,
        project_id: str,
        brief: str,
        genre: str = "",
        tone: str = "",
        runtime_target: str = "",
        guidance: str = "",
        language: str = "",
        overwrite: bool = False,
    ) -> dict:
        """PIPELINE STEP 3 (DEVELOP) — turn a brief into a developed story: the
        template's story core (logline, theme, stakes, motif...), a full cast with
        a DISTINCT dialogue style per character, and the story beats. This is the
        first AI step for any new screenplay; run it before scenes_generate.

        brief: the factual, specific seed — for a news-based short: what happened,
        who was involved, where, what was really at stake, and the angle you want.
        The more concrete the brief, the more recognizable the resulting film.
        genre / tone / runtime_target: optional; stored with the brief.
        guidance: optional development notes (e.g. "keep the real event
        recognizable", "two locations max", "no on-screen text").
        language: the language the story (and later the screenplay) must be
        written in, e.g. "Spanish (Rioplatense)". Omit to follow the brief.
        overwrite: False (default) fills only EMPTY story fields and keeps an
        existing cast; True regenerates the whole story phase from the brief.

        LONG-RUNNING: returns a job_id immediately; poll job_status(job_id).
        The result lists what was filled per subsection. Owner-scoped (404).
        """
        brief = (brief or "").strip()
        if len(brief) < MIN_BRIEF_CHARS:
            raise HTTPException(status_code=400, detail=f"brief must be at least {MIN_BRIEF_CHARS} characters of concrete story material")
        with mcp_session() as db:
            user = resolve_user(ctx, db)
            owner_id = str(user.id)
            project = _owned_project(db, owner_id, project_id)
            template_id = _template_id(project)
            pid = str(project.id)
            idea = _get_or_create_pd(db, project.id, "idea", "idea_wizard")
            _merge_pd_content(idea, {
                "initial_idea": brief,
                "genre": genre,
                "tone": tone,
                "runtime_target": runtime_target,
                "guidance": guidance,
            })
            db.commit()

        job = await registry.create(owner_id, kind="story_develop")

        async def _work():
            return await _develop_story(pid, template_id, _with_language(guidance, language), overwrite)

        await registry.run(job, _work)
        return {"job_id": job.id, "status": job.status, "kind": job.kind,
                "next": "Poll job_status(job_id) until done, then call scenes_generate."}

    @mcp.tool()
    async def scenes_generate(
        ctx: Context,
        project_id: str,
        count: str = "auto",
        runtime_target: str = "",
        guidance: str = "",
        language: str = "",
    ) -> dict:
        """PIPELINE STEP 3 (DEVELOP, scenes) — plan the scene list from the
        developed story: each scene gets the ten dramatic fields the screenplay
        generator needs (summary, arena, inciting incident, goal, subtext, turning
        point, crisis, climax, fallout, push forward). Requires story_develop (or
        a hand-filled story phase) first.

        count: "auto" (default) or a range like "3-4", "5-6".
        runtime_target: e.g. "8 minutes"; defaults to the brief's runtime_target.
        guidance / language: as in story_develop.

        REPLACES the project's existing scene list. LONG-RUNNING: returns a
        job_id; poll job_status(job_id). The result lists the planned scenes.
        Owner-scoped (404).
        """
        with mcp_session() as db:
            user = resolve_user(ctx, db)
            owner_id = str(user.id)
            project = _owned_project(db, owner_id, project_id)
            if not _story_is_developed(db, project.id):
                raise HTTPException(status_code=400, detail="The story phase is empty — run story_develop first")
            template_id = _template_id(project)
            pid = str(project.id)
            config = {
                "count": (count or "auto").strip() or "auto",
                "runtime_target": (runtime_target or "").strip() or _idea_runtime_target(db, project.id),
                "custom_guidance": _with_language(guidance, language),
                "_characters": _get_character_data(db, project.id),
                "_project_context": _get_project_context(db, project, bible_context=build_bible_context(db, project)),
            }

        job = await registry.create(owner_id, kind="scenes_generate")

        async def _work():
            return await _generate_scenes(pid, template_id, config)

        await registry.run(job, _work)
        return {"job_id": job.id, "status": job.status, "kind": job.kind,
                "next": "Poll job_status(job_id) until done, then call screenplay_generate."}

    @mcp.tool()
    async def screenplay_generate(
        ctx: Context,
        project_id: str,
        runtime_target: str = "",
        guidance: str = "",
        language: str = "",
        use_doctrine: bool = True,
    ) -> dict:
        """PIPELINE STEP 4 (WRITE) — the primary way to produce a NEW screenplay.
        Writes the full screenplay from the planned scene list through the
        platform's quality pipeline: scene-by-scene generation with running
        continuity and per-character voice, a story-editor critique + rewrite loop
        per scene, craft doctrine from the book library, and a whole-script polish
        pass. Requires scenes_generate (or a hand-built scene list) first.

        runtime_target: e.g. "8 minutes"; defaults to the brief's runtime_target.
        guidance: notes for the writer (tone, constraints, what to avoid).
        language: language of the screenplay, e.g. "Spanish (Rioplatense)".
        use_doctrine: inject the book library's craft concepts (default True).

        REPLACES the project's existing screenplay and marks breakdown/shotlist
        stale. LONG-RUNNING (several minutes for 5-6 scenes): returns a job_id;
        poll job_status(job_id). The result carries every scene's text plus
        per-scene rubric scores. Review with screenplay_read; for hand edits
        screenplay_write the full text back; for one weak scene use
        screenplay_generate_scene. Owner-scoped (404).
        """
        with mcp_session() as db:
            user = resolve_user(ctx, db)
            owner_id = str(user.id)
            project = _owned_project(db, owner_id, project_id)
            template_id = _template_id(project)
            pid = str(project.id)
            episodes = _scene_episodes_for_regen(db, project.id)
            if not episodes:
                raise HTTPException(status_code=400, detail="No planned scenes — run scenes_generate first")
            bible_context = build_bible_context(db, project)
            continuity_context = None
            if project.show_id:
                show = db.query(database.Show).filter(database.Show.id == str(project.show_id)).first()
                if show and show.continuity_mode == ContinuityMode.CONNECTED.value:
                    continuity_context = _build_prior_episodes_block(db, show, project)
            config = {
                "episodes": episodes,
                "runtime_target": (runtime_target or "").strip() or _idea_runtime_target(db, project.id),
                "custom_guidance": _with_language(guidance, language),
                "use_doctrine": use_doctrine,
                "_characters": _get_character_data(db, project.id),
                "_project_context": _get_project_context(db, project, bible_context=bible_context),
            }
            if settings.DOCTRINE_IN_GENERATION and use_doctrine:
                config["_doctrine_cards"] = doctrine_service.build_doctrine_cards(template_id, db)

        job = await registry.create(owner_id, kind="screenplay_generate")

        async def _work():
            return await _generate_screenplay(pid, template_id, config, continuity_context)

        await registry.run(job, _work)
        return {"job_id": job.id, "status": job.status, "kind": job.kind,
                "next": "Poll job_status(job_id) until done (this takes minutes), then screenplay_read."}
