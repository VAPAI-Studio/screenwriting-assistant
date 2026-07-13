"""Shotlist MCP tools (v8.0 Phase 60).

- shotlist_read: read a project's shots (grouped by scene).
- shot_create: create one shot.
- shotlist_generate: long-running AI shotlist generation → job-id.
"""

from mcp.server.fastmcp import Context
from fastapi import HTTPException

from ...models import database
from ...services.shotlist_generation_service import shotlist_generation_service
from ..context import resolve_user, mcp_session
from ..jobs import registry


def _verify_owned(db, owner_id: str, project_id: str) -> database.Project:
    p = db.query(database.Project).filter(
        database.Project.id == project_id,
        database.Project.owner_id == str(owner_id),
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


def _shot_brief(s) -> dict:
    return {
        "shot_id": str(s.id),
        "scene_item_id": str(s.scene_item_id) if s.scene_item_id else None,
        "shot_number": s.shot_number,
        "fields": s.fields or {},
        "source": s.source,
    }


def register(mcp):
    """Register shotlist tools on the given FastMCP instance."""

    @mcp.tool()
    def shotlist_read(ctx: Context, project_id: str) -> dict:
        """Read a project's shotlist (shots grouped by scene), as populated by
        shotlist_generate and/or shot_create. Owner-scoped."""
        with mcp_session() as db:
            user = resolve_user(ctx, db)
            _verify_owned(db, str(user.id), project_id)
            shots = db.query(database.Shot).filter(
                database.Shot.project_id == str(project_id)
            ).order_by(database.Shot.scene_item_id, database.Shot.sort_order).all()
            groups: dict = {}
            for s in shots:
                key = str(s.scene_item_id) if s.scene_item_id else "unassigned"
                groups.setdefault(key, []).append(_shot_brief(s))
            return {
                "summary": f"{len(shots)} shot(s) across {len(groups)} scene group(s)",
                "scenes": [{"scene_item_id": k if k != "unassigned" else None, "shots": v}
                           for k, v in groups.items()],
            }

    @mcp.tool()
    def shot_create(ctx: Context, project_id: str, fields: dict | None = None,
                    scene_item_id: str = "", shot_number: int = 1) -> dict:
        """Create one shot on a project by hand — for additions or fixes on top of
        shotlist_generate's output. `fields` is a freeform dict of shot properties
        (shot size, angle, movement, description, etc.). Optionally attach it to a
        scene via scene_item_id. Owner-scoped."""
        with mcp_session() as db:
            user = resolve_user(ctx, db)
            _verify_owned(db, str(user.id), project_id)
            shot = database.Shot(
                project_id=str(project_id),
                scene_item_id=(scene_item_id or None),
                shot_number=shot_number,
                fields=fields or {},
                source="user",
            )
            db.add(shot)
            db.commit()
            db.refresh(shot)
            return {"summary": f"Created shot #{shot.shot_number}", "data": _shot_brief(shot)}

    @mcp.tool()
    async def shotlist_generate(ctx: Context, project_id: str) -> dict:
        """PIPELINE STEP 5 (SHOTLIST, final step) — generate a shotlist from the
        project's screenplay using AI. Run it after the breakdown, and re-run when
        the project's shotlist_stale flag is set. LONG-RUNNING: returns a job_id
        immediately — poll job_status(job_id) for the result, then read the shots
        with shotlist_read. Owner-scoped."""
        from uuid import UUID

        with mcp_session() as db:
            user = resolve_user(ctx, db)
            owner_id = str(user.id)
            _verify_owned(db, owner_id, project_id)

        job = await registry.create(owner_id, kind="shotlist_generate")

        async def _work():
            with mcp_session() as work_db:
                result = await shotlist_generation_service.generate(work_db, UUID(project_id))
                # result is a pydantic model / dict-ish; coerce to a plain dict.
                if hasattr(result, "model_dump"):
                    return result.model_dump()
                if hasattr(result, "dict"):
                    return result.dict()
                return {"result": str(result)}

        await registry.run(job, _work)
        return {"job_id": job.id, "status": job.status, "kind": job.kind}
