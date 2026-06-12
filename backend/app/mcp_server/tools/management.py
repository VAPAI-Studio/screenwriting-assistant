"""Project / show management MCP tools (v8.0 Phase 57).

Fast, synchronous, owner-scoped wrappers over the existing project/show models.
These are the agent's session entry point (project_list/get tell it what to
write into). Per the locked decision, NO delete tools are exposed.
"""

from mcp.server.fastmcp import Context
from fastapi import HTTPException

from ...models import database
from ..context import resolve_user, mcp_session

_VALID_FRAMEWORKS = {f.value for f in database.Framework}


def _project_framework(p: database.Project):
    """Read the framework safely. The legacy `framework` enum column is broken on
    Postgres (D-57-A), so prefer the value recorded in template_config; fall back
    to the column only if it reads back cleanly."""
    cfg = p.template_config or {}
    if isinstance(cfg, dict) and cfg.get("framework"):
        return cfg["framework"]
    try:
        v = p.framework
        return (v.value if hasattr(v, "value") else str(v)) if v else None
    except Exception:
        return None


def _enum_value(v):
    """Read an enum-or-str column value uniformly (sqlite stores enums as str)."""
    if v is None:
        return None
    return v.value if hasattr(v, "value") else str(v)


def _project_brief(p: database.Project) -> dict:
    return {
        "project_id": str(p.id),
        "title": p.title,
        "framework": _project_framework(p),
        "template": _enum_value(p.template),
        "show_id": str(p.show_id) if p.show_id else None,
        "episode_number": p.episode_number,
        "breakdown_stale": bool(p.breakdown_stale),
        "shotlist_stale": bool(p.shotlist_stale),
    }


def register(mcp):
    """Register management tools on the given FastMCP instance."""

    @mcp.tool()
    def project_list(ctx: Context) -> dict:
        """List the authenticated user's projects (id, title, framework, and
        whether each belongs to a show). The starting point for any session."""
        with mcp_session() as db:
            user = resolve_user(ctx, db)
            rows = db.query(database.Project).filter(
                database.Project.owner_id == str(user.id)
            ).order_by(database.Project.created_at.desc()).all()
            return {"summary": f"{len(rows)} project(s)", "projects": [_project_brief(p) for p in rows]}

    @mcp.tool()
    def project_get(ctx: Context, project_id: str) -> dict:
        """Read a single project's metadata (the target to write into / extract
        from). 404 if it isn't owned by the caller."""
        with mcp_session() as db:
            user = resolve_user(ctx, db)
            p = db.query(database.Project).filter(
                database.Project.id == project_id,
                database.Project.owner_id == str(user.id),
            ).first()
            if not p:
                raise HTTPException(status_code=404, detail="Project not found")
            return {"summary": p.title, "data": _project_brief(p)}

    @mcp.tool()
    def project_create(ctx: Context, title: str, framework: str = "three_act") -> dict:
        """Create a new standalone project with a title and story framework
        (three_act | save_the_cat | hero_journey). Returns the new project."""
        title = (title or "").strip()
        if len(title) < 2:
            raise HTTPException(status_code=400, detail="title must be at least 2 characters")
        if framework not in _VALID_FRAMEWORKS:
            raise HTTPException(
                status_code=400,
                detail=f"framework must be one of {sorted(_VALID_FRAMEWORKS)}",
            )
        with mcp_session() as db:
            user = resolve_user(ctx, db)
            # Use the working `template` column and record the requested framework
            # in template_config — the legacy `framework` enum is broken on PG
            # (D-57-A). This matches how the live app stores projects.
            p = database.Project(
                title=title,
                template=database.TemplateType.SHORT_MOVIE,
                template_config={"framework": framework},
                owner_id=user.id,
            )
            db.add(p)
            db.commit()
            db.refresh(p)
            return {"summary": f"Created '{p.title}'", "data": _project_brief(p)}

    @mcp.tool()
    def show_list(ctx: Context) -> dict:
        """List the authenticated user's TV shows (id, title, episode count)."""
        with mcp_session() as db:
            user = resolve_user(ctx, db)
            shows = db.query(database.Show).filter(
                database.Show.owner_id == str(user.id)
            ).order_by(database.Show.created_at.desc()).all()
            out = []
            for s in shows:
                ep_count = db.query(database.Project).filter(
                    database.Project.show_id == s.id
                ).count()
                out.append({"show_id": str(s.id), "title": s.title, "episode_count": ep_count})
            return {"summary": f"{len(out)} show(s)", "shows": out}

    @mcp.tool()
    def show_read_bible(ctx: Context, show_id: str) -> dict:
        """Read a show's series bible (characters, world/setting, season arc, tone
        & style). 404 if not owned by the caller."""
        with mcp_session() as db:
            user = resolve_user(ctx, db)
            s = db.query(database.Show).filter(
                database.Show.id == show_id,
                database.Show.owner_id == str(user.id),
            ).first()
            if not s:
                raise HTTPException(status_code=404, detail="Show not found")
            return {
                "summary": f"Bible for '{s.title}'",
                "data": {
                    "show_id": str(s.id),
                    "title": s.title,
                    "description": s.description or "",
                    "characters": s.bible_characters or "",
                    "world_setting": s.bible_world_setting or "",
                    "season_arc": s.bible_season_arc or "",
                    "tone_style": s.bible_tone_style or "",
                },
            }

    @mcp.tool()
    def episode_list(ctx: Context, show_id: str) -> dict:
        """List a show's episodes (project id, episode number, title), ordered by
        episode number. 404 if the show isn't owned by the caller."""
        with mcp_session() as db:
            user = resolve_user(ctx, db)
            s = db.query(database.Show).filter(
                database.Show.id == show_id,
                database.Show.owner_id == str(user.id),
            ).first()
            if not s:
                raise HTTPException(status_code=404, detail="Show not found")
            eps = db.query(database.Project).filter(
                database.Project.show_id == s.id
            ).order_by(database.Project.episode_number).all()
            return {
                "summary": f"{len(eps)} episode(s) in '{s.title}'",
                "episodes": [_project_brief(e) for e in eps],
            }
