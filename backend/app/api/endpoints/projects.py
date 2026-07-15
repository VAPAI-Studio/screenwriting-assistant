# backend/app/api/endpoints/projects.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from uuid import UUID

from ...models import schemas, database
from ..dependencies import get_db, get_current_user
from ...utils import validate_project_title, validate_framework
from ...exceptions import NotFoundException, ValidationException
from ...templates import get_template, get_template_subsections
from ...services.template_ai_service import template_ai_service, _read_episode_text_by_index
from ...services.vapai_service import vapai_service
from ...utils.episode_summary import mark_linked_slot_plan_stale
from .shows import _build_bible_text

router = APIRouter()

@router.post("/", response_model=schemas.Project)
async def create_project(
    project: schemas.ProjectCreate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new project"""
    # Validate project title
    validate_project_title(project.title)
    
    # Validate framework
    if not validate_framework(project.framework.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid framework selected"
        )
    
    db_project = database.Project(
        **project.dict(),
        owner_id=current_user.id
    )
    db.add(db_project)
    db.flush()  # Assigns db_project.id without committing

    # Create default sections based on framework
    section_types = [
        database.SectionType.INCITING_INCIDENT,
        database.SectionType.PLOT_POINT_1,
        database.SectionType.MIDPOINT,
        database.SectionType.PLOT_POINT_2,
        database.SectionType.CLIMAX,
        database.SectionType.RESOLUTION
    ]
    
    for section_type in section_types:
        db_section = database.Section(
            project_id=db_project.id,
            type=section_type,
            ai_suggestions={"issues": [], "suggestions": []}
        )
        db.add(db_section)
    
    db.commit()
    db.refresh(db_project)
    
    return db_project

@router.post("/v2", response_model=schemas.ProjectResponseV2)
async def create_project_v2(
    project: schemas.ProjectCreateV2,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new template-based project with auto-scaffolded phase data."""
    validate_project_title(project.title)

    # Validate template exists
    try:
        template_config = get_template(project.template.value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid template: {project.template.value}"
        )

    db_project = database.Project(
        title=project.title,
        template=project.template,
        current_phase=database.PhaseType.IDEA,
        owner_id=current_user.id
    )
    db.add(db_project)
    db.flush()

    # Auto-create phase_data rows for all subsections in the template
    subsections = get_template_subsections(project.template.value)
    for sub in subsections:
        pd = database.PhaseData(
            project_id=db_project.id,
            phase=sub["phase"],
            subsection_key=sub["subsection_key"],
            sort_order=sub["sort_order"],
            content={},
            ai_suggestions={},
        )
        db.add(pd)

    db.commit()
    db.refresh(db_project)
    return db_project


@router.get("/", response_model=List[schemas.Project])
async def list_projects(
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List the user's standalone projects (Films).

    Episodes are Projects with a show_id and are listed under their show via
    GET /api/shows/{id}/episodes — exclude them here so they don't show up as
    standalone films.
    """
    projects = db.query(database.Project).options(
        joinedload(database.Project.sections)
            .joinedload(database.Section.checklist_items)
    ).filter(
        database.Project.owner_id == current_user.id,
        database.Project.show_id.is_(None),
    ).order_by(database.Project.created_at.desc()).all()

    return projects

@router.get("/{project_id}", response_model=schemas.Project)
async def get_project(
    project_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific project"""
    project = db.query(database.Project).options(
        joinedload(database.Project.sections)
            .joinedload(database.Section.checklist_items)
    ).filter(
        database.Project.id == project_id,
        database.Project.owner_id == current_user.id
    ).first()

    if not project:
        raise NotFoundException(resource="Project", identifier=str(project_id))

    return project

@router.post("/{project_id}/episode-summary")
async def generate_episode_summary(
    project_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """ESUM-01: eager "complete episode" trigger.

    Generate a bounded prose episode_summary from the project's screenplay text and
    persist it (clearing episode_summary_stale). Owner-scoped: a project not owned by
    the caller returns 404 (no cross-user read/write — threat T-69-01).

    Empty-source choice (documented): if the summarizer returns "" (no screenplay
    text to summarize), return 422 and DO NOT clobber an existing summary with empty.

    The summarizer (template_ai_service.summarize_episode) does NOT commit — this
    endpoint owns the write + commit (Phase 67 caller-commits convention). The
    episode_summary TEXT is intentionally NOT surfaced on the Project read schema
    (Phase 67 D-04 — threat T-69-02); this endpoint returns only the owner's status.
    """
    project = db.query(database.Project).filter(
        database.Project.id == str(project_id),
        database.Project.owner_id == str(current_user.id),
    ).first()

    if not project:
        raise NotFoundException(resource="Project", identifier=str(project_id))

    summary = await template_ai_service.summarize_episode(db, project)
    if not summary:
        # No source text to summarize — do not overwrite an existing summary.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No screenplay text available to summarize for this episode.",
        )

    project.episode_summary = summary
    project.episode_summary_stale = False
    # Phase 4 (temporadas): a fresh summary means the written episode may have
    # diverged from its season-map slot plan — surface the reconcile badge.
    mark_linked_slot_plan_stale(db, project.id)
    db.commit()

    return {"status": "success", "episode_summary_stale": False}

@router.post("/{project_id}/send-to-vapai")
async def send_to_vapai(
    project_id: UUID,
    scope: Optional[str] = Query(
        None,
        description="For episodes of a series: 'series' sends this episode into the "
        "series project; 'standalone' sends it as its own project. Ignored for "
        "non-series projects. Omit on a series episode to get a 409 asking to choose.",
    ),
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Push this project's completed screenplay into vapai-studio.

    Creates a project + episode + script over there (breakdown is NOT triggered —
    the user runs it inside vapai). Owner-scoped: a project not owned by the caller
    returns 404. Returns 400 if there is no screenplay text yet, 424 if the
    integration is unconfigured, 502 on a downstream vapai failure.

    Series episodes (project.show_id set): the caller must pass ?scope=series (send
    this episode INTO the show's one vapai series project, with bible + episode
    number) or ?scope=standalone (send it as its own project, the legacy behavior).
    Omitting scope on a series episode returns 409 with is_series_episode=true so the
    UI can offer the choice. Non-series projects ignore scope and send standalone.

    Idempotency: the returned vapai project/episode ids are persisted so a re-send
    adds a new script under the same vapai project/episode instead of duplicating.
    """
    project = db.query(database.Project).filter(
        database.Project.id == str(project_id),
        database.Project.owner_id == str(current_user.id),
    ).first()

    if not project:
        raise NotFoundException(resource="Project", identifier=str(project_id))

    text = _read_episode_text_by_index(db, project_id)
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No screenplay content to send. Write or generate the screenplay first.",
        )

    if scope not in (None, "series", "standalone"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="scope must be 'series' or 'standalone'.",
        )

    is_series_episode = bool(project.show_id)

    # A series episode with no explicit choice: ask the UI to pick (don't silently
    # send it as a standalone project, which loses the series grouping + bible).
    if is_series_episode and scope is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "This episode belongs to a series. Choose whether to send "
                "just this episode into the series, or the whole series.",
                "is_series_episode": True,
                "show_id": str(project.show_id),
            },
        )

    if is_series_episode and scope == "series":
        # Send this episode INTO the show's single vapai series project.
        show = db.query(database.Show).filter(
            database.Show.id == str(project.show_id),
            database.Show.owner_id == str(current_user.id),
        ).first()
        if not show:
            raise NotFoundException(resource="Show", identifier=str(project.show_id))

        result = await vapai_service.send_episode_within_series(
            series_title=show.title,
            bible_text=_build_bible_text(show),
            episode_number=project.episode_number or 1,
            episode_title=project.title,
            fountain_text=text,
            existing_project_id=show.vapai_project_id,
            existing_episode_id=project.vapai_episode_id,
        )
        # Persist linkage on BOTH the show (series project) and this episode.
        show.vapai_project_id = result["vapai_project_id"]
        project.vapai_project_id = result["vapai_project_id"]
        project.vapai_episode_id = result["vapai_episode_id"]
        db.commit()
        return result

    # Standalone: either a non-series project, or a series episode the user
    # explicitly chose to send on its own.
    result = await vapai_service.send_screenplay(
        title=project.title,
        fountain_text=text,
        existing_project_id=project.vapai_project_id,
        existing_episode_id=project.vapai_episode_id,
        episode_number=project.episode_number or 1,
    )

    project.vapai_project_id = result["vapai_project_id"]
    project.vapai_episode_id = result["vapai_episode_id"]
    db.commit()

    return result

@router.patch("/{project_id}", response_model=schemas.Project)
async def update_project(
    project_id: UUID,
    project_update: schemas.ProjectUpdate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a project"""
    project = db.query(database.Project).filter(
        database.Project.id == project_id,
        database.Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    update_data = project_update.dict(exclude_unset=True)
    
    # Validate title if it's being updated
    if 'title' in update_data and update_data['title'] is not None:
        validate_project_title(update_data['title'])
    
    # Validate framework if it's being updated
    if 'framework' in update_data and update_data['framework'] is not None:
        if not validate_framework(update_data['framework'].value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid framework selected"
            )
    
    for field, value in update_data.items():
        setattr(project, field, value)
    
    db.commit()
    db.refresh(project)
    
    return project

@router.delete("/{project_id}")
async def delete_project(
    project_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a project"""
    project = db.query(database.Project).filter(
        database.Project.id == project_id,
        database.Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    db.delete(project)
    db.commit()

    return {"status": "success", "message": "Project deleted"}


@router.get("/{project_id}/episode-context")
async def get_episode_context(
    project_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Read-only view of the global data an episode carries: the show's bible and
    (in connected mode) the prior episodes' summaries. Returns is_episode=False for
    standalone films so the UI can hide the panel.
    """
    project = (
        db.query(database.Project)
        .filter(
            database.Project.id == str(project_id),
            database.Project.owner_id == current_user.id,
        )
        .first()
    )
    if not project:
        raise NotFoundException(resource="Project", identifier=str(project_id))

    if not project.show_id:
        return {"is_episode": False}

    show = db.query(database.Show).filter(database.Show.id == str(project.show_id)).first()
    if not show:
        return {"is_episode": False}

    mode = show.continuity_mode or "anthology"

    bible = {
        "characters": show.bible_characters or "",
        "world_setting": show.bible_world_setting or "",
        "season_arc": show.bible_season_arc or "",
        "tone_style": show.bible_tone_style or "",
        "episode_duration_minutes": show.episode_duration_minutes,
    }

    # Prior episodes (connected mode only) — strictly-prior, ordered by episode_number.
    prior_episodes = []
    if mode == schemas.ContinuityMode.CONNECTED.value and project.episode_number is not None:
        priors = (
            db.query(database.Project)
            .filter(
                database.Project.show_id == str(show.id),
                database.Project.episode_number < project.episode_number,
                database.Project.episode_summary.isnot(None),
            )
            .order_by(database.Project.episode_number.asc())
            .all()
        )
        for p in priors:
            summary = (p.episode_summary or "").strip()
            if not summary:
                continue
            prior_episodes.append({
                "episode_number": p.episode_number,
                "title": p.title,
                "summary": summary,
                "stale": bool(p.episode_summary_stale),
            })

    return {
        "is_episode": True,
        "show_id": str(show.id),
        "show_title": show.title,
        "continuity_mode": mode,
        "episode_number": project.episode_number,
        "bible": bible,
        "prior_episodes": prior_episodes,
    }
