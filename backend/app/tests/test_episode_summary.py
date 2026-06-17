# backend/app/tests/test_episode_summary.py
"""
Phase 69 — Auto Episode Summary & Lazy Regeneration (ESUM-01, ESUM-03).

Shared scaffolding for both Plan 69-01 (eager initial generation) and Plan 69-02
(lazy regenerate-before-read). All AI provider calls are mocked offline via
``_patch_chat_completion`` — these tests must NEVER hit a live provider.

Test keys (so the VALIDATION.md ``-k`` selectors resolve):
  initial         — ESUM-01 eager generation (endpoint + service summarizer call)
  by_index        — source text reconstructed strictly by episode_index (not positional)
  lazy_regen      — ESUM-03 stale prior regenerated before connected read (Plan 69-02)
  preserves_fresh — up-to-date prior NOT regenerated (Plan 69-02)
  regen_failure   — regen failure leaves stale=True + Phase 68 marker (Plan 69-02)
  existence_gate  — summary-less prior not regenerated (Plan 69-02)
"""

import uuid
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

from app.models.database import Project, Show, ScreenplayContent

MOCK_USER_ID = "12345678-1234-5678-1234-567812345678"


# ---------------------------------------------------------------------------
# Setup helpers (mirror test_bible_injection.py / test_episode_summary_staleness.py)
# ---------------------------------------------------------------------------

def _create_show(db_session, **overrides):
    """Create a Show record with optional overrides (mirrors test_bible_injection)."""
    defaults = {
        "id": str(uuid.uuid4()),
        "owner_id": MOCK_USER_ID,
        "title": "Breaking Bad",
        "description": "A chemistry teacher turns to meth cooking",
        "bible_characters": "Walter White - chemistry teacher turned drug lord",
        "bible_world_setting": "Albuquerque, New Mexico",
        "bible_season_arc": "Walter's descent from teacher to Heisenberg",
        "bible_tone_style": "Dark, tense, morally complex",
        "episode_duration_minutes": 47,
    }
    defaults.update(overrides)
    show = Show(**defaults)
    db_session.add(show)
    db_session.flush()
    return show


def _create_project(db_session, show=None, **overrides):
    """Create a Project record, optionally linked to a show."""
    defaults = {
        "id": str(uuid.uuid4()),
        "owner_id": MOCK_USER_ID,
        "title": "Pilot Episode",
    }
    if show:
        defaults["show_id"] = str(show.id)
        defaults["episode_number"] = 1
    defaults.update(overrides)
    project = Project(**defaults)
    db_session.add(project)
    db_session.flush()
    return project


def _create_project_via_api(client, mock_auth_headers, title="ESum Test Project"):
    """Create a project through the API (correct owner_id handling in SQLite)."""
    resp = client.post(
        "/api/projects/",
        json={"title": title, "framework": "three_act"},
        headers=mock_auth_headers,
    )
    assert resp.status_code == 200, f"Project creation failed: {resp.json()}"
    return resp.json()["id"]


def _insert_screenplay_content(db_session, project_id, episode_index, content):
    """Insert a ScreenplayContent row carrying formatted_content.episode_index.

    episode_index is the ONLY reliable join key (project memory: positional reads
    bit the project twice — v6.0 WR-01, v7.0 ph50). Tests insert rows out-of-order
    to prove the read reconstructs by episode_index, never by insertion order.
    """
    row = ScreenplayContent(
        id=str(uuid.uuid4()),
        project_id=str(project_id),
        content=content,
        formatted_content={"episode_index": episode_index},
    )
    db_session.add(row)
    db_session.flush()
    db_session.commit()
    return row


def _get_project(db_session, project_id):
    """Load a fresh Project object from db for assertion."""
    db_session.expire_all()
    return db_session.query(Project).filter(Project.id == str(project_id)).first()


@contextmanager
def _patch_chat_completion(return_value="A bounded prose episode summary."):
    """Patch the chat_completion symbol imported into template_ai_service with an
    AsyncMock so summary tests are deterministic and offline (NEVER a live call).

    Yields the AsyncMock so tests can assert call kwargs (json_mode, max_tokens, ...).
    Pass an Exception instance/class as ``side_effect`` via the returned mock for
    failure-path tests (Plan 69-02 regen_failure).
    """
    mock = AsyncMock(return_value=return_value)
    with patch(
        "app.services.template_ai_service.chat_completion",
        mock,
    ):
        yield mock


# ---------------------------------------------------------------------------
# Sanity: the mock helper patches the right symbol
# ---------------------------------------------------------------------------

class TestScaffoldSanity:
    """Wave 0 sanity: helpers import and the provider patch works offline."""

    def test_patch_chat_completion_patches_offline(self):
        """_patch_chat_completion replaces template_ai_service.chat_completion."""
        import app.services.template_ai_service as svc_mod

        with _patch_chat_completion(return_value="STUBBED") as mock:
            assert svc_mod.chat_completion is mock
        # patch is undone on exit
        assert svc_mod.chat_completion is not mock

    def test_insert_screenplay_content_carries_episode_index(self, db_session):
        """_insert_screenplay_content writes a row with formatted_content.episode_index."""
        show = _create_show(db_session)
        project = _create_project(db_session, show=show)
        row = _insert_screenplay_content(db_session, project.id, 0, "INT. LAB - DAY")
        assert row.formatted_content.get("episode_index") == 0
        assert row.content == "INT. LAB - DAY"
