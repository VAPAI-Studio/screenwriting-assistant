# backend/app/utils/bible_context.py

"""
Shared helper to build series bible context for AI prompt injection.

When a project is an episode (has show_id), this function fetches the
associated show's bible data and formats it as a context string for
AI generation prompts. Returns None for standalone film projects.

Phase 68 (SCONT-02/03/04): in `connected` continuity mode the context also
includes a "Prior Episodes" block built from the episode_summary of strictly
prior episodes (ordered by episode_number ascending, most-recent-8 cap,
stale summaries tagged, empty summaries skipped). `anthology` / `standalone`
shows and `show_id=NULL` films are unchanged (bible-only / None).
"""

from typing import Optional
from sqlalchemy.orm import Session
from ..models.database import EpisodeSlot, Project, Season, Show
from ..models.schemas import ContinuityMode


# Most-recent prior episodes to inject in connected mode (D-CAP). The summaries
# are bounded AI auto-summaries (Phase 69), so a simple count cap bounds prompt
# size regardless of season length (threat T-68-03 token blow-up).
PRIOR_EPISODE_CAP = 8

# Literal marker appended to a prior-episode entry whose summary is stale
# (Phase 69 lazy regen clears the stale flag; Phase 68 still injects, tagged).
STALE_SUMMARY_MARKER = " (summary may be out of date)"


def _build_prior_episodes_block(db: Session, show: Show, project: Project) -> Optional[str]:
    """Build the connected-mode "Prior Episodes" block, or None if there is none.

    NOTE: semi-public. Also imported by api/endpoints/wizards.py (Phase 71) to build the
    same connected-mode coherence reference for episode review. Keep the signature/return
    contract stable for that caller.


    Queries strictly-prior episodes (episode_number < current) for THIS show
    only, ordered by episode_number ascending (reliable integer key -- NEVER
    positional, the recurring v6.0/v7.0 ordering bug), skips empty/whitespace
    summaries, and keeps only the most-recent PRIOR_EPISODE_CAP.
    """
    # episode_number is nullable; `< None` is undefined -- guard it.
    if project.episode_number is None:
        return None

    priors = (
        db.query(Project)
        .filter(
            Project.show_id == str(show.id),
            Project.episode_number < project.episode_number,
            Project.episode_summary.isnot(None),
        )
        .order_by(Project.episode_number.asc())  # reliable integer key (shows.py:181)
        .all()
    )

    # Existence-gate: drop null/empty/whitespace summaries (Phase 67 convention).
    priors = [p for p in priors if (p.episode_summary or "").strip()]
    # Most-recent-N: list is episode_number-ascending, so the tail is the
    # PRIOR_EPISODE_CAP highest episode_numbers below current.
    priors = priors[-PRIOR_EPISODE_CAP:]

    if not priors:
        return None

    lines = ["\n### Prior Episodes (for continuity)"]
    for p in priors:
        marker = STALE_SUMMARY_MARKER if p.episode_summary_stale else ""
        lines.append(f"\n**Episode {p.episode_number}: {p.title}**{marker}\n{p.episode_summary.strip()}")
    return "\n".join(lines)


def _build_slot_block(db: Session, project: Project) -> Optional[str]:
    """Phase 4 (temporadas): "this episode in the season map" block, or None.

    When the project was born from an episode slot, its plan (logline, arc
    function, character states at close, cliffhanger) is injected as GUIDANCE —
    the plan steers generation but is never copied into phase_data, so the user
    can diverge without fighting pre-pasted content.
    """
    slot = db.query(EpisodeSlot).filter(EpisodeSlot.project_id == str(project.id)).first()
    if not slot:
        return None

    states = slot.character_states or {}
    has_plan = any([
        (slot.logline or "").strip(),
        (slot.arc_function or "").strip(),
        (slot.cliffhanger or "").strip(),
        states,
    ])
    if not has_plan:
        return None

    lines = [f"\n### This Episode in the Season Map (slot {slot.slot_number})"]
    lines.append("The season was planned ahead; use this plan as guidance for the episode.")
    if (slot.logline or "").strip():
        lines.append(f"**Logline:** {slot.logline.strip()}")
    if (slot.arc_function or "").strip():
        lines.append(f"**Function in the season arc:** {slot.arc_function.strip()}")
    if states:
        lines.append("**Character states at the end of this episode:**")
        for name, state in states.items():
            lines.append(f"- {name}: {state}")
    if (slot.cliffhanger or "").strip():
        lines.append(f"**Planned cliffhanger / out:** {slot.cliffhanger.strip()}")
    return "\n".join(lines)


def build_bible_context(db: Session, project: Project) -> Optional[str]:
    """Build bible context string for episode projects. Returns None for standalone films."""
    if not project.show_id:
        return None

    show = db.query(Show).filter(Show.id == str(project.show_id)).first()
    if not show:
        return None

    # In connected mode, compute prior episodes first so a show with an empty
    # bible but non-empty prior summaries still emits the Prior Episodes block.
    # VARCHAR(20) column -- compare to the string .value, NOT the enum object
    # (comparing to the enum object would silently never match).
    prior_block = None
    if show.continuity_mode == ContinuityMode.CONNECTED.value:
        prior_block = _build_prior_episodes_block(db, show, project)

    # Phase 4 (temporadas): a non-empty season arc_summary supersedes the show's
    # bible_season_arc for this season's episodes; the slot plan is injected as
    # its own block.
    season_arc = show.bible_season_arc
    if project.season_id:
        season = db.query(Season).filter(Season.id == str(project.season_id)).first()
        if season and (season.arc_summary or "").strip():
            season_arc = season.arc_summary
    slot_block = _build_slot_block(db, project)

    # Check if there's any actual bible content or duration
    has_bible_content = any([
        show.bible_characters, show.bible_world_setting,
        season_arc, show.bible_tone_style
    ])
    # Return None only when the bible is empty AND there is no slot plan or priors.
    if not has_bible_content and not show.episode_duration_minutes and not prior_block and not slot_block:
        return None

    parts = []
    parts.append("## Series Bible Context")
    parts.append(f"**Show:** {show.title}")

    if show.episode_duration_minutes:
        parts.append(f"**Target Episode Duration:** {show.episode_duration_minutes} minutes")

    if show.bible_characters:
        parts.append(f"\n### Characters\n{show.bible_characters}")

    if show.bible_world_setting:
        parts.append(f"\n### World & Setting\n{show.bible_world_setting}")

    if season_arc:
        parts.append(f"\n### Season Arc\n{season_arc}")

    if show.bible_tone_style:
        parts.append(f"\n### Tone & Style\n{show.bible_tone_style}")

    if slot_block:
        parts.append(slot_block)

    if prior_block:
        parts.append(prior_block)

    return "\n".join(parts)
