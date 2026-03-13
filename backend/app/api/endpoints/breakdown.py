# backend/app/api/endpoints/breakdown.py

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...models import schemas, database
from ...services.breakdown_service import breakdown_service
from ..dependencies import get_db, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


def _verify_project_ownership(db: Session, project_id: UUID, user_id: UUID) -> database.Project:
    """Verify user owns the project. Returns project or raises 404."""
    project = db.query(database.Project).filter(
        database.Project.id == str(project_id),
        database.Project.owner_id == str(user_id)
    ).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _verify_element_ownership(db: Session, element_id: UUID, user_id: UUID) -> database.BreakdownElement:
    """Verify user owns the project containing this breakdown element. Returns element or raises 404."""
    element = db.query(database.BreakdownElement).filter(
        database.BreakdownElement.id == str(element_id)
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
        database.BreakdownElement.project_id == str(project_id)
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
        database.BreakdownElement.project_id == str(project_id),
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


# ============================================================
# Extraction trigger (API-01) -- calls real BreakdownService
# ============================================================

@router.post("/extract/{project_id}", response_model=schemas.BreakdownRunResponse)
async def trigger_extraction(
    project_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trigger AI extraction of production elements from screenplay content."""
    _verify_project_ownership(db, project_id, current_user.id)

    try:
        run = await breakdown_service.extract(db, project_id)
        return run
    except Exception as e:
        logger.error(f"Extraction failed for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction failed: {str(e)}"
        )


# ============================================================
# Scene link add/remove (API-06)
# ============================================================

@router.post("/element/{element_id}/scenes", status_code=status.HTTP_201_CREATED)
async def add_scene_link(
    element_id: UUID,
    body: schemas.SceneLinkCreate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Link a breakdown element to a scene (ListItem). Idempotent: duplicate returns 200."""
    _verify_element_ownership(db, element_id, current_user.id)

    # Validate scene exists
    scene = db.query(database.ListItem).filter(
        database.ListItem.id == str(body.scene_item_id)
    ).first()
    if not scene:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found")

    # Idempotent: check for existing link
    existing = db.query(database.ElementSceneLink).filter(
        database.ElementSceneLink.element_id == str(element_id),
        database.ElementSceneLink.scene_item_id == str(body.scene_item_id),
    ).first()
    if existing:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Scene link already exists", "id": str(existing.id)},
        )

    link = database.ElementSceneLink(
        element_id=element_id,
        scene_item_id=body.scene_item_id,
        context=body.context,
        source="user",
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return {"message": "Scene linked", "id": str(link.id)}


@router.delete("/element/{element_id}/scenes/{scene_item_id}")
async def remove_scene_link(
    element_id: UUID,
    scene_item_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a scene link from a breakdown element. Hard-delete for junction table."""
    _verify_element_ownership(db, element_id, current_user.id)

    link = db.query(database.ElementSceneLink).filter(
        database.ElementSceneLink.element_id == str(element_id),
        database.ElementSceneLink.scene_item_id == str(scene_item_id),
    ).first()
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene link not found")

    db.delete(link)
    db.commit()
    return {"status": "success", "message": "Scene link removed"}


# ============================================================
# Summary endpoint (API-07)
# ============================================================

@router.get("/summary/{project_id}", response_model=schemas.BreakdownSummaryResponse)
async def get_summary(
    project_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get breakdown summary with category counts, staleness, and last run info."""
    project = _verify_project_ownership(db, project_id, current_user.id)

    # Single aggregation query (GROUP BY, not N+1)
    counts = db.query(
        database.BreakdownElement.category,
        func.count(database.BreakdownElement.id)
    ).filter(
        database.BreakdownElement.project_id == str(project_id),
        database.BreakdownElement.is_deleted == False,
    ).group_by(database.BreakdownElement.category).all()

    counts_dict = {cat: count for cat, count in counts}
    total_elements = sum(counts_dict.values())

    # Latest run
    last_run = db.query(database.BreakdownRun).filter(
        database.BreakdownRun.project_id == str(project_id)
    ).order_by(database.BreakdownRun.created_at.desc()).first()

    return schemas.BreakdownSummaryResponse(
        project_id=project_id,
        is_stale=project.breakdown_stale or False,
        total_elements=total_elements,
        counts_by_category=counts_dict,
        last_run=schemas.BreakdownRunResponse.model_validate(last_run) if last_run else None,
    )
