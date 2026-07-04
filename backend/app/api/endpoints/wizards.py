# backend/app/api/endpoints/wizards.py

import logging
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from uuid import UUID

from ...config import settings
from ...models import schemas, database
from ..dependencies import get_db, get_current_user
from ...services import doctrine_service
from ...services.template_ai_service import template_ai_service
from ...db import SessionLocal
from ...services.agent_review_middleware import agent_review_middleware
from ...utils.bible_context import build_bible_context, _build_prior_episodes_block
from ...utils.episode_summary import regenerate_stale_priors
from ...models.schemas import ContinuityMode
from .phase_data import _mark_breakdown_stale, _mark_shotlist_stale
from .seasons import _get_owned_season, _season_slots
from .shows import _build_bible_text

logger = logging.getLogger(__name__)
router = APIRouter()

# Phase 4 (temporadas): the one wizard_type that runs season-scoped
# (WizardRun.season_id set, project_id NULL).
SEASON_MAP_WIZARD = "season_map_wizard"


def _get_project_context(db: Session, project: database.Project, bible_context: Optional[str] = None) -> str:
    """Build project context string from all phase data, including list items."""
    phase_data_records = db.query(database.PhaseData).filter(
        database.PhaseData.project_id == project.id
    ).all()

    project_data = {}
    list_items_map = {}
    for pd in phase_data_records:
        phase_key = pd.phase.value if hasattr(pd.phase, 'value') else pd.phase
        if phase_key not in project_data:
            project_data[phase_key] = {}
        project_data[phase_key][pd.subsection_key] = pd.content or {}

        # Include list items (characters, scenes, etc.)
        if pd.list_items:
            items = [{"item_type": li.item_type, **(li.content or {})} for li in pd.list_items]
            if items:
                list_items_map[f"{phase_key}.{pd.subsection_key}"] = items

    template_id = project.template.value if hasattr(project.template, 'value') else project.template
    return template_ai_service._build_project_context(project_data, template_id, list_items=list_items_map, project_title=project.title, bible_context=bible_context)


def _get_character_data(db: Session, project_id) -> list:
    """Fetch character ListItems for the project."""
    characters_pd = db.query(database.PhaseData).filter(
        database.PhaseData.project_id == project_id,
        database.PhaseData.phase == "story",
        database.PhaseData.subsection_key == "characters",
    ).first()
    if not characters_pd:
        return []
    items = db.query(database.ListItem).filter(
        database.ListItem.phase_data_id == characters_pd.id
    ).order_by(database.ListItem.sort_order).all()
    return [{"item_type": li.item_type, **(li.content or {})} for li in items]


async def _run_wizard_background(
    run_id, project_id, template_id: str,
    wizard_type: str, config: dict, phase: str, owner_id: str,
    bible_context: Optional[str] = None,
    continuity_context: Optional[str] = None,
):
    """Background task: run wizard generation and update the WizardRun record."""
    db = SessionLocal()
    wizard_run = None
    try:
        wizard_run = db.query(database.WizardRun).filter(
            database.WizardRun.id == run_id
        ).first()
        project = db.query(database.Project).filter(
            database.Project.id == project_id
        ).first()

        wizard_run.status = "running"
        db.commit()

        project_context = _get_project_context(db, project, bible_context=bible_context)

        # Craft doctrine (books Phase 2): format-tagged book concepts for the
        # critique/rewrite/polish loop. Failure or empty library → no doctrine,
        # generation proceeds unchanged.
        if settings.DOCTRINE_IN_GENERATION and wizard_type == "script_writer_wizard":
            config["_doctrine_cards"] = doctrine_service.build_doctrine_cards(
                template_id, db
            )

        result = await template_ai_service.wizard_generate(
            wizard_type=wizard_type,
            config=config,
            project_context=project_context,
            template_id=template_id,
        )

        # Phase 3: capture the critique/rewrite rubric scores BEFORE the review
        # middleware potentially replaces `result` with a schema-shaped merge
        # output (which drops non-schema keys like rubric_scores).
        rubric_scores = result.get("rubric_scores") if isinstance(result, dict) else None

        review_result = await agent_review_middleware.review_step_output(
            phase=phase,
            subsection_key=wizard_type,
            raw_output=result,
            owner_id=owner_id,
            session_factory=SessionLocal,
            wizard_type=wizard_type,
            continuity_context=continuity_context,
        )
        result = review_result["output"]

        if "_meta" not in result:
            result["_meta"] = {}
        result["_meta"]["agents_consulted"] = review_result["agents_consulted"]
        result["_meta"]["review_applied"] = review_result["review_applied"]
        # Phase 3: surface per-scene rubric scores (critique/rewrite loop) so the
        # frontend can show quality metrics. Present only for script_writer_wizard
        # runs with the critique loop enabled.
        if rubric_scores:
            result["_meta"]["rubric_scores"] = rubric_scores

        wizard_run.result = result
        wizard_run.status = "completed"
    except Exception as e:
        logger.error(f"Wizard background task failed ({wizard_type}): {e}")
        if wizard_run:
            wizard_run.status = "failed"
            wizard_run.error_message = str(e)
    finally:
        db.commit()
        db.close()


async def _run_season_map_background(run_id, config: dict, show_context: str):
    """Background task: generate the season map and update the WizardRun record.

    No agent-review middleware here (v1): the pipeline map has no season step,
    so the raw generation result is stored as-is.
    """
    db = SessionLocal()
    wizard_run = None
    try:
        wizard_run = db.query(database.WizardRun).filter(
            database.WizardRun.id == run_id
        ).first()
        wizard_run.status = "running"
        db.commit()

        # Craft doctrine: the season plans episodes of a series, so the deck is
        # the series-format canon (same gating flag as the script writer).
        if settings.DOCTRINE_IN_GENERATION:
            config["_doctrine_cards"] = doctrine_service.build_doctrine_cards("episode", db)

        result = await template_ai_service.generate_season_map(config, show_context)
        wizard_run.result = result
        wizard_run.status = "completed"
    except Exception as e:
        logger.error(f"Season map wizard background task failed: {e}")
        if wizard_run:
            wizard_run.status = "failed"
            wizard_run.error_message = str(e)
    finally:
        db.commit()
        db.close()


def _build_season_wizard_context(db: Session, season, show) -> str:
    """Series-level context string for the season map prompt: show + bible +
    continuity mode + this season's identity and current arc, if any."""
    parts = [f"**Show:** {show.title}"]
    if (show.description or "").strip():
        parts.append(show.description.strip())
    parts.append(f"**Continuity mode:** {show.continuity_mode}")
    if show.episode_duration_minutes:
        parts.append(f"**Target episode duration:** {show.episode_duration_minutes} minutes")
    bible_text = _build_bible_text(show)
    if bible_text:
        parts.append(bible_text)
    parts.append(f"\n**Planning:** Season {season.number}" + (f" — {season.title}" if (season.title or "").strip() else ""))
    if (season.arc_summary or "").strip():
        parts.append(f"Current season arc notes:\n{season.arc_summary.strip()}")
    return "\n".join(parts)


def _start_season_map_run(
    request: schemas.WizardRunRequest,
    background_tasks: BackgroundTasks,
    current_user: schemas.User,
    db: Session,
):
    """Season-scoped branch of run_wizard (Phase 4). Locked slots (episodes
    already linked) are passed to the prompt as canon anchors; their numbers
    are never regenerated."""
    if request.wizard_type != SEASON_MAP_WIZARD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {SEASON_MAP_WIZARD} runs season-scoped.",
        )
    season = _get_owned_season(db, request.season_id, current_user)
    show = db.query(database.Show).filter(database.Show.id == str(season.show_id)).first()

    config = dict(request.config)
    locked = []
    for slot in _season_slots(db, season.id):
        if not slot.project_id:
            continue
        project = db.query(database.Project).filter(
            database.Project.id == str(slot.project_id)
        ).first()
        locked.append({
            "slot_number": slot.slot_number,
            "title": slot.title or (project.title if project else ""),
            "logline": slot.logline or "",
            "episode_summary": (project.episode_summary or "").strip() if project else "",
        })
    config["_locked_slots"] = locked

    wizard_run = database.WizardRun(
        season_id=season.id,
        wizard_type=request.wizard_type,
        phase=request.phase,
        config=request.config,
        status="pending",
    )
    db.add(wizard_run)
    db.commit()
    db.refresh(wizard_run)

    background_tasks.add_task(
        _run_season_map_background,
        run_id=wizard_run.id,
        config=config,
        show_context=_build_season_wizard_context(db, season, show),
    )
    return wizard_run


@router.post("/run", response_model=schemas.WizardRunResponse)
async def run_wizard(
    request: schemas.WizardRunRequest,
    background_tasks: BackgroundTasks,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start a wizard run. Returns immediately; generation runs in the background."""
    # Phase 4 (temporadas): season-scoped runs take their own path; the schema
    # validator guarantees exactly one of project_id / season_id is set.
    if request.season_id:
        return _start_season_map_run(request, background_tasks, current_user, db)
    if request.wizard_type == SEASON_MAP_WIZARD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{SEASON_MAP_WIZARD} requires season_id, not project_id.",
        )

    project = db.query(database.Project).filter(
        database.Project.id == request.project_id,
        database.Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not project.template:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project has no template")

    # ESUM-03 lazy regen: in connected mode, regenerate any stale prior-episode
    # summaries BEFORE build_bible_context reads them, so the frozen bible_context
    # string sees fresh rows (Pitfall 2). Gated on connected mode; on per-prior AI
    # failure the flag stays True and Phase 68's stale-with-marker path degrades
    # gracefully (generation never fails). Must precede the build_bible_context call.
    # Phase 71 (SREV-01): connected-mode + script_writer_wizard review additionally
    # considers character/plot coherence against prior-episode summaries. We build the
    # block here (request session) and pass it across the background boundary as a plain
    # string — never an ORM object/live session (T-71-01). All other modes/wizards leave
    # continuity_context as None, so review runs byte-identical to today (D5).
    continuity_context = None
    if project.show_id:
        show = db.query(database.Show).filter(database.Show.id == str(project.show_id)).first()
        if show and show.continuity_mode == ContinuityMode.CONNECTED.value:
            await regenerate_stale_priors(db, show, project)
            if request.wizard_type == "script_writer_wizard":
                # Reuse Phase 68 helper: episode_number ASC, cap 8, stale-tagged,
                # freshly regenerated by the pre-pass above. Returns None when no priors.
                continuity_context = _build_prior_episodes_block(db, show, project)

    # Build bible context for episode projects (passed as string to background task)
    bible_context = build_bible_context(db, project)

    # Inject character data for scene and script-writer wizards before handing off to background
    config = dict(request.config)
    if request.wizard_type in ("scene_wizard", "script_writer_wizard"):
        config["_characters"] = _get_character_data(db, project.id)

    wizard_run = database.WizardRun(
        project_id=project.id,
        wizard_type=request.wizard_type,
        phase=request.phase,
        config=request.config,
        status="pending",
    )
    db.add(wizard_run)
    db.commit()
    db.refresh(wizard_run)

    background_tasks.add_task(
        _run_wizard_background,
        run_id=wizard_run.id,
        project_id=project.id,
        template_id=project.template.value,
        wizard_type=request.wizard_type,
        config=config,
        phase=request.phase,
        owner_id=str(current_user.id),
        bible_context=bible_context,
        continuity_context=continuity_context,
    )

    return wizard_run


@router.get("/{run_id}", response_model=schemas.WizardRunResponse)
async def get_wizard_run(
    run_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get wizard run status and results."""
    # str() — codebase convention: UUID columns are compared as strings so the
    # SQLite test engine (String(36) columns) matches Postgres behavior.
    wizard_run = db.query(database.WizardRun).filter(
        database.WizardRun.id == str(run_id)
    ).first()
    if not wizard_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wizard run not found")

    # Verify ownership (season runs resolve owner through Season -> Show).
    if wizard_run.season_id:
        _get_owned_season(db, wizard_run.season_id, current_user)
        return wizard_run

    project = db.query(database.Project).filter(
        database.Project.id == wizard_run.project_id,
        database.Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return wizard_run


@router.post("/{run_id}/apply")
async def apply_wizard_results(
    run_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Apply wizard results to project data (create list_items from generated episodes/scenes)."""
    wizard_run = db.query(database.WizardRun).filter(
        database.WizardRun.id == str(run_id)
    ).first()
    if not wizard_run or wizard_run.status != "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wizard run not found or not completed")

    # Phase 4 (temporadas): season map apply writes Season + slots.
    if wizard_run.season_id:
        season = _get_owned_season(db, wizard_run.season_id, current_user)
        return apply_season_map_to_db(db, season, wizard_run.result or {})

    project = db.query(database.Project).filter(
        database.Project.id == wizard_run.project_id,
        database.Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return apply_wizard_result_to_db(
        db, project, wizard_run.phase, wizard_run.wizard_type, wizard_run.result or {}
    )


def apply_season_map_to_db(db: Session, season, result: dict) -> dict:
    """Persist a season_map_wizard result: season.arc_summary + upsert slots.

    HARD RULE: slots linked to an episode project are NEVER touched or deleted.
    Re-running the wizard only rewrites/creates free slots; free slots whose
    number is absent from the new map are removed (the re-run replaces the free
    part of the map wholesale).
    """
    generated = result.get("slots", []) or []
    if not generated:
        return {"status": "success", "slots_written": 0, "message": "No slots to apply"}

    arc_summary = str(result.get("arc_summary", "") or "").strip()
    if arc_summary:
        season.arc_summary = arc_summary

    existing = {
        s.slot_number: s
        for s in db.query(database.EpisodeSlot)
        .filter(database.EpisodeSlot.season_id == str(season.id))
        .all()
    }
    linked_numbers = {n for n, s in existing.items() if s.project_id}

    written = 0
    generated_numbers = set()
    for entry in generated:
        try:
            slot_number = int(entry.get("slot_number"))
        except (TypeError, ValueError):
            continue
        if slot_number < 1 or slot_number in linked_numbers or slot_number in generated_numbers:
            continue
        generated_numbers.add(slot_number)

        states = entry.get("character_states")
        plan = {
            "title": str(entry.get("title", "") or ""),
            "logline": str(entry.get("logline", "") or ""),
            "arc_function": str(entry.get("arc_function", "") or ""),
            "character_states": (
                {str(k): str(v) for k, v in states.items()} if isinstance(states, dict) else {}
            ),
            "cliffhanger": str(entry.get("cliffhanger", "") or ""),
        }
        slot = existing.get(slot_number)
        if slot:
            for field, value in plan.items():
                setattr(slot, field, value)
            slot.plan_stale = False
        else:
            db.add(database.EpisodeSlot(season_id=season.id, slot_number=slot_number, **plan))
        written += 1

    deleted = 0
    for slot_number, slot in existing.items():
        if slot.project_id or slot_number in generated_numbers:
            continue
        db.delete(slot)
        deleted += 1

    db.commit()
    return {
        "status": "success",
        "slots_written": written,
        "slots_locked": len(linked_numbers),
        "slots_deleted": deleted,
    }


def apply_wizard_result_to_db(db: Session, project, phase: str, wizard_type: str, result: dict) -> dict:
    """Apply wizard generation results to the database. Reusable by both the apply endpoint and YOLO fill."""

    # Idea wizard: update PhaseData fields directly
    if wizard_type == "idea_wizard":
        fields = result.get("fields", {})
        if not fields:
            return {"status": "success", "message": "No fields to apply"}

        phase_data = db.query(database.PhaseData).filter(
            database.PhaseData.project_id == project.id,
            database.PhaseData.phase == phase,
            database.PhaseData.subsection_key == "idea_wizard",
        ).first()
        if not phase_data:
            phase_data = database.PhaseData(
                project_id=project.id,
                phase=phase,
                subsection_key="idea_wizard",
                content={},
            )
            db.add(phase_data)
            db.flush()

        existing = dict(phase_data.content or {})
        existing.update(fields)
        phase_data.content = existing
        flag_modified(phase_data, "content")
        db.commit()
        return {"status": "success", "fields_updated": list(fields.keys())}

    items_created = 0

    # Script writer wizard: store screenplays in ScreenplayContent + PhaseData
    if wizard_type == "script_writer_wizard":
        screenplays = result.get("screenplays", [])
        synopsis = result.get("synopsis", "")
        if not screenplays:
            return {"status": "success", "items_created": 0, "message": "No screenplays to apply"}

        phase_data = db.query(database.PhaseData).filter(
            database.PhaseData.project_id == project.id,
            database.PhaseData.phase == phase,
            database.PhaseData.subsection_key == "screenplay_editor"
        ).first()
        if not phase_data:
            phase_data = database.PhaseData(
                project_id=project.id,
                phase=phase,
                subsection_key="screenplay_editor",
                content={},
            )
            db.add(phase_data)
            db.flush()

        phase_data.content = {"screenplays": screenplays, "synopsis": synopsis}
        flag_modified(phase_data, "content")

        for sp in screenplays:
            sc = database.ScreenplayContent(
                project_id=project.id,
                content=sp.get("content", ""),
                formatted_content=sp,
            )
            db.add(sc)

        _mark_breakdown_stale(db, project.id)
        _mark_shotlist_stale(db, project.id)
        db.commit()
        return {"status": "success", "items_created": len(screenplays)}

    # Episode/scene wizard: create ListItem records
    if wizard_type == "scene_wizard":
        items_key = "scenes"
        item_type = "scene"
        subsection_key = "scene_list"
    else:
        return {"status": "success", "items_created": 0, "message": "No items to apply for this wizard type"}

    phase_data = db.query(database.PhaseData).filter(
        database.PhaseData.project_id == project.id,
        database.PhaseData.phase == phase,
        database.PhaseData.subsection_key == subsection_key
    ).first()
    if not phase_data:
        phase_data = database.PhaseData(
            project_id=project.id,
            phase=phase,
            subsection_key=subsection_key,
            content={},
        )
        db.add(phase_data)
        db.flush()

    existing_count = db.query(database.ListItem).filter(
        database.ListItem.phase_data_id == phase_data.id
    ).count()

    generated_items = result.get(items_key, [])
    for i, item_data in enumerate(generated_items):
        db_item = database.ListItem(
            phase_data_id=phase_data.id,
            item_type=item_type,
            sort_order=existing_count + i,
            content=item_data,
            status="draft"
        )
        db.add(db_item)
        items_created += 1

    _mark_breakdown_stale(db, project.id)
    _mark_shotlist_stale(db, project.id)
    db.commit()
    return {"status": "success", "items_created": items_created}


# ============================================================
# Phase 49 — Single-scene regenerate + keep (EVAL-01)
# ============================================================

def _scene_episodes_for_regen(db: Session, project_id) -> list:
    """Read the scene_list ListItems (phase=scenes, key=scene_list) ordered by
    sort_order into the `episodes` shape consumed by the script-writer path.

    Mirrors _get_character_data's query shape but for scenes. Each ListItem maps
    to {"item_type": ..., **content} so the regenerate prompt's scene data and
    summary match what _generate_scripts saw at batch time.
    """
    scenes_pd = db.query(database.PhaseData).filter(
        database.PhaseData.project_id == project_id,
        database.PhaseData.phase == "scenes",
        database.PhaseData.subsection_key == "scene_list",
    ).first()
    if not scenes_pd:
        return []
    items = db.query(database.ListItem).filter(
        database.ListItem.phase_data_id == scenes_pd.id
    ).order_by(database.ListItem.sort_order).all()
    return [{"item_type": li.item_type, **(li.content or {})} for li in items]


def _latest_script_wizard_config(db: Session, project_id) -> dict:
    """Best-effort: pull runtime_target / custom_guidance from the most recent
    script_writer_wizard WizardRun config, if one exists. Returns {} otherwise."""
    run = db.query(database.WizardRun).filter(
        database.WizardRun.project_id == project_id,
        database.WizardRun.wizard_type == "script_writer_wizard",
    ).order_by(database.WizardRun.created_at.desc()).first()
    return dict(run.config or {}) if run else {}


@router.post("/regenerate-scene", response_model=schemas.RegenerateSceneResponse)
async def regenerate_scene(
    request: schemas.RegenerateSceneRequest,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Regenerate ONE scene by episode_index via the improved phases 45-48 path and
    return it as a PREVIEW. Writes NOTHING to the store (D-49-02).

    Owner-scoped (404 for a non-owner), mirroring run_wizard.

    NOTE: this is a SYNCHRONOUS LLM call (max_tokens=4000) and may exceed the
    30s default API timeout. The FRONTEND calls it with CHAT_TIMEOUT (120s) per
    49-02; we intentionally do NOT add background-task plumbing for a single scene.

    ALIGNMENT ASSUMPTION (D-49-03): episode_index indexes BOTH the sort_order-ordered
    scene_list (episodes) AND screenplays[] 1:1 — the same implicit contract the
    breakdown/shotlist pipeline already relies on. We bounds-check it below.
    """
    project = db.query(database.Project).filter(
        database.Project.id == str(request.project_id),
        database.Project.owner_id == str(current_user.id)
    ).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    bible_context = build_bible_context(db, project)
    project_context = _get_project_context(db, project, bible_context=bible_context)

    # Build the regenerate config: scene inputs + characters + carried runtime/guidance.
    episodes = _scene_episodes_for_regen(db, project.id)
    if not (0 <= request.episode_index < len(episodes)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"episode_index {request.episode_index} out of range",
        )
    prior_config = _latest_script_wizard_config(db, project.id)
    config = {
        "episodes": episodes,
        "_characters": _get_character_data(db, project.id),
        "runtime_target": prior_config.get("runtime_target", ""),
        "custom_guidance": prior_config.get("custom_guidance", ""),
    }

    # Source continuity inputs from the stored screenplay_editor content.
    sp_pd = db.query(database.PhaseData).filter(
        database.PhaseData.project_id == project.id,
        database.PhaseData.phase == request.phase,
        database.PhaseData.subsection_key == "screenplay_editor",
    ).first()
    sp_content = dict(sp_pd.content or {}) if sp_pd else {}
    synopsis = sp_content.get("synopsis", "")
    screenplays = sp_content.get("screenplays", [])
    prev_scene_text = ""
    if request.episode_index > 0 and request.episode_index - 1 < len(screenplays):
        prev_scene_text = (screenplays[request.episode_index - 1] or {}).get("content", "")

    result = await template_ai_service.regenerate_single_scene(
        config, project_context, request.episode_index, synopsis, prev_scene_text
    )
    # FastAPI coerces the dict to RegenerateSceneResponse. No DB write (D-49-02).
    return result


@router.post("/keep-scene-version")
async def keep_scene_version(
    request: schemas.KeepSceneVersionRequest,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Persist the chosen scene version into screenplays[episode_index] in the
    screenplay_editor PhaseData.content AND the matching ScreenplayContent row,
    then mark breakdown + shotlist stale (keep-new ONLY — D-49-02).

    The global running synopsis is left UNTOUCHED (D-49-05). Owner-scoped (404).
    """
    project = db.query(database.Project).filter(
        database.Project.id == str(request.project_id),
        database.Project.owner_id == str(current_user.id)
    ).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    phase_data = db.query(database.PhaseData).filter(
        database.PhaseData.project_id == project.id,
        database.PhaseData.phase == request.phase,
        database.PhaseData.subsection_key == "screenplay_editor",
    ).first()
    if not phase_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No screenplay to update")

    content = dict(phase_data.content or {})
    screenplays = list(content.get("screenplays", []))
    if not (0 <= request.episode_index < len(screenplays)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"episode_index {request.episode_index} out of range",
        )

    new_slot = {
        "title": request.title,
        "content": request.content,
        "episode_index": request.episode_index,
    }
    screenplays[request.episode_index] = new_slot
    content["screenplays"] = screenplays  # leave content["synopsis"] untouched (D-49-05)
    phase_data.content = content
    flag_modified(phase_data, "content")

    # Update the matching ScreenplayContent row. The batch-generate path appends
    # rows and never deletes them (see apply_wizard_result_to_db), so a project
    # that has been re-generated can hold duplicate rows per episode_index. Order
    # NEWEST-first and take the most recent match so the kept version aligns with
    # the latest generation that the breakdown/shotlist services also read — not a
    # stale earlier row (WR-01). Prefer matching by the stored
    # formatted_content.episode_index; fall back to stable ordering when no row
    # carries the index (NO migration — D-49-03).
    rows = db.query(database.ScreenplayContent).filter(
        database.ScreenplayContent.project_id == project.id
    ).order_by(
        database.ScreenplayContent.created_at.desc(), database.ScreenplayContent.id.desc()
    ).all()
    target = next(
        (r for r in rows if (r.formatted_content or {}).get("episode_index") == request.episode_index),
        None,
    )
    if target is None and request.episode_index < len(rows):
        # rows is newest-first; index from the end to keep positional alignment
        # with the original ascending order.
        target = rows[len(rows) - 1 - request.episode_index]
    if target is not None:
        target.content = request.content
        target.formatted_content = new_slot

    _mark_breakdown_stale(db, project.id)
    _mark_shotlist_stale(db, project.id)
    db.commit()
    return {"status": "success", "episode_index": request.episode_index}
