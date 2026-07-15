# backend/app/tests/test_missing_priors.py

"""
Tests for on-demand first-time generation of prior-episode summaries
(generate_missing_priors).

This closes the gap that made the agent chat unable to answer about earlier
episodes: prior episodes were never eagerly summarized (the summary endpoint is
never called from the UI), and regenerate_stale_priors only REFRESHES existing
summaries. generate_missing_priors creates the first summary for strictly-prior
episodes that have written screenplay text but no episode_summary yet.

Mocking pattern mirrors test_episode_summary.py: template_ai_service is a
module-level singleton; chat_completion is patched where summarize_episode reads it.
"""

import uuid
from unittest.mock import patch, AsyncMock

from app.models.database import Project, Show, ScreenplayContent
from app.utils.episode_summary import generate_missing_priors

MOCK_USER_ID = "00000000-0000-0000-0000-000000000001"


def _create_show(db_session, **overrides):
    defaults = {
        "id": str(uuid.uuid4()),
        "owner_id": MOCK_USER_ID,
        "title": "Test Series",
        "continuity_mode": "connected",
    }
    defaults.update(overrides)
    show = Show(**defaults)
    db_session.add(show)
    db_session.flush()
    return show


def _create_episode(db_session, show, number, **overrides):
    defaults = {
        "id": str(uuid.uuid4()),
        "owner_id": MOCK_USER_ID,
        "title": f"Episode {number}",
        "show_id": str(show.id),
        "episode_number": number,
    }
    defaults.update(overrides)
    project = Project(**defaults)
    db_session.add(project)
    db_session.flush()
    return project


def _add_screenplay(db_session, project_id, text, episode_index=0):
    row = ScreenplayContent(
        id=str(uuid.uuid4()),
        project_id=str(project_id),
        content=text,
        formatted_content={"episode_index": episode_index},
        version=1,
    )
    db_session.add(row)
    db_session.commit()


def _reload(db_session, project_id):
    db_session.expire_all()
    return db_session.query(Project).filter(Project.id == str(project_id)).first()


class TestGenerateMissingPriors:
    def test_generates_first_summary_for_prior_with_text(self, db_session):
        """Ep1 has screenplay but no summary; from Ep3's chat it must be created."""
        show = _create_show(db_session)
        ep1 = _create_episode(db_session, show, 1)
        ep3 = _create_episode(db_session, show, 3)
        _add_screenplay(db_session, ep1.id, "INT. LAB - DAY\nWalter cooks.")

        with patch(
            "app.services.template_ai_service.chat_completion",
            new_callable=AsyncMock,
            return_value="Walter starts cooking; tension with Jesse established.",
        ):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                generate_missing_priors(db_session, show, ep3)
            )

        ep1_after = _reload(db_session, ep1.id)
        assert ep1_after.episode_summary == "Walter starts cooking; tension with Jesse established."
        assert ep1_after.episode_summary_stale is False

    def test_prior_without_text_is_left_null(self, db_session):
        """A prior with no screenplay text gets no summary (summarize returns '')."""
        show = _create_show(db_session)
        ep1 = _create_episode(db_session, show, 1)  # no screenplay
        ep3 = _create_episode(db_session, show, 3)

        with patch(
            "app.services.template_ai_service.chat_completion",
            new_callable=AsyncMock,
            return_value="should not be written",
        ):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                generate_missing_priors(db_session, show, ep3)
            )

        ep1_after = _reload(db_session, ep1.id)
        assert ep1_after.episode_summary is None

    def test_does_not_touch_later_or_current_episodes(self, db_session):
        """Only strictly-prior episodes are summarized, never the current or later ones."""
        show = _create_show(db_session)
        ep3 = _create_episode(db_session, show, 3)
        ep5 = _create_episode(db_session, show, 5)
        _add_screenplay(db_session, ep3.id, "INT. CURRENT - DAY\nStuff happens.")
        _add_screenplay(db_session, ep5.id, "INT. LATER - DAY\nMore stuff.")

        with patch(
            "app.services.template_ai_service.chat_completion",
            new_callable=AsyncMock,
            return_value="a summary",
        ):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                generate_missing_priors(db_session, show, ep3)
            )

        assert _reload(db_session, ep3.id).episode_summary is None
        assert _reload(db_session, ep5.id).episode_summary is None

    def test_ai_failure_on_one_prior_does_not_abort(self, db_session):
        """A per-prior AI failure is swallowed; the chat proceeds (no exception)."""
        show = _create_show(db_session)
        ep1 = _create_episode(db_session, show, 1)
        ep2 = _create_episode(db_session, show, 2)
        ep3 = _create_episode(db_session, show, 3)
        _add_screenplay(db_session, ep1.id, "INT. ONE - DAY\nA.")
        _add_screenplay(db_session, ep2.id, "INT. TWO - DAY\nB.")

        calls = {"n": 0}

        async def _flaky(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("embeddings/LLM down")
            return "second summary ok"

        with patch(
            "app.services.template_ai_service.chat_completion",
            new=_flaky,
        ):
            import asyncio
            # Must not raise despite the first prior failing.
            asyncio.get_event_loop().run_until_complete(
                generate_missing_priors(db_session, show, ep3)
            )

        # One prior failed (stays null), the other succeeded.
        summaries = {
            _reload(db_session, ep1.id).episode_summary,
            _reload(db_session, ep2.id).episode_summary,
        }
        assert "second summary ok" in summaries
        assert None in summaries
