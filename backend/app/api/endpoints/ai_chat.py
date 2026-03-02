# backend/app/api/endpoints/ai_chat.py

import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import List, Optional
from uuid import UUID

from ...models import schemas, database
from ..dependencies import get_db, get_current_user
from ...services.template_ai_service import template_ai_service
from ...templates import get_template

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_project_context(db: Session, project: database.Project) -> str:
    """Build project context from all phase data."""
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


def _get_subsection_config(template_id: str, phase: str, subsection_key: str) -> dict:
    """Get subsection config from template."""
    template = get_template(template_id)
    for p in template.get("phases", []):
        if p["id"] == phase:
            for sub in p.get("subsections", []):
                if sub["key"] == subsection_key:
                    return sub
    return {}


@router.post("/sessions", response_model=schemas.AISessionResponse)
async def create_ai_session(
    request: schemas.AISessionCreate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a contextual AI chat session."""
    project = db.query(database.Project).filter(
        database.Project.id == request.project_id,
        database.Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    session = database.AISession(
        project_id=project.id,
        phase=request.phase,
        subsection_key=request.subsection_key,
        context_item_id=request.context_item_id,
        user_id=current_user.id
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions/lookup", response_model=schemas.AISessionResponse)
async def lookup_ai_session(
    project_id: UUID,
    phase: str,
    subsection_key: str,
    context_item_id: Optional[UUID] = None,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Find the most recent existing session for a given context."""
    query = db.query(database.AISession).filter(
        database.AISession.project_id == project_id,
        database.AISession.user_id == current_user.id,
        database.AISession.phase == phase,
        database.AISession.subsection_key == subsection_key,
    )
    if context_item_id:
        query = query.filter(database.AISession.context_item_id == context_item_id)
    else:
        query = query.filter(database.AISession.context_item_id.is_(None))

    session = query.order_by(database.AISession.created_at.desc()).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No existing session")
    return session


@router.get("/sessions/{session_id}/messages", response_model=List[schemas.AIMessageResponse])
async def get_ai_messages(
    session_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get chat message history."""
    session = db.query(database.AISession).filter(
        database.AISession.id == session_id,
        database.AISession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    messages = db.query(database.AIMessage).filter(
        database.AIMessage.session_id == session_id
    ).order_by(database.AIMessage.created_at).all()

    return messages


@router.post("/sessions/{session_id}/messages", response_model=schemas.AIMessageResponse)
async def send_ai_message(
    session_id: UUID,
    message: schemas.AIMessageCreate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message and get an AI response."""
    session = db.query(database.AISession).filter(
        database.AISession.id == session_id,
        database.AISession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Get project
    project = db.query(database.Project).filter(
        database.Project.id == session.project_id
    ).first()
    if not project or not project.template:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project not found or has no template")

    # Save user message
    user_msg = database.AIMessage(
        session_id=session_id,
        role="user",
        content=message.content,
        message_type="chat"
    )
    db.add(user_msg)
    db.commit()

    # Build context and get AI response
    project_context = _get_project_context(db, project)
    template_id = project.template.value

    # Get system prompt and subsection config
    sub_config = _get_subsection_config(template_id, session.phase, session.subsection_key)
    system_prompt = sub_config.get(
        "chat_system_prompt",
        "You are a helpful screenwriting assistant. Help the user develop their story."
    )

    # Get chat history
    history = db.query(database.AIMessage).filter(
        database.AIMessage.session_id == session_id
    ).order_by(database.AIMessage.created_at).all()
    chat_history = [{"role": m.role, "content": m.content} for m in history]

    mode = getattr(message, "mode", "brainstorm")

    if mode == "action":
        # Action mode: AI can modify fields
        # Gather field definitions from subsection config (handles all template patterns)
        field_defs = []
        if "fields" in sub_config:
            field_defs = sub_config["fields"]
        elif "field_groups" in sub_config:
            for group in sub_config.get("field_groups", []):
                field_defs.extend(group.get("fields", []))
        elif "cards" in sub_config:
            field_defs = sub_config["cards"]
        elif "card_groups" in sub_config:
            for group in sub_config.get("card_groups", []):
                field_defs.extend(group.get("fields", []))

        # Fallback: check editor_config (used by individual_editor / ordered_list patterns)
        if not field_defs:
            editor_config = sub_config.get("editor_config", {})
            if editor_config.get("fields"):
                field_defs = editor_config["fields"]

        logger.info(f"Action mode: phase={session.phase}, subsection={session.subsection_key}, field_defs_count={len(field_defs)}")

        # Get current content
        current_content = {}
        if session.context_item_id:
            item = db.query(database.ListItem).filter(
                database.ListItem.id == session.context_item_id
            ).first()
            if item:
                current_content = item.content or {}
                # Use editor_config fields for items
                editor_config = sub_config.get("editor_config", {})
                if editor_config.get("fields"):
                    field_defs = editor_config["fields"]
        else:
            phase_data = db.query(database.PhaseData).filter(
                database.PhaseData.project_id == project.id,
                database.PhaseData.phase == session.phase,
                database.PhaseData.subsection_key == session.subsection_key,
            ).first()
            if phase_data:
                current_content = phase_data.content or {}

        result = await template_ai_service.chat_with_action(
            user_message=message.content,
            chat_history=chat_history[:-1],
            system_prompt=system_prompt,
            project_context=project_context,
            field_definitions=field_defs,
            current_content=current_content,
        )

        ai_text = result.get("message", "")
        field_updates = result.get("field_updates", {})
        applied = False

        logger.info(f"Action mode AI result: field_updates keys={list(field_updates.keys()) if field_updates else 'none'}")

        # Apply field updates if any
        if field_updates:
            if session.context_item_id:
                item = db.query(database.ListItem).filter(
                    database.ListItem.id == session.context_item_id
                ).first()
                if item:
                    existing = dict(item.content or {})
                    existing.update(field_updates)
                    item.content = existing
                    flag_modified(item, "content")
                    db.commit()
                    applied = True
                    logger.info(f"Action mode: updated ListItem {item.id}, keys={list(field_updates.keys())}")
                else:
                    logger.warning(f"Action mode: ListItem {session.context_item_id} not found")
            else:
                phase_data = db.query(database.PhaseData).filter(
                    database.PhaseData.project_id == project.id,
                    database.PhaseData.phase == session.phase,
                    database.PhaseData.subsection_key == session.subsection_key,
                ).first()
                if not phase_data:
                    # Create PhaseData if it doesn't exist
                    logger.warning(f"Action mode: PhaseData not found, creating for phase={session.phase}, key={session.subsection_key}")
                    phase_data = database.PhaseData(
                        project_id=project.id,
                        phase=session.phase,
                        subsection_key=session.subsection_key,
                        content={},
                    )
                    db.add(phase_data)
                    db.flush()

                existing = dict(phase_data.content or {})
                existing.update(field_updates)
                phase_data.content = existing
                flag_modified(phase_data, "content")
                db.commit()
                applied = True
                logger.info(f"Action mode: updated PhaseData {phase_data.id}, keys={list(field_updates.keys())}")

        ai_msg = database.AIMessage(
            session_id=session_id,
            role="assistant",
            content=ai_text,
            message_type="action",
            metadata_={"field_updates": field_updates, "applied": applied},
        )
    else:
        # Brainstorm mode: plain conversational response
        ai_response = await template_ai_service.chat_respond(
            user_message=message.content,
            chat_history=chat_history[:-1],
            system_prompt=system_prompt,
            project_context=project_context,
        )

        ai_msg = database.AIMessage(
            session_id=session_id,
            role="assistant",
            content=ai_response,
            message_type="chat",
        )

    try:
        db.add(ai_msg)
        db.commit()
        db.refresh(ai_msg)
    except IntegrityError:
        # Session was deleted while the AI was generating a response (race condition)
        db.rollback()
        logger.warning(f"Session {session_id} was deleted during AI response generation")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chat session was closed while generating response"
        )
    return ai_msg


@router.post("/sessions/{session_id}/messages/stream")
async def send_ai_message_stream(
    session_id: UUID,
    message: schemas.AIMessageCreate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message and stream the AI response via SSE."""
    session = db.query(database.AISession).filter(
        database.AISession.id == session_id,
        database.AISession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    project = db.query(database.Project).filter(
        database.Project.id == session.project_id
    ).first()
    if not project or not project.template:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project not found or has no template")

    # Save user message
    user_msg = database.AIMessage(
        session_id=session_id,
        role="user",
        content=message.content,
        message_type="chat"
    )
    db.add(user_msg)
    db.commit()

    # Build context
    project_context = _get_project_context(db, project)
    template_id = project.template.value
    sub_config = _get_subsection_config(template_id, session.phase, session.subsection_key)
    system_prompt = sub_config.get(
        "chat_system_prompt",
        "You are a helpful screenwriting assistant. Help the user develop their story."
    )

    # Get chat history
    history = db.query(database.AIMessage).filter(
        database.AIMessage.session_id == session_id
    ).order_by(database.AIMessage.created_at).all()
    chat_history = [{"role": m.role, "content": m.content} for m in history]

    mode = getattr(message, "mode", "brainstorm")

    if mode == "action":
        # Action mode: two-phase streaming
        # Phase 1: stream conversational message, Phase 2: extract field updates via JSON
        field_defs = []
        if "fields" in sub_config:
            field_defs = sub_config["fields"]
        elif "field_groups" in sub_config:
            for group in sub_config.get("field_groups", []):
                field_defs.extend(group.get("fields", []))
        elif "cards" in sub_config:
            field_defs = sub_config["cards"]
        elif "card_groups" in sub_config:
            for group in sub_config.get("card_groups", []):
                field_defs.extend(group.get("fields", []))

        # Fallback: check editor_config (used by individual_editor / ordered_list patterns)
        if not field_defs:
            editor_config = sub_config.get("editor_config", {})
            if editor_config.get("fields"):
                field_defs = editor_config["fields"]

        current_content = {}
        if session.context_item_id:
            item = db.query(database.ListItem).filter(
                database.ListItem.id == session.context_item_id
            ).first()
            if item:
                current_content = item.content or {}
                editor_config = sub_config.get("editor_config", {})
                if editor_config.get("fields"):
                    field_defs = editor_config["fields"]
        else:
            phase_data = db.query(database.PhaseData).filter(
                database.PhaseData.project_id == project.id,
                database.PhaseData.phase == session.phase,
                database.PhaseData.subsection_key == session.subsection_key,
            ).first()
            if phase_data:
                current_content = phase_data.content or {}

        async def action_stream():
            full_text = ""
            try:
                # Phase 1: Stream conversational message
                async for chunk in template_ai_service.chat_action_stream_message(
                    user_message=message.content,
                    chat_history=chat_history[:-1],
                    system_prompt=system_prompt,
                    project_context=project_context,
                    field_definitions=field_defs,
                    current_content=current_content,
                ):
                    full_text += chunk
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            except Exception as e:
                logger.error(f"Action streaming error: {e}", exc_info=True)
                full_text = full_text or "I had trouble generating a response."

            # Phase 2: Extract field updates via JSON-mode call
            field_updates = {}
            applied = False
            try:
                field_updates = await template_ai_service.chat_action_extract_updates(
                    user_message=message.content,
                    assistant_message=full_text,
                    field_definitions=field_defs,
                    current_content=current_content,
                )
                logger.info(f"Action mode extracted field_updates keys={list(field_updates.keys()) if field_updates else 'none'}")
            except Exception as e:
                logger.error(f"Action field extraction error: {e}", exc_info=True)

            # Apply field updates to database
            if field_updates:
                if session.context_item_id:
                    item = db.query(database.ListItem).filter(
                        database.ListItem.id == session.context_item_id
                    ).first()
                    if item:
                        existing = dict(item.content or {})
                        existing.update(field_updates)
                        item.content = existing
                        flag_modified(item, "content")
                        db.commit()
                        applied = True
                else:
                    pd = db.query(database.PhaseData).filter(
                        database.PhaseData.project_id == project.id,
                        database.PhaseData.phase == session.phase,
                        database.PhaseData.subsection_key == session.subsection_key,
                    ).first()
                    if not pd:
                        pd = database.PhaseData(
                            project_id=project.id,
                            phase=session.phase,
                            subsection_key=session.subsection_key,
                            content={},
                        )
                        db.add(pd)
                        db.flush()
                    existing = dict(pd.content or {})
                    existing.update(field_updates)
                    pd.content = existing
                    flag_modified(pd, "content")
                    db.commit()
                    applied = True

            # Save AI message to database
            ai_msg = database.AIMessage(
                session_id=session_id,
                role="assistant",
                content=full_text,
                message_type="action",
                metadata_={"field_updates": field_updates, "applied": applied},
            )
            try:
                db.add(ai_msg)
                db.commit()
                db.refresh(ai_msg)
                yield f"data: {json.dumps({'field_updates': field_updates, 'applied': applied, 'done': True, 'id': str(ai_msg.id)})}\n\n"
            except IntegrityError:
                db.rollback()
                logger.warning(f"Session {session_id} deleted during action streaming")

            yield "data: [DONE]\n\n"

        return StreamingResponse(action_stream(), media_type="text/event-stream")

    # Brainstorm mode: stream the response
    async def brainstorm_stream():
        full_text = ""
        try:
            async for chunk in template_ai_service.chat_respond_stream(
                user_message=message.content,
                chat_history=chat_history[:-1],
                system_prompt=system_prompt,
                project_context=project_context,
            ):
                full_text += chunk
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            full_text = full_text or "I'm having trouble generating a response right now."

        # Save the complete AI message to the database
        ai_msg = database.AIMessage(
            session_id=session_id,
            role="assistant",
            content=full_text,
            message_type="chat",
        )
        try:
            db.add(ai_msg)
            db.commit()
            db.refresh(ai_msg)
            yield f"data: {json.dumps({'done': True, 'id': str(ai_msg.id)})}\n\n"
        except IntegrityError:
            db.rollback()
            logger.warning(f"Session {session_id} deleted during streaming")
        yield "data: [DONE]\n\n"

    return StreamingResponse(brainstorm_stream(), media_type="text/event-stream")


@router.delete("/sessions/{session_id}")
async def delete_ai_session(
    session_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a chat session."""
    session = db.query(database.AISession).filter(
        database.AISession.id == session_id,
        database.AISession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    db.delete(session)
    db.commit()
    return {"status": "success"}


@router.post("/fill-blanks", response_model=schemas.AIActionResponse)
async def fill_blanks(
    request: schemas.FillBlanksRequest,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI fills empty fields for a subsection or item."""
    project = db.query(database.Project).filter(
        database.Project.id == request.project_id,
        database.Project.owner_id == current_user.id
    ).first()
    if not project or not project.template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    template_id = project.template.value
    sub_config = _get_subsection_config(template_id, request.phase, request.subsection_key)

    if request.item_id:
        # Fill blanks for a specific item
        item = db.query(database.ListItem).filter(database.ListItem.id == request.item_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        current_content = item.content or {}
        # Use editor_config fields if available
        editor_config = sub_config.get("editor_config", {})
        field_config = {"fields": editor_config.get("fields", [])}
    else:
        # Fill blanks for a subsection
        phase_data = db.query(database.PhaseData).filter(
            database.PhaseData.project_id == project.id,
            database.PhaseData.phase == request.phase,
            database.PhaseData.subsection_key == request.subsection_key
        ).first()
        if not phase_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phase data not found")
        current_content = phase_data.content or {}
        field_config = sub_config

    project_context = _get_project_context(db, project)
    result = await template_ai_service.fill_blanks(
        current_content=current_content,
        subsection_config=field_config,
        project_context=project_context
    )

    # Apply results
    if request.item_id and "content" in result:
        item = db.query(database.ListItem).filter(database.ListItem.id == request.item_id).first()
        existing = dict(item.content or {})
        existing.update(result["content"])
        item.content = existing
        flag_modified(item, "content")
        db.commit()
    elif "content" in result:
        phase_data = db.query(database.PhaseData).filter(
            database.PhaseData.project_id == project.id,
            database.PhaseData.phase == request.phase,
            database.PhaseData.subsection_key == request.subsection_key
        ).first()
        if phase_data:
            existing = dict(phase_data.content or {})
            existing.update(result["content"])
            phase_data.content = existing
            flag_modified(phase_data, "content")
            db.commit()

    return result


@router.post("/give-notes", response_model=schemas.AIActionResponse)
async def give_notes(
    request: schemas.GiveNotesRequest,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI gives feedback on content."""
    project = db.query(database.Project).filter(
        database.Project.id == request.project_id,
        database.Project.owner_id == current_user.id
    ).first()
    if not project or not project.template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    template_id = project.template.value
    sub_config = _get_subsection_config(template_id, request.phase, request.subsection_key)

    if request.item_id:
        item = db.query(database.ListItem).filter(database.ListItem.id == request.item_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        current_content = item.content or {}
    else:
        phase_data = db.query(database.PhaseData).filter(
            database.PhaseData.project_id == project.id,
            database.PhaseData.phase == request.phase,
            database.PhaseData.subsection_key == request.subsection_key
        ).first()
        if not phase_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phase data not found")
        current_content = phase_data.content or {}

    project_context = _get_project_context(db, project)
    result = await template_ai_service.give_notes(
        current_content=current_content,
        subsection_config=sub_config,
        project_context=project_context
    )

    return result


@router.post("/analyze-structure")
async def analyze_structure(
    request: schemas.AnalyzeStructureRequest,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI analyzes episode/scene list structure."""
    project = db.query(database.Project).filter(
        database.Project.id == request.project_id,
        database.Project.owner_id == current_user.id
    ).first()
    if not project or not project.template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Get the list items for the subsection
    phase_data = db.query(database.PhaseData).filter(
        database.PhaseData.project_id == project.id,
        database.PhaseData.phase == request.phase,
        database.PhaseData.subsection_key == request.subsection_key
    ).first()
    if not phase_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phase data not found")

    items = db.query(database.ListItem).filter(
        database.ListItem.phase_data_id == phase_data.id
    ).order_by(database.ListItem.sort_order).all()

    items_data = [{"sort_order": i.sort_order, **i.content} for i in items]

    project_context = _get_project_context(db, project)
    template_id = project.template.value

    result = await template_ai_service.analyze_structure(
        items=items_data,
        template_id=template_id,
        project_context=project_context
    )

    return result
