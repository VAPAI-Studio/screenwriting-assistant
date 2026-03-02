from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...models import schemas
from ...models.database import Agent, Book, AgentBook
from ...services.agent_templates import AGENT_TEMPLATES
from ..dependencies import get_db, get_current_user

router = APIRouter()


@router.get("/")
async def list_agents(
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all agents (user-owned + defaults)."""
    agents = (
        db.query(Agent)
        .filter(
            (Agent.owner_id == current_user.id) | (Agent.is_default == True)
        )
        .filter(Agent.is_active == True)
        .all()
    )
    return [
        {
            "id": str(a.id),
            "name": a.name,
            "description": a.description,
            "personality": a.personality,
            "color": a.color,
            "icon": a.icon,
            "is_active": a.is_active,
            "is_default": a.is_default,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "book_count": len(a.books),
        }
        for a in agents
    ]


@router.post("/")
async def create_agent(
    agent_data: schemas.AgentCreate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a custom agent."""
    agent = Agent(
        owner_id=current_user.id,
        name=agent_data.name,
        description=agent_data.description,
        system_prompt_template=agent_data.system_prompt_template,
        personality=agent_data.personality,
        color=agent_data.color,
        icon=agent_data.icon,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return {
        "id": str(agent.id),
        "name": agent.name,
        "description": agent.description,
        "color": agent.color,
        "icon": agent.icon,
        "is_active": agent.is_active,
        "is_default": agent.is_default,
    }


@router.patch("/{agent_id}")
async def update_agent(
    agent_id: UUID,
    agent_data: schemas.AgentUpdate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an agent's properties."""
    agent = (
        db.query(Agent)
        .filter(Agent.id == agent_id, Agent.owner_id == current_user.id)
        .first()
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    update_data = agent_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)

    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an agent."""
    agent = (
        db.query(Agent)
        .filter(Agent.id == agent_id, Agent.owner_id == current_user.id)
        .first()
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    db.delete(agent)
    db.commit()
    return {"message": "Agent deleted"}


@router.post("/{agent_id}/books/{book_id}")
async def link_book_to_agent(
    agent_id: UUID,
    book_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Link a book to an agent for RAG retrieval."""
    agent = (
        db.query(Agent)
        .filter(Agent.id == agent_id, Agent.owner_id == current_user.id)
        .first()
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    book = (
        db.query(Book)
        .filter(Book.id == book_id, Book.owner_id == current_user.id)
        .first()
    )
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    existing = (
        db.query(AgentBook)
        .filter(AgentBook.agent_id == agent_id, AgentBook.book_id == book_id)
        .first()
    )
    if not existing:
        link = AgentBook(agent_id=agent_id, book_id=book_id)
        db.add(link)
        db.commit()

    return {"message": "Book linked to agent"}


@router.delete("/{agent_id}/books/{book_id}")
async def unlink_book_from_agent(
    agent_id: UUID,
    book_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unlink a book from an agent."""
    link = (
        db.query(AgentBook)
        .filter(AgentBook.agent_id == agent_id, AgentBook.book_id == book_id)
        .first()
    )
    if link:
        db.delete(link)
        db.commit()
    return {"message": "Book unlinked from agent"}


@router.post("/seed-defaults")
async def seed_default_agents(
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Seed default agent templates (idempotent)."""
    created = 0
    for template in AGENT_TEMPLATES:
        existing = (
            db.query(Agent)
            .filter(Agent.name == template["name"], Agent.is_default == True)
            .first()
        )
        if not existing:
            agent = Agent(
                owner_id=current_user.id,
                name=template["name"],
                description=template["description"],
                system_prompt_template=template["system_prompt_template"],
                personality=template["personality"],
                color=template["color"],
                icon=template["icon"],
                is_default=True,
                is_active=True,
            )
            db.add(agent)
            created += 1

    db.commit()
    return {"message": f"Seeded {created} default agents", "total_defaults": len(AGENT_TEMPLATES)}
