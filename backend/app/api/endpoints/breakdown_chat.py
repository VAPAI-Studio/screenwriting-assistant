# backend/app/api/endpoints/breakdown_chat.py

import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from uuid import UUID

from ...models import schemas, database
from ..dependencies import get_db, get_current_user
from ...services.ai_provider import chat_completion_stream

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


def _build_breakdown_system_prompt(
    shots: list[schemas.BreakdownChatShotContext],
    elements: list[schemas.BreakdownChatElementContext],
) -> str:
    """Build a system prompt with injected shots and breakdown elements context."""
    prompt_parts = [
        "You are a filmmaking and breakdown assistant. You help users plan their "
        "shots, manage breakdown elements, and make production decisions. You have "
        "full context about the current project's shotlist and breakdown elements.",
        "",
        "When discussing shots, reference them by their shot number (e.g., Shot #1). "
        "When discussing breakdown elements, reference them by name and category.",
        "",
        "When the user asks you to create a new shot, describe what you would create "
        "in your response. When the user asks you to modify an existing shot, describe "
        "the changes in your response. Include shot numbers, scene associations, and "
        "field values in your description.",
        "",
    ]

    # Add shots context
    if shots:
        prompt_parts.append("## Current Shotlist")
        prompt_parts.append("")
        for shot in shots:
            scene_info = f" (Scene: {shot.scene_item_id})" if shot.scene_item_id else " (Unassigned)"
            fields_str = ", ".join(f"{k}: {v}" for k, v in shot.fields.items()) if shot.fields else "No fields set"
            prompt_parts.append(f"- Shot #{shot.shot_number}{scene_info} [{shot.source}]: {fields_str}")
        prompt_parts.append("")
    else:
        prompt_parts.append("## Current Shotlist")
        prompt_parts.append("No shots created yet.")
        prompt_parts.append("")

    # Add breakdown elements context grouped by category
    if elements:
        prompt_parts.append("## Breakdown Elements")
        prompt_parts.append("")
        categories: dict[str, list[schemas.BreakdownChatElementContext]] = {}
        for elem in elements:
            categories.setdefault(elem.category, []).append(elem)
        for category, items in sorted(categories.items()):
            prompt_parts.append(f"### {category.title()}")
            for item in items:
                desc = f" - {item.description}" if item.description else ""
                prompt_parts.append(f"- {item.name}{desc}")
            prompt_parts.append("")
    else:
        prompt_parts.append("## Breakdown Elements")
        prompt_parts.append("No breakdown elements created yet.")
        prompt_parts.append("")

    prompt_parts.append(
        "Provide helpful, specific advice based on the project context above. "
        "Be concise and actionable."
    )

    return "\n".join(prompt_parts)


@router.post("/{project_id}/stream")
async def breakdown_chat_stream(
    project_id: UUID,
    body: schemas.BreakdownChatRequest,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stream a breakdown-aware AI response."""
    _verify_project_ownership(db, project_id, current_user.id)

    system_prompt = _build_breakdown_system_prompt(body.shots_context, body.elements_context)

    messages = (
        [{"role": "system", "content": system_prompt}]
        + [{"role": m.role, "content": m.content} for m in body.message_history]
        + [{"role": "user", "content": body.content}]
    )

    async def generate():
        full_text = ""
        try:
            async for chunk in chat_completion_stream(
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
            ):
                full_text += chunk
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        except Exception as e:
            logger.error(f"Breakdown chat streaming error: {e}")
            full_text = full_text or "I had trouble generating a response."

        # shot_action is always None in Plan 01; Plan 02 adds extraction
        yield f"data: {json.dumps({'done': True, 'full_text': full_text, 'shot_action': None})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
