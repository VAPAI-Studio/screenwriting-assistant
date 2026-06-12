"""Screenwriting MCP tools (v8.0).

Phase 56 introduces the FIRST long-running (AI) tool — screenplay_generate_scene
— which proves the job-id + poll pattern. It wraps the existing v6.0
regenerate_single_scene path and returns a job_id immediately; the regenerated
scene PREVIEW is retrieved via the generic job_status tool.

Phase 58 adds screenplay_read + screenplay_write (the Phase 54 direct path).
"""

import re

from mcp.server.fastmcp import Context
from fastapi import HTTPException
from sqlalchemy.orm.attributes import flag_modified

from ...models import database
from ...services.template_ai_service import template_ai_service
from ...utils.bible_context import build_bible_context
from ...api.endpoints.wizards import (
    _get_project_context,
    _get_character_data,
    _scene_episodes_for_regen,
    _latest_script_wizard_config,
)
from ...api.endpoints.phase_data import _mark_breakdown_stale, _mark_shotlist_stale
from ..context import resolve_user, mcp_session
from ..jobs import registry


# Matches an INT./EXT. scene heading (slugline) at the start of a line.
_HEADING_RE = re.compile(r"^\s*(INT\.|EXT\.|INT/EXT\.|I/E\.)", re.IGNORECASE)


def _split_by_headings(text: str) -> list:
    """Split a hand-written screenplay into scenes by INT./EXT. sluglines.

    Server-side equivalent of the frontend's splitByHeadings (Phase 54, D-54-03):
    each slugline starts a new scene; no-heading text becomes a single "Untitled"
    scene so nothing is lost. Returns [{title, content, episode_index}]. Title is
    the slugline; content is the body after it.
    """
    text = text or ""
    if not text.strip():
        return []

    scenes = []
    cur_title = None
    cur_body: list = []

    def _flush():
        if cur_title is None and not any(l.strip() for l in cur_body):
            return
        title = cur_title if cur_title is not None else "Untitled"
        scenes.append({"title": title, "content": "\n".join(cur_body).strip("\n")})

    for line in text.splitlines():
        if _HEADING_RE.match(line):
            _flush()
            cur_title = line.strip()
            cur_body = []
        else:
            cur_body.append(line)
    _flush()

    for i, s in enumerate(scenes):
        s["episode_index"] = i
    return scenes


def _build_regen_context(db, owner_id: str, project_id, phase: str, episode_index: int):
    """Load everything regenerate_single_scene needs, scoped to the owner.

    Returns a (config, project_context, episode_index, synopsis, prev_scene_text)
    tuple. Raises HTTPException(404) if the project isn't owned by the caller or
    the episode_index is out of range. Runs entirely within a short-lived DB
    session — nothing here is held across the later AI await (D-56-B).
    """
    project = db.query(database.Project).filter(
        database.Project.id == str(project_id),
        database.Project.owner_id == str(owner_id),
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    bible_context = build_bible_context(db, project)
    project_context = _get_project_context(db, project, bible_context=bible_context)

    episodes = _scene_episodes_for_regen(db, project.id)
    if not (0 <= episode_index < len(episodes)):
        raise HTTPException(status_code=404, detail=f"episode_index {episode_index} out of range")

    prior_config = _latest_script_wizard_config(db, project.id)
    config = {
        "episodes": episodes,
        "_characters": _get_character_data(db, project.id),
        "runtime_target": prior_config.get("runtime_target", ""),
        "custom_guidance": prior_config.get("custom_guidance", ""),
    }

    sp_pd = db.query(database.PhaseData).filter(
        database.PhaseData.project_id == project.id,
        database.PhaseData.phase == phase,
        database.PhaseData.subsection_key == "screenplay_editor",
    ).first()
    sp_content = dict(sp_pd.content or {}) if sp_pd else {}
    synopsis = sp_content.get("synopsis", "")
    screenplays = sp_content.get("screenplays", [])
    prev_scene_text = ""
    if episode_index > 0 and episode_index - 1 < len(screenplays):
        prev_scene_text = (screenplays[episode_index - 1] or {}).get("content", "")

    return config, project_context, episode_index, synopsis, prev_scene_text


def register(mcp):
    """Register screenwriting tools on the given FastMCP instance."""

    @mcp.tool()
    async def screenplay_generate_scene(ctx: Context, project_id: str, episode_index: int, phase: str = "write") -> dict:
        """Generate (regenerate) one screenplay scene by its index using the
        improved AI generation path (continuity, character voice, craft).

        LONG-RUNNING: returns a job_id immediately. Poll job_status(job_id) until
        status is "done"; the result is a preview {title, content, episode_index}.
        Returns a preview only — it does NOT overwrite the stored scene.
        """
        # Resolve owner + build context within a short-lived session (fast).
        with mcp_session() as db:
            user = resolve_user(ctx, db)
            owner_id = str(user.id)
            args = _build_regen_context(db, owner_id, project_id, phase, episode_index)

        job = await registry.create(owner_id, kind="screenplay_generate_scene")

        async def _work():
            # AI call is async and holds NO db session across its awaits (D-56-B).
            return await template_ai_service.regenerate_single_scene(*args)

        await registry.run(job, _work)
        return {"job_id": job.id, "status": job.status, "kind": job.kind}

    @mcp.tool()
    def screenplay_read(ctx: Context, project_id: str, scene_index: int = -1, phase: str = "write") -> dict:
        """Read a project's screenplay scenes. By default returns all scenes
        (title + content, ordered by episode_index). Pass scene_index >= 0 to read
        one scene. Owner-scoped (404 if not owned)."""
        with mcp_session() as db:
            user = resolve_user(ctx, db)
            project = db.query(database.Project).filter(
                database.Project.id == project_id,
                database.Project.owner_id == str(user.id),
            ).first()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            sp_pd = db.query(database.PhaseData).filter(
                database.PhaseData.project_id == project.id,
                database.PhaseData.phase == phase,
                database.PhaseData.subsection_key == "screenplay_editor",
            ).first()
            sp_content = dict(sp_pd.content or {}) if sp_pd else {}
            screenplays = sp_content.get("screenplays", []) or []
            scenes = [
                {
                    "episode_index": sp.get("episode_index", i),
                    "title": sp.get("title", ""),
                    "content": sp.get("content", ""),
                }
                for i, sp in enumerate(screenplays)
            ]
            if scene_index is not None and scene_index >= 0:
                match = next((s for s in scenes if s["episode_index"] == scene_index), None)
                if match is None:
                    raise HTTPException(status_code=404, detail=f"scene_index {scene_index} not found")
                return {"summary": f"Scene {scene_index}: {match['title']}", "data": match}
            return {"summary": f"{len(scenes)} scene(s)", "scenes": scenes}

    @mcp.tool()
    def screenplay_write(ctx: Context, project_id: str, text: str, phase: str = "write") -> dict:
        """Write a screenplay directly from raw text (no AI). The text is split
        into scenes by INT./EXT. headings (no-heading text becomes one "Untitled"
        scene), persisted to the project, and the breakdown/shotlist are marked
        stale so extraction picks up the hand-written scenes. Idempotent — repeated
        writes REPLACE the project's scenes (no duplicate accumulation).

        Mirrors the Phase 54 direct-writing path. Owner-scoped (404 if not owned).
        """
        screenplays = _split_by_headings(text)
        with mcp_session() as db:
            user = resolve_user(ctx, db)
            project = db.query(database.Project).filter(
                database.Project.id == project_id,
                database.Project.owner_id == str(user.id),
            ).first()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            # Upsert the screenplay_editor PhaseData (fetch-or-create, mirrors
            # the Phase 54 PATCH upsert).
            pd = db.query(database.PhaseData).filter(
                database.PhaseData.project_id == project.id,
                database.PhaseData.phase == phase,
                database.PhaseData.subsection_key == "screenplay_editor",
            ).first()
            if pd is None:
                pd = database.PhaseData(
                    project_id=project.id,
                    phase=phase,
                    subsection_key="screenplay_editor",
                    content={},
                )
                db.add(pd)
                db.flush()
            new_content = dict(pd.content or {})
            new_content["screenplays"] = screenplays
            pd.content = new_content
            flag_modified(pd, "content")

            # Reconcile ScreenplayContent (delete-then-recreate, scoped to project)
            # — same idempotent logic as the Phase 54 PATCH path (D-54-05).
            db.query(database.ScreenplayContent).filter(
                database.ScreenplayContent.project_id == str(project.id)
            ).delete(synchronize_session=False)
            for sp in screenplays:
                db.add(database.ScreenplayContent(
                    project_id=str(project.id),
                    content=sp.get("content", ""),
                    formatted_content=sp,
                ))

            _mark_breakdown_stale(db, project.id)
            _mark_shotlist_stale(db, project.id)
            db.commit()

            return {
                "summary": f"Saved {len(screenplays)} scene(s)",
                "data": {"project_id": str(project.id), "scene_count": len(screenplays),
                         "scenes": [{"episode_index": s["episode_index"], "title": s["title"]} for s in screenplays]},
            }
