# backend/app/api/endpoints/seasons.py

"""Season layer endpoints (Phase 4 -- capa de temporada).

Routes are registered under the bare /api prefix (see main.py) because the
resource nests two ways: seasons under /shows/{id}/seasons, and season/slot
operations under /seasons/{id} and /slots/{id}.

Ownership: seasons and slots have no owner_id of their own -- ownership is
always resolved through the parent Show (owner-scoped 404, same convention as
shows.py).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List, Tuple
from uuid import UUID

from ...models import schemas, database
from ..dependencies import get_db, get_current_user
from ...exceptions import NotFoundException
from ...templates import get_template, get_template_subsections
from ...services.template_ai_service import template_ai_service

router = APIRouter()


def _get_owned_show(db: Session, show_id, current_user) -> database.Show:
    show = (
        db.query(database.Show)
        .filter(database.Show.id == str(show_id), database.Show.owner_id == str(current_user.id))
        .first()
    )
    if not show:
        raise NotFoundException(resource="Show", identifier=str(show_id))
    return show


def _get_owned_season(db: Session, season_id, current_user) -> database.Season:
    season = (
        db.query(database.Season)
        .join(database.Show, database.Season.show_id == database.Show.id)
        .filter(
            database.Season.id == str(season_id),
            database.Show.owner_id == str(current_user.id),
        )
        .first()
    )
    if not season:
        raise NotFoundException(resource="Season", identifier=str(season_id))
    return season


def _get_owned_slot(db: Session, slot_id, current_user) -> Tuple[database.EpisodeSlot, database.Season]:
    row = (
        db.query(database.EpisodeSlot, database.Season)
        .join(database.Season, database.EpisodeSlot.season_id == database.Season.id)
        .join(database.Show, database.Season.show_id == database.Show.id)
        .filter(
            database.EpisodeSlot.id == str(slot_id),
            database.Show.owner_id == str(current_user.id),
        )
        .first()
    )
    if not row:
        raise NotFoundException(resource="EpisodeSlot", identifier=str(slot_id))
    return row


def _season_slots(db: Session, season_id) -> List[database.EpisodeSlot]:
    return (
        db.query(database.EpisodeSlot)
        .filter(database.EpisodeSlot.season_id == str(season_id))
        .order_by(database.EpisodeSlot.slot_number.asc())
        .all()
    )


def _season_detail(db: Session, season: database.Season) -> schemas.SeasonDetailResponse:
    detail = schemas.SeasonDetailResponse.model_validate(season)
    detail.slots = [
        schemas.EpisodeSlotResponse.model_validate(s) for s in _season_slots(db, season.id)
    ]
    return detail


# ============================================================
# Seasons
# ============================================================

@router.get("/shows/{show_id}/seasons", response_model=List[schemas.SeasonResponse])
async def list_seasons(
    show_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List a show's seasons ordered by number."""
    _get_owned_show(db, show_id, current_user)
    return (
        db.query(database.Season)
        .filter(database.Season.show_id == str(show_id))
        .order_by(database.Season.number.asc())
        .all()
    )


@router.post("/shows/{show_id}/seasons", response_model=schemas.SeasonResponse, status_code=status.HTTP_201_CREATED)
async def create_season(
    show_id: UUID,
    body: schemas.SeasonCreate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a season; number auto-increments per show when omitted."""
    _get_owned_show(db, show_id, current_user)

    number = body.number
    if number is None:
        max_num = (
            db.query(func.max(database.Season.number))
            .filter(database.Season.show_id == str(show_id))
            .scalar()
        )
        number = (max_num or 0) + 1
    else:
        exists = (
            db.query(database.Season)
            .filter(database.Season.show_id == str(show_id), database.Season.number == number)
            .first()
        )
        if exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Season {number} already exists for this show.",
            )

    season = database.Season(
        show_id=str(show_id),
        number=number,
        title=body.title or f"Season {number}",
        arc_summary=body.arc_summary,
    )
    db.add(season)
    db.commit()
    db.refresh(season)
    return season


@router.get("/seasons/{season_id}", response_model=schemas.SeasonDetailResponse)
async def get_season(
    season_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a season with its slots ordered by slot_number."""
    season = _get_owned_season(db, season_id, current_user)
    return _season_detail(db, season)


@router.put("/seasons/{season_id}", response_model=schemas.SeasonResponse)
async def update_season(
    season_id: UUID,
    body: schemas.SeasonUpdate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    season = _get_owned_season(db, season_id, current_user)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(season, field, value)
    db.commit()
    db.refresh(season)
    return season


@router.delete("/seasons/{season_id}")
async def delete_season(
    season_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a season and its slots. Episode projects survive (season_id -> NULL)."""
    season = _get_owned_season(db, season_id, current_user)
    # ondelete=SET NULL is a Postgres-level rule; the SQLite test engine created by
    # create_all doesn't enforce it, so clear the FK explicitly for both engines.
    db.query(database.Project).filter(
        database.Project.season_id == str(season_id)
    ).update({database.Project.season_id: None}, synchronize_session=False)
    db.delete(season)
    db.commit()
    return {"status": "success", "message": "Season deleted"}


# ============================================================
# Episode slots
# ============================================================

@router.post("/seasons/{season_id}/slots", response_model=schemas.EpisodeSlotResponse, status_code=status.HTTP_201_CREATED)
async def create_slot(
    season_id: UUID,
    body: schemas.EpisodeSlotCreate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a slot; slot_number auto-increments per season when omitted."""
    season = _get_owned_season(db, season_id, current_user)

    slot_number = body.slot_number
    if slot_number is None:
        max_num = (
            db.query(func.max(database.EpisodeSlot.slot_number))
            .filter(database.EpisodeSlot.season_id == str(season.id))
            .scalar()
        )
        slot_number = (max_num or 0) + 1
    else:
        exists = (
            db.query(database.EpisodeSlot)
            .filter(
                database.EpisodeSlot.season_id == str(season.id),
                database.EpisodeSlot.slot_number == slot_number,
            )
            .first()
        )
        if exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Slot {slot_number} already exists in this season.",
            )

    slot = database.EpisodeSlot(
        season_id=str(season.id),
        slot_number=slot_number,
        title=body.title,
        logline=body.logline,
        arc_function=body.arc_function,
        character_states=body.character_states,
        cliffhanger=body.cliffhanger,
        notes=body.notes,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


@router.put("/slots/{slot_id}", response_model=schemas.EpisodeSlotResponse)
async def update_slot(
    slot_id: UUID,
    body: schemas.EpisodeSlotUpdate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    slot, season = _get_owned_slot(db, slot_id, current_user)
    update_data = body.model_dump(exclude_unset=True)

    # Manual episode assignment (explicit null unlinks). The slot is the PLAN;
    # linking adopts an already-created episode as its written reality.
    if "project_id" in update_data:
        new_project_id = update_data.pop("project_id")
        if new_project_id is None:
            slot.project_id = None
        else:
            episode = (
                db.query(database.Project)
                .filter(
                    database.Project.id == str(new_project_id),
                    database.Project.owner_id == str(current_user.id),
                )
                .first()
            )
            if not episode:
                raise NotFoundException(resource="Episode", identifier=str(new_project_id))
            if str(episode.show_id or "") != str(season.show_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="That episode belongs to a different show.",
                )
            taken = (
                db.query(database.EpisodeSlot)
                .filter(
                    database.EpisodeSlot.project_id == str(new_project_id),
                    database.EpisodeSlot.id != str(slot.id),
                )
                .first()
            )
            if taken:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"That episode is already assigned to slot {taken.slot_number}.",
                )
            slot.project_id = str(new_project_id)
            # Same linkage create-episode-from-slot establishes.
            episode.season_id = str(season.id)

    new_number = update_data.get("slot_number")
    if new_number is not None and new_number != slot.slot_number:
        exists = (
            db.query(database.EpisodeSlot)
            .filter(
                database.EpisodeSlot.season_id == str(season.id),
                database.EpisodeSlot.slot_number == new_number,
            )
            .first()
        )
        if exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Slot {new_number} already exists in this season.",
            )

    for field, value in update_data.items():
        setattr(slot, field, value)
    db.commit()
    db.refresh(slot)
    return slot


@router.delete("/slots/{slot_id}")
async def delete_slot(
    slot_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a slot. A linked episode project survives, simply unslotted."""
    slot, _season = _get_owned_slot(db, slot_id, current_user)
    db.delete(slot)
    db.commit()
    return {"status": "success", "message": "Slot deleted"}


# ============================================================
# Episodes are born from slots
# ============================================================

@router.post("/slots/{slot_id}/create-episode", response_model=schemas.Project, status_code=status.HTTP_201_CREATED)
async def create_episode_from_slot(
    slot_id: UUID,
    body: schemas.SlotCreateEpisodeRequest,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create the episode project for a slot and link them.

    episode_number is GLOBAL per show, derived from narrative position:
    (slot count of prior seasons) + slot_number -- so connected-mode continuity
    (ordered by episode_number) stays correct even when slots are written out
    of order. The slot plan is NOT copied into phase_data; it is injected as
    generation context by build_bible_context.
    """
    slot, season = _get_owned_slot(db, slot_id, current_user)
    if slot.project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This slot already has an episode.",
        )

    try:
        get_template(body.template.value)
    except ValueError:
        raise NotFoundException(resource="Template", identifier=str(body.template.value))

    prior_slot_count = (
        db.query(func.count(database.EpisodeSlot.id))
        .join(database.Season, database.EpisodeSlot.season_id == database.Season.id)
        .filter(
            database.Season.show_id == str(season.show_id),
            database.Season.number < season.number,
        )
        .scalar()
    ) or 0
    episode_number = prior_slot_count + slot.slot_number

    title = (body.title or "").strip() or (slot.title or "").strip() or f"Episode {slot.slot_number}"

    db_project = database.Project(
        title=title,
        template=body.template,
        current_phase=database.PhaseType.IDEA,
        show_id=str(season.show_id),
        season_id=str(season.id),
        episode_number=episode_number,
        owner_id=str(current_user.id),
    )
    db.add(db_project)
    db.flush()

    for sub in get_template_subsections(body.template.value):
        db.add(database.PhaseData(
            project_id=db_project.id,
            phase=sub["phase"],
            subsection_key=sub["subsection_key"],
            sort_order=sub["sort_order"],
            content={},
            ai_suggestions={},
        ))

    slot.project_id = db_project.id
    db.commit()
    db.refresh(db_project)
    return db_project


# ============================================================
# Reconcile: written episode vs slot plan
# ============================================================

@router.post("/slots/{slot_id}/reconcile", response_model=schemas.SlotReconcileResponse)
async def reconcile_slot(
    slot_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI-compare the written episode's summary against the slot plan and return
    a PROPOSAL for updated plan fields. Writes NOTHING (preview pattern, like
    /wizards/regenerate-scene); the client applies via PUT /slots/{id} with
    plan_stale=false.
    """
    slot, _season = _get_owned_slot(db, slot_id, current_user)
    if not slot.project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This slot has no linked episode to reconcile against.",
        )

    project = db.query(database.Project).filter(
        database.Project.id == str(slot.project_id)
    ).first()
    summary = (project.episode_summary or "").strip() if project else ""
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The linked episode has no summary yet — generate its episode summary first.",
        )

    proposal = await template_ai_service.reconcile_slot_plan(
        slot_plan={
            "title": slot.title or "",
            "logline": slot.logline or "",
            "arc_function": slot.arc_function or "",
            "character_states": slot.character_states or {},
            "cliffhanger": slot.cliffhanger or "",
        },
        episode_title=project.title,
        episode_summary=summary,
    )
    return schemas.SlotReconcileResponse(
        slot_id=slot.id,
        episode_summary=summary,
        proposal=proposal,
    )
