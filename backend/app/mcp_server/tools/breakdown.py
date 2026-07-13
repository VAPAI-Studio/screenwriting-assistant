"""Breakdown MCP tools (v8.0 Phase 59).

- breakdown_extract: long-running (AI) extraction via the v7.0 path → job-id.
- breakdown_read: read elements, category-scoped, with their scene appearances.
"""

from mcp.server.fastmcp import Context
from fastapi import HTTPException
from sqlalchemy.orm import selectinload

from ...models import database
from ...services.breakdown_service import breakdown_service
from ...utils.bible_context import build_bible_context
from ..context import resolve_user, mcp_session
from ..jobs import registry

_VALID_CATEGORIES = {c.value for c in database.BreakdownCategory}


def _verify_owned(db, owner_id: str, project_id: str) -> database.Project:
    p = db.query(database.Project).filter(
        database.Project.id == project_id,
        database.Project.owner_id == str(owner_id),
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


def _element_brief(el) -> dict:
    cat = el.category
    appearances = [
        {
            "scene_item_id": str(link.scene_item_id) if link.scene_item_id else None,
            "context": link.context or "",
            "source": getattr(link, "source", None),
        }
        for link in (el.scene_links or [])
    ]
    return {
        "element_id": str(el.id),
        "name": el.name,
        "category": cat.value if hasattr(cat, "value") else str(cat),
        "user_modified": bool(getattr(el, "user_modified", False)),
        "appearances": appearances,
    }


def register(mcp):
    """Register breakdown tools on the given FastMCP instance."""

    @mcp.tool()
    async def breakdown_extract(ctx: Context, project_id: str) -> dict:
        """PIPELINE STEP 4 (BREAKDOWN) — extract production elements (characters,
        locations, props, etc.) from a project's screenplay using the AI breakdown
        path. Run it once the screenplay is settled, and re-run whenever the
        project's breakdown_stale flag is set. LONG-RUNNING: returns a job_id
        immediately — poll job_status(job_id) for the run result, then read the
        elements with breakdown_read. Owner-scoped."""
        from uuid import UUID

        with mcp_session() as db:
            user = resolve_user(ctx, db)
            owner_id = str(user.id)
            project = _verify_owned(db, owner_id, project_id)
            bible_context = build_bible_context(db, project)

        job = await registry.create(owner_id, kind="breakdown_extract")

        async def _work():
            # Extraction manages its own session+transaction; give it a fresh one.
            with mcp_session() as work_db:
                run = await breakdown_service.extract(work_db, UUID(project_id), bible_context=bible_context)
                return {
                    "run_id": str(getattr(run, "id", "")),
                    "status": getattr(run, "status", None) and (
                        run.status.value if hasattr(run.status, "value") else str(run.status)
                    ),
                    "element_count": getattr(run, "element_count", None),
                }

        await registry.run(job, _work)
        return {"job_id": job.id, "status": job.status, "kind": job.kind}

    @mcp.tool()
    def breakdown_read(ctx: Context, project_id: str, category: str = "") -> dict:
        """Read a project's breakdown elements with their scene appearances
        (populated by breakdown_extract). Optionally filter by category
        (character | location | prop | wardrobe | vehicle | set_dressing |
        animal | sfx | makeup_hair | extras). Owner-scoped."""
        category = (category or "").strip()
        if category and category not in _VALID_CATEGORIES:
            raise HTTPException(
                status_code=400,
                detail=f"category must be one of {sorted(_VALID_CATEGORIES)}",
            )
        with mcp_session() as db:
            user = resolve_user(ctx, db)
            _verify_owned(db, str(user.id), project_id)
            q = db.query(database.BreakdownElement).filter(
                database.BreakdownElement.project_id == str(project_id),
                database.BreakdownElement.is_deleted == False,  # noqa: E712
            )
            if category:
                q = q.filter(database.BreakdownElement.category == category)
            q = q.order_by(database.BreakdownElement.sort_order, database.BreakdownElement.created_at)
            elements = q.options(selectinload(database.BreakdownElement.scene_links)).all()
            return {
                "summary": f"{len(elements)} element(s)" + (f" in '{category}'" if category else ""),
                "elements": [_element_brief(e) for e in elements],
            }
