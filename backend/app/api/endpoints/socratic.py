# backend/app/api/endpoints/socratic.py
"""Socratic "hard questions" endpoints (mounted at /api/projects/{project_id}/socratic).

GET  /current            -> the pending question, a freshly generated one, or a cooldown.
POST /{question_id}/answer -> persist the author's answer (starts the 3h cooldown).
GET  /history            -> all questions+answers for the project.

All owner-scoped: the project must belong to the current user.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...models import schemas, database
from ..dependencies import get_db, get_current_user
from ...exceptions import NotFoundException
from ...services import socratic_service
from ...utils.bible_context import build_bible_context
from ..endpoints.wizards import _get_project_context

router = APIRouter()


class AnswerRequest(BaseModel):
    answer: str


def _owned_project(db: Session, project_id: UUID, user_id) -> database.Project:
    project = (
        db.query(database.Project)
        .filter(
            database.Project.id == str(project_id),
            database.Project.owner_id == str(user_id),
        )
        .first()
    )
    if not project:
        raise NotFoundException(resource="Project", identifier=str(project_id))
    return project


def _serialize(q: database.SocraticQuestion) -> dict:
    return {
        "id": str(q.id),
        "question": q.question,
        "rationale": q.rationale,
        "source_concepts": q.source_concepts or [],
        "answer": q.answer,
        "answered_at": q.answered_at.isoformat() if q.answered_at else None,
        "created_at": q.created_at.isoformat() if q.created_at else None,
    }


@router.get("/{project_id}/socratic/current")
async def get_current_question(
    project_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the pending question, a new one (if cooldown elapsed), or cooldown info."""
    project = _owned_project(db, project_id, current_user.id)

    # 1. A still-unanswered question is never replaced — show it.
    pending = socratic_service.get_pending(db, project.id)
    if pending:
        return {"status": "pending", "question": _serialize(pending)}

    # 2. Within the 3h cooldown after the last answer -> don't generate.
    remaining = socratic_service.cooldown_remaining_seconds(db, project.id)
    if remaining > 0:
        last = socratic_service._last_answered(db, project.id)
        return {
            "status": "cooldown",
            "cooldown_seconds": remaining,
            "last_answered": _serialize(last) if last else None,
        }

    # 3. Generate a fresh one, grounded in the script (+ prior answers) and books.
    bible = build_bible_context(db, project)
    answers_block = socratic_service.socratic_answers_context(db, project.id)
    extra = "\n\n".join(b for b in (bible, answers_block) if b) or None
    script_context = _get_project_context(db, project, bible_context=extra)

    q = await socratic_service.generate_question(db, project, script_context)
    return {"status": "new", "question": _serialize(q)}


@router.post("/{project_id}/socratic/{question_id}/answer")
async def answer_question(
    project_id: UUID,
    question_id: UUID,
    body: AnswerRequest,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Persist the author's answer; starts the 3h regeneration cooldown."""
    _owned_project(db, project_id, current_user.id)

    q = (
        db.query(database.SocraticQuestion)
        .filter(
            database.SocraticQuestion.id == str(question_id),
            database.SocraticQuestion.project_id == str(project_id),
        )
        .first()
    )
    if not q:
        raise NotFoundException(resource="SocraticQuestion", identifier=str(question_id))

    answer = (body.answer or "").strip()
    if not answer:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Answer cannot be empty")

    q.answer = answer
    q.answered_at = socratic_service._now()
    db.commit()
    db.refresh(q)
    return _serialize(q)


@router.get("/{project_id}/socratic/history")
async def question_history(
    project_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """All questions for the project, newest first."""
    _owned_project(db, project_id, current_user.id)
    rows = (
        db.query(database.SocraticQuestion)
        .filter(database.SocraticQuestion.project_id == str(project_id))
        .order_by(database.SocraticQuestion.created_at.desc())
        .all()
    )
    return {"questions": [_serialize(r) for r in rows]}
