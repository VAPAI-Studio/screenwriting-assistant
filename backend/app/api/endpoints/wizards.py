# backend/app/api/endpoints/wizards.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from uuid import UUID

from ...models import schemas, database
from ..dependencies import get_db, get_current_user
from ...services.template_ai_service import template_ai_service

router = APIRouter()


def _get_project_context(db: Session, project: database.Project) -> str:
    """Build project context string from all phase data."""
    phase_data = db.query(database.PhaseData).filter(
        database.PhaseData.project_id == project.id
    ).all()

    project_data = {}
    for pd in phase_data:
        phase_key = pd.phase.value if hasattr(pd.phase, 'value') else pd.phase
        if phase_key not in project_data:
            project_data[phase_key] = {}
        project_data[phase_key][pd.subsection_key] = pd.content or {}

    template_id = project.template.value if hasattr(project.template, 'value') else project.template
    return template_ai_service._build_project_context(project_data, template_id)


@router.post("/run", response_model=schemas.WizardRunResponse)
async def run_wizard(
    request: schemas.WizardRunRequest,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start a wizard run (beat, episode, scene, or script generation)."""
    project = db.query(database.Project).filter(
        database.Project.id == request.project_id,
        database.Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not project.template:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project has no template")

    # Create wizard run record
    wizard_run = database.WizardRun(
        project_id=project.id,
        wizard_type=request.wizard_type,
        phase=request.phase,
        config=request.config,
        status="running"
    )
    db.add(wizard_run)
    db.commit()
    db.refresh(wizard_run)

    # Build project context and run wizard
    project_context = _get_project_context(db, project)
    template_id = project.template.value

    try:
        result = await template_ai_service.wizard_generate(
            wizard_type=request.wizard_type,
            config=request.config,
            project_context=project_context,
            template_id=template_id
        )
        wizard_run.result = result
        wizard_run.status = "completed"
    except Exception as e:
        wizard_run.status = "failed"
        wizard_run.error_message = str(e)

    db.commit()
    db.refresh(wizard_run)
    return wizard_run


@router.get("/{run_id}", response_model=schemas.WizardRunResponse)
async def get_wizard_run(
    run_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get wizard run status and results."""
    wizard_run = db.query(database.WizardRun).filter(
        database.WizardRun.id == run_id
    ).first()
    if not wizard_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wizard run not found")

    # Verify ownership
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
        database.WizardRun.id == run_id
    ).first()
    if not wizard_run or wizard_run.status != "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wizard run not found or not completed")

    project = db.query(database.Project).filter(
        database.Project.id == wizard_run.project_id,
        database.Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    result = wizard_run.result or {}

    # Idea wizard: update PhaseData fields directly
    if wizard_run.wizard_type == "idea_wizard":
        fields = result.get("fields", {})
        if not fields:
            return {"status": "success", "message": "No fields to apply"}

        phase_data = db.query(database.PhaseData).filter(
            database.PhaseData.project_id == project.id,
            database.PhaseData.phase == wizard_run.phase,
            database.PhaseData.subsection_key == "idea_wizard",
        ).first()
        if not phase_data:
            phase_data = database.PhaseData(
                project_id=project.id,
                phase=wizard_run.phase,
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

    # Determine which phase_data to add items to
    if wizard_run.wizard_type == "episode_wizard":
        items_key = "episodes"
        item_type = "episode"
        subsection_key = "episode_list"
    elif wizard_run.wizard_type == "scene_wizard":
        items_key = "scenes"
        item_type = "scene"
        subsection_key = "scene_list"
    else:
        return {"status": "success", "items_created": 0, "message": "No items to apply for this wizard type"}

    # Find the target phase_data
    phase_data = db.query(database.PhaseData).filter(
        database.PhaseData.project_id == project.id,
        database.PhaseData.phase == wizard_run.phase,
        database.PhaseData.subsection_key == subsection_key
    ).first()
    if not phase_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Phase data for {subsection_key} not found")

    # Get current max sort_order
    existing_count = db.query(database.ListItem).filter(
        database.ListItem.phase_data_id == phase_data.id
    ).count()

    # Create list items from results
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

    db.commit()
    return {"status": "success", "items_created": items_created}
