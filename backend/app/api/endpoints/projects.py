# backend/app/api/endpoints/projects.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from uuid import UUID

from ...models import schemas, database
from ..dependencies import get_db, get_current_user
from ...utils import validate_project_title, validate_framework
from ...exceptions import NotFoundException, ValidationException
from ...templates import get_template, get_template_subsections
from ...services.template_ai_service import template_ai_service

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
    """List all projects for the current user"""
    projects = db.query(database.Project).options(
        joinedload(database.Project.sections)
            .joinedload(database.Section.checklist_items)
    ).filter(
        database.Project.owner_id == current_user.id
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
    db.commit()

    return {"status": "success", "episode_summary_stale": False}

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
