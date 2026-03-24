from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from ...models import schemas, database
from ..dependencies import get_db, get_current_user
from ...exceptions import NotFoundException

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
        episode_duration_minutes=show.episode_duration_minutes,
    )
