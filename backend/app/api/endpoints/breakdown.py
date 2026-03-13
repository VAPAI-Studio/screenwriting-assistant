# backend/app/api/endpoints/breakdown.py

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...models import schemas, database
from ..dependencies import get_db, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


def _verify_project_ownership(db: Session, project_id: UUID, user_id: UUID) -> database.Project:
    """Verify user owns the project. Returns project or raises 404."""
    project = db.query(database.Project).filter(
        database.Project.id == project_id,
        database.Project.owner_id == user_id
    ).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _verify_element_ownership(db: Session, element_id: UUID, user_id: UUID) -> database.BreakdownElement:
    """Verify user owns the project containing this breakdown element. Returns element or raises 404."""
    element = db.query(database.BreakdownElement).filter(
        database.BreakdownElement.id == element_id
    ).first()
    if not element:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Element not found")

    _verify_project_ownership(db, element.project_id, user_id)
    return element


@router.get("/elements/{project_id}", response_model=List[schemas.BreakdownElementResponse])
async def list_elements(
    project_id: UUID,
    category: Optional[str] = None,
    include_deleted: bool = False,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List breakdown elements for a project, optionally filtered by category."""
    _verify_project_ownership(db, project_id, current_user.id)

    query = db.query(database.BreakdownElement).filter(
        database.BreakdownElement.project_id == project_id
    )

    if not include_deleted:
        query = query.filter(database.BreakdownElement.is_deleted == False)

    if category:
        query = query.filter(database.BreakdownElement.category == category)

    query = query.order_by(
        database.BreakdownElement.sort_order,
        database.BreakdownElement.created_at
    )

    return query.all()


@router.post("/elements/{project_id}", response_model=schemas.BreakdownElementResponse, status_code=status.HTTP_201_CREATED)
async def create_element(
    project_id: UUID,
    body: schemas.BreakdownElementCreate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new breakdown element. Restores soft-deleted duplicates; returns 409 for active duplicates."""
    _verify_project_ownership(db, project_id, current_user.id)

    # Check for existing element with same (project_id, category, name) -- including soft-deleted
    existing = db.query(database.BreakdownElement).filter(
        database.BreakdownElement.project_id == project_id,
        database.BreakdownElement.category == body.category,
        database.BreakdownElement.name == body.name
    ).first()

    if existing:
        if existing.is_deleted:
            # Restore soft-deleted element with updated fields
            existing.is_deleted = False
            existing.description = body.description
            existing.metadata_ = body.metadata
            existing.source = "user"
            existing.user_modified = True
            db.commit()
            db.refresh(existing)
            return existing
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Element '{body.name}' already exists in category '{body.category}'"
            )

    db_element = database.BreakdownElement(
        project_id=project_id,
        category=body.category,
        name=body.name,
        description=body.description,
        metadata_=body.metadata,
        source="user",
    )
    db.add(db_element)
    db.commit()
    db.refresh(db_element)
    return db_element


@router.put("/element/{element_id}", response_model=schemas.BreakdownElementResponse)
async def update_element(
    element_id: UUID,
    body: schemas.BreakdownElementUpdate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a breakdown element. Always sets user_modified=True."""
    element = _verify_element_ownership(db, element_id, current_user.id)

    update_data = body.model_dump(exclude_unset=True)

    # Map Pydantic 'metadata' field to ORM 'metadata_' attribute
    if "metadata" in update_data:
        update_data["metadata_"] = update_data.pop("metadata")

    for field, value in update_data.items():
        setattr(element, field, value)

    # Always mark as user-modified on any update
    element.user_modified = True

    db.commit()
    db.refresh(element)
    return element


@router.delete("/element/{element_id}")
async def delete_element(
    element_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Soft-delete a breakdown element. Never hard-deletes."""
    element = _verify_element_ownership(db, element_id, current_user.id)

    element.is_deleted = True
    db.commit()

    return {"status": "success", "message": "Element soft-deleted"}
