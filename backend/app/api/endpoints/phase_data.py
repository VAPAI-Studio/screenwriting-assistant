# backend/app/api/endpoints/phase_data.py

import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import List, Dict
from uuid import UUID

from ...models import schemas, database
from ...models.database import BreakdownElement
from ..dependencies import get_db, get_current_user
from ...templates import get_template
from ...utils.screenplay_split import split_by_headings

router = APIRouter()

# Phases that trigger breakdown_stale when their content is updated.
BREAKDOWN_SENSITIVE_PHASES = {"write", "scenes"}
SHOTLIST_SENSITIVE_PHASES = {"write", "scenes"}


def _mark_breakdown_stale(db: Session, project_id) -> None:
    """Set breakdown_stale=True if a breakdown exists for this project.

    Does not commit -- caller's existing commit covers the change.
    Only marks stale when at least one non-deleted BreakdownElement exists.
    """
    has_breakdown = db.query(BreakdownElement).filter(
        BreakdownElement.project_id == str(project_id),
        BreakdownElement.is_deleted == False,  # noqa: E712
    ).first() is not None
    if has_breakdown:
        project = db.query(database.Project).filter(
            database.Project.id == str(project_id)
        ).first()
        if project:
            project.breakdown_stale = True


def _mark_shotlist_stale(db: Session, project_id) -> None:
    """Set shotlist_stale=True if shots exist for this project.

    Does not commit -- caller's existing commit covers the change.
    Only marks stale when at least one Shot exists.
    """
    has_shots = db.query(database.Shot).filter(
        database.Shot.project_id == str(project_id),
    ).first() is not None
    if has_shots:
        project = db.query(database.Project).filter(
            database.Project.id == str(project_id)
        ).first()
        if project:
            project.shotlist_stale = True


def _mark_episode_summary_stale(db: Session, project_id) -> None:
    """Set episode_summary_stale=True if this episode already has a summary.

    Does not commit -- caller's existing commit covers the change.
    Existence-gated (D-02): only flips True when the Project's OWN
    episode_summary is non-empty (truthy after strip). When no summary
    exists yet there is nothing to invalidate, so the flag stays False.
    Keys purely on summary existence -- show linkage (show_id) is
    irrelevant, so standalone projects are unaffected unless they carry a
    summary of their own.
    """
    project = db.query(database.Project).filter(
        database.Project.id == str(project_id)
    ).first()
    if project and project.episode_summary and project.episode_summary.strip():
        project.episode_summary_stale = True


def _verify_project_ownership(db: Session, project_id: UUID, user_id: UUID) -> database.Project:
    """Verify user owns the project and return it."""
    project = db.query(database.Project).filter(
        database.Project.id == str(project_id),
        database.Project.owner_id == str(user_id)
    ).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


# NOTE: readiness must be defined BEFORE the /{project_id}/{phase}/{subsection_key}
# catch-all route, otherwise FastAPI matches "readiness" as a phase parameter.
@router.get("/{project_id}/readiness/{phase}")
async def get_readiness(
    project_id: UUID,
    phase: str,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Calculate readiness scores for a wizard based on project data completeness."""
    project = _verify_project_ownership(db, project_id, current_user.id)

    if not project.template:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project has no template")

    template_config = get_template(project.template.value)

    # Find the target phase in the template
    target_phase = None
    for p in template_config.get("phases", []):
        if p["id"] == phase:
            target_phase = p
            break

    if not target_phase:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Phase '{phase}' not found")

    # Get all phase_data for this project
    all_data = db.query(database.PhaseData).filter(
        database.PhaseData.project_id == project_id
    ).all()
    data_map = {f"{d.phase}.{d.subsection_key}": d for d in all_data}

    # Calculate readiness for each wizard subsection
    readiness = {"checks": [], "overall_percent": 0, "is_ready": False}
    total_score = 0
    total_max = 0

    for sub in target_phase.get("subsections", []):
        wizard_config = sub.get("wizard_config", {})
        for check in wizard_config.get("readiness_checks", []):
            source = check["source"]
            label = check["label"]

            source_data = data_map.get(source)
            content = source_data.content if source_data else {}

            if "count_fields" in check:
                fields = check["count_fields"]
                filled = sum(1 for f in fields if content.get(f))
                total = len(fields)
            elif "count_items" in check:
                # Count list items for this phase_data
                if source_data:
                    item_count = db.query(database.ListItem).filter(
                        database.ListItem.phase_data_id == source_data.id
                    ).count()
                else:
                    item_count = 0
                filled = item_count
                total = max(1, item_count)  # At least 1 required
            else:
                filled = 0
                total = 1

            total_score += filled
            total_max += total

            readiness["checks"].append({
                "label": label,
                "filled": filled,
                "total": total,
                "percent": round(filled / total * 100, 1) if total > 0 else 0
            })

    if total_max > 0:
        readiness["overall_percent"] = round(total_score / total_max * 100, 1)
    readiness["is_ready"] = readiness["overall_percent"] >= 50

    return readiness


@router.get("/{project_id}/{phase}", response_model=List[schemas.PhaseDataResponse])
async def get_phase_data(
    project_id: UUID,
    phase: str,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all subsection data for a phase."""
    _verify_project_ownership(db, project_id, current_user.id)

    data = db.query(database.PhaseData).filter(
        database.PhaseData.project_id == project_id,
        database.PhaseData.phase == phase
    ).order_by(database.PhaseData.sort_order).all()

    return data


@router.get("/{project_id}/{phase}/{subsection_key}", response_model=schemas.PhaseDataResponse)
async def get_subsection_data(
    project_id: UUID,
    phase: str,
    subsection_key: str,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get content for a specific subsection."""
    _verify_project_ownership(db, project_id, current_user.id)

    data = db.query(database.PhaseData).filter(
        database.PhaseData.project_id == project_id,
        database.PhaseData.phase == phase,
        database.PhaseData.subsection_key == subsection_key
    ).first()

    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phase data not found")

    return data


@router.patch("/{project_id}/{phase}/{subsection_key}", response_model=schemas.PhaseDataResponse)
async def update_subsection_data(
    project_id: UUID,
    phase: str,
    subsection_key: str,
    update: schemas.PhaseDataUpdate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update content for a specific subsection (merge into existing JSONB)."""
    _verify_project_ownership(db, project_id, current_user.id)

    data = db.query(database.PhaseData).filter(
        database.PhaseData.project_id == str(project_id),
        database.PhaseData.phase == phase,
        database.PhaseData.subsection_key == subsection_key
    ).first()

    # Upsert (D-54-01): fetch-or-create so the first save from an empty project
    # does not 404. Mirrors the proven wizard pattern (wizards.py:261-269). This
    # is generic and safe for ANY subsection -- only the merge below runs for an
    # absent row; the screenplay-scoped reconcile further down is still gated.
    if not data:
        data = database.PhaseData(
            project_id=str(project_id),
            phase=phase,
            subsection_key=subsection_key,
            content={},
        )
        db.add(data)
        db.flush()

    # Merge new content into existing content
    existing = dict(data.content or {})
    existing.update(update.content)
    data.content = existing
    flag_modified(data, "content")

    # Screenplay-scoped reconcile (D-54-05): only for the manual screenplay-save
    # path. Idempotently REPLACE this project's ScreenplayContent rows from the
    # saved screenplays (delete-then-recreate) so repeated saves never accumulate
    # duplicates and so the breakdown extraction (which reads ScreenplayContent)
    # sees the hand-written scenes. This is NOT applied to any other subsection --
    # the generic PATCH must never create ScreenplayContent rows for arbitrary
    # subsections (design constraint, covered by a test). Staleness is already
    # handled by the generic phase-in-*_SENSITIVE_PHASES calls below (phase=="write"
    # is in both sets), so it is NOT duplicated here.
    if phase == "write" and subsection_key == "screenplay_editor":
        # Reconcile ScreenplayContent ONLY when this request actually carried the
        # screenplays key (the caller is authoritative for screenplays). If the key
        # is present we delete-then-recreate unconditionally — including the empty
        # case, so emptying a screenplay also clears its stale rows (WR-02). If the
        # key is absent, leave existing rows untouched (the PATCH touched something
        # else in screenplay_editor content).
        if "screenplays" in (update.content or {}):
            screenplays = update.content.get("screenplays") or []
            db.query(database.ScreenplayContent).filter(
                database.ScreenplayContent.project_id == str(project_id)
            ).delete(synchronize_session=False)
            for sp in screenplays:
                db.add(database.ScreenplayContent(
                    project_id=str(project_id),
                    content=sp.get("content", ""),
                    formatted_content=sp,
                ))

    if phase in BREAKDOWN_SENSITIVE_PHASES:
        _mark_breakdown_stale(db, project_id)
        # Same write/scenes edit site (D-02a); existence-gated inside the helper,
        # so it only flips when this episode already has a summary to invalidate.
        _mark_episode_summary_stale(db, project_id)
    if phase in SHOTLIST_SENSITIVE_PHASES:
        _mark_shotlist_stale(db, project_id)

    db.commit()
    db.refresh(data)
    return data


_IMPORT_EXTENSIONS = {".pdf": "pdf", ".txt": "txt"}


@router.post("/{project_id}/screenplay/import")
async def import_screenplay_file(
    project_id: UUID,
    file: UploadFile = File(...),
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import a screenplay from an uploaded PDF/TXT file.

    Extracts the text (document_service, same path as book ingestion), splits it
    into scenes by INT./EXT. sluglines, and persists via the canonical
    screenplay_editor PATCH path — so ScreenplayContent reconcile and
    breakdown/shotlist staleness behave exactly like a manual editor save.
    """
    from ...services.document_service import document_service

    _verify_project_ownership(db, project_id, current_user.id)

    ext = os.path.splitext(file.filename or "")[1].lower()
    file_type = _IMPORT_EXTENSIONS.get(ext)
    if not file_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext or 'unknown'}'. Use .pdf or .txt",
        )

    raw = await file.read()
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(raw)
            tmp_path = tmp.name
        try:
            pages = document_service.extract_text(tmp_path, file_type)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not read the file: {e}",
            )
    finally:
        if tmp_path:
            os.unlink(tmp_path)

    text = "\n".join(p.get("text", "") for p in pages)
    screenplays = split_by_headings(text)
    if not screenplays:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text could be extracted from the file (is it a scanned/image-only PDF?)",
        )

    # Reuse the PATCH handler so reconcile + staleness stay single-sourced.
    await update_subsection_data(
        project_id,
        "write",
        "screenplay_editor",
        schemas.PhaseDataUpdate(content={"screenplays": screenplays}),
        current_user,
        db,
    )

    return {
        "scene_count": len(screenplays),
        "scenes": [
            {"episode_index": s["episode_index"], "title": s["title"]}
            for s in screenplays
        ],
    }
