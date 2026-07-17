import enum
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from ...models import schemas, database
from ..dependencies import get_db, get_current_user
from ...exceptions import NotFoundException
from ...templates import get_template, get_template_subsections
from ...services.vapai_service import vapai_service
from ...services.template_ai_service import _read_episode_text_by_index

router = APIRouter()


@router.post("/", response_model=schemas.ShowResponse, status_code=status.HTTP_201_CREATED)
async def create_show(
    body: schemas.ShowCreate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new show."""
    db_show = database.Show(
        title=body.title,
        description=body.description,
        continuity_mode=body.continuity_mode.value,
        owner_id=str(current_user.id),
    )
    db.add(db_show)
    db.commit()
    db.refresh(db_show)
    return db_show


@router.get("/", response_model=List[schemas.ShowResponse])
async def list_shows(
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all shows for the current user."""
    return (
        db.query(database.Show)
        .filter(database.Show.owner_id == str(current_user.id))
        .order_by(database.Show.created_at.desc())
        .all()
    )


@router.get("/{show_id}", response_model=schemas.ShowResponse)
async def get_show(
    show_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single show by ID."""
    show = (
        db.query(database.Show)
        .filter(database.Show.id == str(show_id), database.Show.owner_id == str(current_user.id))
        .first()
    )
    if not show:
        raise NotFoundException(resource="Show", identifier=str(show_id))
    return show


@router.put("/{show_id}", response_model=schemas.ShowResponse)
async def update_show(
    show_id: UUID,
    body: schemas.ShowUpdate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a show's title and/or description."""
    show = (
        db.query(database.Show)
        .filter(database.Show.id == str(show_id), database.Show.owner_id == str(current_user.id))
        .first()
    )
    if not show:
        raise NotFoundException(resource="Show", identifier=str(show_id))
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        # Coerce Enum members (e.g. continuity_mode) to their string value so
        # the VARCHAR column stores "standalone", not "ContinuityMode.STANDALONE".
        if isinstance(value, enum.Enum):
            value = value.value
        setattr(show, field, value)
    db.commit()
    db.refresh(show)
    return show


@router.delete("/{show_id}")
async def delete_show(
    show_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a show."""
    show = (
        db.query(database.Show)
        .filter(database.Show.id == str(show_id), database.Show.owner_id == str(current_user.id))
        .first()
    )
    if not show:
        raise NotFoundException(resource="Show", identifier=str(show_id))
    db.delete(show)
    db.commit()
    return {"status": "success", "message": "Show deleted"}


@router.get("/{show_id}/bible", response_model=schemas.BibleResponse)
async def get_bible(
    show_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get bible sections and episode duration for a show."""
    show = (
        db.query(database.Show)
        .filter(database.Show.id == str(show_id), database.Show.owner_id == str(current_user.id))
        .first()
    )
    if not show:
        raise NotFoundException(resource="Show", identifier=str(show_id))
    return schemas.BibleResponse(
        show_id=show.id,
        bible_characters=show.bible_characters or "",
        bible_world_setting=show.bible_world_setting or "",
        bible_season_arc=show.bible_season_arc or "",
        bible_tone_style=show.bible_tone_style or "",
        bible_central_premise=show.bible_central_premise or "",
        bible_story_engine=show.bible_story_engine or "",
        bible_series_questions=show.bible_series_questions or "",
        episode_duration_minutes=show.episode_duration_minutes,
    )


@router.put("/{show_id}/bible", response_model=schemas.BibleResponse)
async def update_bible(
    show_id: UUID,
    body: schemas.BibleUpdate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update bible sections and/or episode duration for a show."""
    show = (
        db.query(database.Show)
        .filter(database.Show.id == str(show_id), database.Show.owner_id == str(current_user.id))
        .first()
    )
    if not show:
        raise NotFoundException(resource="Show", identifier=str(show_id))
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(show, field, value)
    db.commit()
    db.refresh(show)
    return schemas.BibleResponse(
        show_id=show.id,
        bible_characters=show.bible_characters or "",
        bible_world_setting=show.bible_world_setting or "",
        bible_season_arc=show.bible_season_arc or "",
        bible_tone_style=show.bible_tone_style or "",
        bible_central_premise=show.bible_central_premise or "",
        bible_story_engine=show.bible_story_engine or "",
        bible_series_questions=show.bible_series_questions or "",
        episode_duration_minutes=show.episode_duration_minutes,
    )


@router.get("/{show_id}/episodes", response_model=List[schemas.Project])
async def list_episodes(
    show_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all episodes for a show, ordered by episode number."""
    show = (
        db.query(database.Show)
        .filter(database.Show.id == str(show_id), database.Show.owner_id == str(current_user.id))
        .first()
    )
    if not show:
        raise NotFoundException(resource="Show", identifier=str(show_id))
    return (
        db.query(database.Project)
        .filter(database.Project.show_id == str(show_id))
        .order_by(database.Project.episode_number.asc())
        .all()
    )


@router.post("/{show_id}/episodes", response_model=schemas.Project, status_code=status.HTTP_201_CREATED)
async def create_episode(
    show_id: UUID,
    body: schemas.EpisodeCreate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new episode (project) under a show."""
    # 1. Verify show exists and is owned by user
    show = (
        db.query(database.Show)
        .filter(database.Show.id == str(show_id), database.Show.owner_id == str(current_user.id))
        .first()
    )
    if not show:
        raise NotFoundException(resource="Show", identifier=str(show_id))

    # 2. Auto-calculate episode number if not provided
    episode_number = body.episode_number
    if episode_number is None:
        max_num = (
            db.query(func.max(database.Project.episode_number))
            .filter(database.Project.show_id == str(show_id))
            .scalar()
        )
        episode_number = (max_num or 0) + 1

    # 3. Validate the template (episodes are template-based, like films — the
    # legacy/classic framework flow is no longer offered).
    try:
        get_template(body.template.value)
    except ValueError:
        raise NotFoundException(resource="Template", identifier=str(body.template.value))

    # 4. Create the episode project with show linkage, scaffolding phase_data the
    # same way create_project_v2 does for standalone films.
    db_project = database.Project(
        title=body.title,
        template=body.template,
        current_phase=database.PhaseType.IDEA,
        show_id=str(show_id),
        episode_number=episode_number,
        owner_id=str(current_user.id),
    )
    db.add(db_project)
    db.flush()

    # 5. Auto-create phase_data rows for all subsections in the template.
    for sub in get_template_subsections(body.template.value):
        db.add(database.PhaseData(
            project_id=db_project.id,
            phase=sub["phase"],
            subsection_key=sub["subsection_key"],
            sort_order=sub["sort_order"],
            content={},
            ai_suggestions={},
        ))

    db.commit()
    db.refresh(db_project)
    return db_project


def _build_bible_text(show: "database.Show") -> str:
    """Concatenate the show's non-empty bible fields into one labeled block."""
    sections = [
        ("Central Premise", show.bible_central_premise),
        ("Story Engine", show.bible_story_engine),
        ("Series Questions", show.bible_series_questions),
        ("Characters", show.bible_characters),
        ("World / Setting", show.bible_world_setting),
        ("Season Arc", show.bible_season_arc),
        ("Tone / Style", show.bible_tone_style),
    ]
    parts = [f"## {label}\n{value.strip()}" for label, value in sections if (value or "").strip()]
    return "\n\n".join(parts)


@router.post("/{show_id}/send-to-vapai")
async def send_series_to_vapai(
    show_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Push the whole series (show + all episodes) to vapai-studio as one project
    (type="series"). Each episode becomes a vapai episode; episodes with a
    screenplay also get a script (empty ones are created without one). The show
    bible is sent to the vapai project. Owner-scoped (404 if not owned), 400 if
    the show has no episodes, 424 unconfigured, 502 on downstream failure.

    Idempotent: reuses show.vapai_project_id and each episode's persisted
    vapai_episode_id on re-send, then persists any newly returned ids.
    """
    show = (
        db.query(database.Show)
        .filter(database.Show.id == str(show_id), database.Show.owner_id == str(current_user.id))
        .first()
    )
    if not show:
        raise NotFoundException(resource="Show", identifier=str(show_id))

    episode_projects = (
        db.query(database.Project)
        .filter(database.Project.show_id == str(show_id))
        .order_by(database.Project.episode_number.asc())
        .all()
    )
    if not episode_projects:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This show has no episodes to send.",
        )

    episodes_payload = [
        {
            "episode_number": ep.episode_number or (i + 1),
            "title": ep.title,
            "fountain_text": _read_episode_text_by_index(db, ep.id),
            "vapai_episode_id": ep.vapai_episode_id,
        }
        for i, ep in enumerate(episode_projects)
    ]

    result = await vapai_service.send_series(
        series_title=show.title,
        bible_text=_build_bible_text(show),
        episodes=episodes_payload,
        existing_project_id=show.vapai_project_id,
    )

    # Persist linkage: the series project on the show, and each episode's vapai
    # ids on its Project (keeps per-episode and per-series re-send consistent).
    show.vapai_project_id = result["vapai_project_id"]
    by_number = {r["episode_number"]: r for r in result["episodes"]}
    for i, ep in enumerate(episode_projects):
        r = by_number.get(ep.episode_number or (i + 1))
        if r:
            ep.vapai_project_id = result["vapai_project_id"]
            ep.vapai_episode_id = r["vapai_episode_id"]
    db.commit()

    return result
