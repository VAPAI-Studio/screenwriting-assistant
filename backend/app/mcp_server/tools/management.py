"""Project / show management MCP tools (v8.0 Phase 57).

Fast, synchronous, owner-scoped wrappers over the existing project/show models.
These are the agent's session entry point (project_list/get tell it what to
write into). Per the locked decision, NO delete tools are exposed.
"""

from typing import Optional

from mcp.server.fastmcp import Context
from fastapi import HTTPException

from ...models import database
from ...models.schemas import ContinuityMode
from ..context import resolve_user, mcp_session

_VALID_FRAMEWORKS = {f.value for f in database.Framework}
_VALID_CONTINUITY = {m.value for m in ContinuityMode}


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
        """PIPELINE STEP 1 (ORIENT) — list the authenticated user's standalone
        projects (Films). Episodes (projects with a show_id) are listed per-show
        via episode_list, not here. The starting point for any session: call this
        (or show_list) before creating or writing anything."""
        with mcp_session() as db:
            user = resolve_user(ctx, db)
            rows = db.query(database.Project).filter(
                database.Project.owner_id == str(user.id),
                database.Project.show_id.is_(None),
            ).order_by(database.Project.created_at.desc()).all()
            return {"summary": f"{len(rows)} project(s)", "projects": [_project_brief(p) for p in rows]}

    @mcp.tool()
    def project_get(ctx: Context, project_id: str) -> dict:
        """Read a single project's metadata (the target to write into / extract
        from). breakdown_stale / shotlist_stale flags mean the screenplay changed
        since the last extraction/generation — re-run those steps. 404 if it
        isn't owned by the caller."""
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
        """PIPELINE STEP 2 (CREATE) — create a new standalone film project with a
        title and story framework (three_act | save_the_cat | hero_journey).
        Returns the new project; write its screenplay next with screenplay_write.
        Shows, episodes, and season maps are created in the web app, not here."""
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
        """PIPELINE STEP 1 (ORIENT, series) — list the authenticated user's TV
        shows (id, title, episode count). Follow up with episode_list and
        show_read_bible before touching any episode."""
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
        & style). REQUIRED READING before writing or revising any episode of the
        show — everything you write must honor it. 404 if not owned by the
        caller."""
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
                    "central_premise": s.bible_central_premise or "",
                    "story_engine": s.bible_story_engine or "",
                    "series_questions": s.bible_series_questions or "",
                    "characters": s.bible_characters or "",
                    "regular_cast": s.bible_regular_cast or [],
                    "world_setting": s.bible_world_setting or "",
                    "season_arc": s.bible_season_arc or "",
                    "tone_style": s.bible_tone_style or "",
                },
            }

    @mcp.tool()
    def show_create(ctx: Context, title: str, description: str = "", continuity_mode: str = "anthology") -> dict:
        """PIPELINE STEP 2 (CREATE, series) — create a new TV show (series). Next,
        fill its bible with bible_write (or bible_draft to propose one from a seed),
        then build a season with season_create + slot_create. continuity_mode is
        one of: anthology (standalone episodes), connected (serial with carried
        continuity), standalone (a single film-like show)."""
        title = (title or "").strip()
        if len(title) < 2:
            raise HTTPException(status_code=400, detail="title must be at least 2 characters")
        if continuity_mode not in _VALID_CONTINUITY:
            raise HTTPException(
                status_code=400,
                detail=f"continuity_mode must be one of {sorted(_VALID_CONTINUITY)}",
            )
        with mcp_session() as db:
            user = resolve_user(ctx, db)
            s = database.Show(
                title=title,
                description=(description or "").strip(),
                continuity_mode=continuity_mode,
                owner_id=user.id,
            )
            db.add(s)
            db.commit()
            db.refresh(s)
            return {"summary": f"Created show '{s.title}'", "data": {"show_id": str(s.id), "title": s.title}}

    @mcp.tool()
    def bible_write(
        ctx: Context,
        show_id: str,
        central_premise: Optional[str] = None,
        story_engine: Optional[str] = None,
        series_questions: Optional[str] = None,
        characters: Optional[str] = None,
        regular_cast: Optional[list] = None,
        world_setting: Optional[str] = None,
        season_arc: Optional[str] = None,
        tone_style: Optional[str] = None,
    ) -> dict:
        """PIPELINE STEP 2 (CREATE, series) — write/update a show's series bible.
        Only the fields you pass are changed (partial update); omit a field to
        leave it untouched. regular_cast is a list of {name, role, arc} objects.
        The bible is REQUIRED READING (show_read_bible) before writing episodes,
        so fill it before generating any script. 404 if the show isn't owned."""
        fields = {
            "bible_central_premise": central_premise,
            "bible_story_engine": story_engine,
            "bible_series_questions": series_questions,
            "bible_characters": characters,
            "bible_world_setting": world_setting,
            "bible_season_arc": season_arc,
            "bible_tone_style": tone_style,
        }
        with mcp_session() as db:
            user = resolve_user(ctx, db)
            s = db.query(database.Show).filter(
                database.Show.id == show_id,
                database.Show.owner_id == str(user.id),
            ).first()
            if not s:
                raise HTTPException(status_code=404, detail="Show not found")
            for col, val in fields.items():
                if val is not None:
                    setattr(s, col, str(val))
            if regular_cast is not None:
                # Sanitize to [{name, role, arc}]; drop non-dicts and fully-empty entries.
                cast = []
                for m in (regular_cast or [])[:50]:
                    if not isinstance(m, dict):
                        continue
                    member = {
                        "name": str(m.get("name", "") or "").strip(),
                        "role": str(m.get("role", "") or "").strip(),
                        "arc": str(m.get("arc", "") or "").strip(),
                    }
                    if any(member.values()):
                        cast.append(member)
                s.bible_regular_cast = cast
            db.commit()
            return {"summary": f"Updated bible for '{s.title}'", "data": {"show_id": str(s.id)}}

    @mcp.tool()
    async def bible_draft(
        ctx: Context,
        show_id: str,
        logline: str = "",
        genre: str = "",
        tone: str = "",
        guidance: str = "",
    ) -> dict:
        """Propose a full series bible from a short seed (logline/genre/tone), using
        the show's CURRENT bible as grounding. Returns the proposal WITHOUT saving —
        review it, then persist the parts you want with bible_write. 404 if the show
        isn't owned by the caller."""
        from ...services.template_ai_service import template_ai_service
        from ...api.endpoints.shows import _build_bible_text
        with mcp_session() as db:
            user = resolve_user(ctx, db)
            s = db.query(database.Show).filter(
                database.Show.id == show_id,
                database.Show.owner_id == str(user.id),
            ).first()
            if not s:
                raise HTTPException(status_code=404, detail="Show not found")
            current = _build_bible_text(s)
            show_context = f"**Show:** {s.title}"
            if (s.description or "").strip():
                show_context += f"\n{s.description.strip()}"
            show_context += f"\n\n{current}" if current else "\n(The bible is currently empty.)"
        proposal = await template_ai_service.generate_series_bible(
            config={"logline": logline, "genre": genre, "tone": tone, "custom_guidance": guidance},
            show_context=show_context,
        )
        return {"summary": f"Drafted a bible for '{s.title}' (not saved)", "data": proposal}

    @mcp.tool()
    def episode_list(ctx: Context, show_id: str) -> dict:
        """List a show's episodes (project id, episode number, title), ordered by
        episode number. Each episode is a project — pass its project_id to the
        screenplay/breakdown/shotlist tools. 404 if the show isn't owned by the
        caller."""
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

    @mcp.tool()
    def season_create(ctx: Context, show_id: str, title: str = "", arc_summary: str = "", number: Optional[int] = None) -> dict:
        """PIPELINE STEP 2 (CREATE, series) — create a season for a show. `number`
        auto-increments per show when omitted. Fill its episode plan with
        slot_create. A season's arc_summary supersedes the show's bible season arc
        for that season's episodes. 404 if the show isn't owned by the caller."""
        from sqlalchemy import func
        with mcp_session() as db:
            user = resolve_user(ctx, db)
            s = db.query(database.Show).filter(
                database.Show.id == show_id,
                database.Show.owner_id == str(user.id),
            ).first()
            if not s:
                raise HTTPException(status_code=404, detail="Show not found")
            if number is None:
                max_num = db.query(func.max(database.Season.number)).filter(
                    database.Season.show_id == str(show_id)
                ).scalar()
                number = (max_num or 0) + 1
            elif db.query(database.Season).filter(
                database.Season.show_id == str(show_id), database.Season.number == number
            ).first():
                raise HTTPException(status_code=400, detail=f"Season {number} already exists in this show.")
            season = database.Season(
                show_id=str(show_id), number=number,
                title=(title or "").strip(), arc_summary=(arc_summary or "").strip(),
            )
            db.add(season)
            db.commit()
            db.refresh(season)
            return {"summary": f"Created season {season.number}", "data": {"season_id": str(season.id), "number": season.number}}

    @mcp.tool()
    def slot_create(
        ctx: Context,
        season_id: str,
        title: str = "",
        logline: str = "",
        arc_function: str = "",
        cliffhanger: str = "",
        slot_number: Optional[int] = None,
    ) -> dict:
        """PIPELINE STEP 2 (CREATE, series) — add one planned-episode slot to a
        season map. `slot_number` (narrative order) auto-increments per season when
        omitted. The slot is the PLAN; once its episode is written the episode is
        the truth. 404 if the season isn't owned by the caller."""
        from sqlalchemy import func
        with mcp_session() as db:
            user = resolve_user(ctx, db)
            season = (
                db.query(database.Season)
                .join(database.Show, database.Season.show_id == database.Show.id)
                .filter(database.Season.id == season_id, database.Show.owner_id == str(user.id))
                .first()
            )
            if not season:
                raise HTTPException(status_code=404, detail="Season not found")
            if slot_number is None:
                max_num = db.query(func.max(database.EpisodeSlot.slot_number)).filter(
                    database.EpisodeSlot.season_id == str(season_id)
                ).scalar()
                slot_number = (max_num or 0) + 1
            elif db.query(database.EpisodeSlot).filter(
                database.EpisodeSlot.season_id == str(season_id),
                database.EpisodeSlot.slot_number == slot_number,
            ).first():
                raise HTTPException(status_code=400, detail=f"Slot {slot_number} already exists in this season.")
            slot = database.EpisodeSlot(
                season_id=str(season_id), slot_number=slot_number,
                title=(title or "").strip(), logline=(logline or "").strip(),
                arc_function=(arc_function or "").strip(), cliffhanger=(cliffhanger or "").strip(),
            )
            db.add(slot)
            db.commit()
            db.refresh(slot)
            return {"summary": f"Created slot {slot.slot_number}", "data": {"slot_id": str(slot.id), "slot_number": slot.slot_number}}
