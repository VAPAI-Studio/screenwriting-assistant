"""Screenwriting MCP tools (v8.0).

Phase 56 introduces the FIRST long-running (AI) tool — screenplay_generate_scene
— which proves the job-id + poll pattern. It wraps the existing v6.0
regenerate_single_scene path and returns a job_id immediately; the regenerated
scene PREVIEW is retrieved via the generic job_status tool.

Read/direct-write screenwriting tools are added in Phase 58.
"""

from mcp.server.fastmcp import Context
from fastapi import HTTPException

from ...models import database
from ...services.template_ai_service import template_ai_service
from ...utils.bible_context import build_bible_context
from ...api.endpoints.wizards import (
    _get_project_context,
    _get_character_data,
    _scene_episodes_for_regen,
    _latest_script_wizard_config,
)
from ..context import resolve_user, mcp_session
from ..jobs import registry


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
