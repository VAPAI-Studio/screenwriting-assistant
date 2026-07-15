# backend/app/utils/episode_summary.py

"""
Lazy regeneration of stale prior-episode summaries (ESUM-03).

Phase 69 closes the continuity loop: any prior episode whose ``episode_summary``
was marked stale (Phase 67's ``episode_summary_stale`` flag) is regenerated
JUST-IN-TIME, before it is read as prior-episode context for a LATER episode of
the same connected show.

``regenerate_stale_priors`` is an async pre-pass intended to run in the connected-
mode generation flow (``wizards.py::run_wizard``) IMMEDIATELY BEFORE the synchronous
``build_bible_context(db, project)`` reads the rows, so the reader sees fresh text.

Design constraints (RESEARCH §Patterns 3 + Pitfalls 4 & 6):
  * Query shape mirrors ``bible_context._build_prior_episodes_block`` — strictly-prior
    episodes (episode_number < current) scoped to THIS project's own show_id (T-69-04),
    ordered by episode_number ascending (never positional).
  * Existence-gate: only regenerate priors that already have a non-empty summary
    (SC-3 — a summary-less prior is never auto-summarised here; that is ESUM-01's job).
  * Up-to-date priors (stale=False) are never touched (SC-3).
  * Per-prior try/except: on AI failure leave ``episode_summary_stale=True`` so Phase 68
    injects the stale text WITH its ``(summary may be out of date)`` marker — generation
    NEVER fails (T-69-05 / D-REGEN-FAIL).
  * Caller-commits convention is honoured by ``summarize_episode`` (it does not write);
    this pre-pass owns the single ``db.commit()`` after the loop.
"""

import logging

from ..models.database import EpisodeSlot, Project
from ..services.template_ai_service import template_ai_service

logger = logging.getLogger(__name__)


def mark_linked_slot_plan_stale(db, project_id) -> None:
    """Phase 4 (temporadas): flag the episode's slot plan as stale.

    Called wherever an episode_summary is (re)generated — the summary is a fresh
    snapshot of the WRITTEN episode, so the slot's plan may no longer match and
    the season map shows a reconcile badge. No-op for unslotted episodes.
    Caller-commits convention: this does NOT commit.
    """
    slot = db.query(EpisodeSlot).filter(
        EpisodeSlot.project_id == str(project_id)
    ).first()
    if slot:
        slot.plan_stale = True


async def generate_missing_priors(db, show, project) -> None:
    """Generate first-time summaries for strictly-prior episodes that have written
    screenplay text but no ``episode_summary`` yet (ESUM-01, on-demand).

    Complements ``regenerate_stale_priors`` (which only REFRESHES existing summaries):
    without this pre-pass, an episode whose summary was never eagerly created stays
    invisible to later episodes' continuity context. Mirrors the prior-episode query
    shape (strictly-prior, same show_id, episode_number ASC — never positional).

    ``summarize_episode`` returns "" when the prior has no source screenplay text; in
    that case nothing is written (a summary-less, text-less prior simply contributes
    no context). Per-prior try/except so one AI failure never aborts the chat. Commits
    once after the loop (caller-commits convention is honoured by ``summarize_episode``).
    """
    if project.episode_number is None:
        return

    missing_priors = (
        db.query(Project)
        .filter(
            Project.show_id == str(show.id),
            Project.episode_number < project.episode_number,
            Project.episode_summary.is_(None),
        )
        .order_by(Project.episode_number.asc())
        .all()
    )

    wrote_any = False
    for prior in missing_priors:
        try:
            fresh = await template_ai_service.summarize_episode(db, prior)
            if fresh:
                prior.episode_summary = fresh
                prior.episode_summary_stale = False
                mark_linked_slot_plan_stale(db, prior.id)
                wrote_any = True
            # summarize_episode returns "" when the prior has no screenplay text —
            # leave episode_summary NULL rather than writing an empty string.
        except Exception as exc:  # noqa: BLE001 -- degrade gracefully, never abort the chat
            logger.warning(
                "On-demand episode-summary generation failed for ep %s: %s",
                prior.episode_number,
                exc,
            )

    if wrote_any:
        db.commit()


async def regenerate_stale_priors(db, show, project) -> None:
    """Regenerate stale prior-episode summaries for ``project``'s connected show.

    No-op when ``project.episode_number`` is None (``< None`` is undefined). Queries
    strictly-prior episodes of ``show`` flagged stale with a non-null summary, applies
    the existence-gate, regenerates each via ``template_ai_service.summarize_episode``,
    clears the flag on success, and on per-prior AI failure leaves the flag True (no
    exception escapes). Commits once after the loop.
    """
    # episode_number is nullable; `< None` is undefined -- guard it (mirrors
    # _build_prior_episodes_block).
    if project.episode_number is None:
        return

    stale_priors = (
        db.query(Project)
        .filter(
            Project.show_id == str(show.id),
            Project.episode_number < project.episode_number,
            Project.episode_summary.isnot(None),
            Project.episode_summary_stale.is_(True),
        )
        .order_by(Project.episode_number.asc())  # reliable integer key (never positional)
        .all()
    )

    for prior in stale_priors:
        # Existence-gate: never regenerate a summary-less prior (SC-3). The column may
        # be a non-null but empty/whitespace string.
        if not (prior.episode_summary or "").strip():
            continue
        try:
            fresh = await template_ai_service.summarize_episode(db, prior)
            if fresh:
                prior.episode_summary = fresh
                prior.episode_summary_stale = False
                mark_linked_slot_plan_stale(db, prior.id)
            # If the summarizer returns "" (no source text), leave the existing
            # summary + flag untouched rather than clobbering with empty.
        except Exception as exc:  # noqa: BLE001 -- degrade gracefully, never abort generation
            logger.warning(
                "Lazy episode-summary regen failed for ep %s: %s",
                prior.episode_number,
                exc,
            )
            # Leave episode_summary_stale=True -> Phase 68 injects the stale text WITH
            # its existing marker (graceful degradation; generation proceeds).

    db.commit()
