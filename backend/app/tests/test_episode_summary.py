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


# ---------------------------------------------------------------------------
# Task 2 — _read_episode_text_by_index + summarize_episode (ESUM-01 service)
# ---------------------------------------------------------------------------

class TestReadEpisodeTextByIndex:
    """Source text is reconstructed strictly by episode_index, never positionally."""

    def test_by_index_reconstructs_in_episode_index_order(self, db_session):
        """Rows inserted with SHUFFLED episode_index reconstruct in ascending order.

        Positional / created_at-order reads would FAIL this assertion because the
        rows are inserted out of episode_index order.
        """
        from app.services.template_ai_service import _read_episode_text_by_index

        project = _create_project(db_session)
        # Insert OUT of order: index 2 first, then 0, then 1.
        _insert_screenplay_content(db_session, project.id, 2, "SCENE TWO")
        _insert_screenplay_content(db_session, project.id, 0, "SCENE ZERO")
        _insert_screenplay_content(db_session, project.id, 1, "SCENE ONE")

        text = _read_episode_text_by_index(db_session, project.id)
        assert text == "SCENE ZERO\n\nSCENE ONE\n\nSCENE TWO"

    def test_by_index_skips_missing_index_and_empty_content(self, db_session):
        """Rows lacking episode_index or with empty content are skipped."""
        from app.services.template_ai_service import _read_episode_text_by_index

        project = _create_project(db_session)
        _insert_screenplay_content(db_session, project.id, 0, "REAL SCENE")
        # Row with empty content at a valid index -> skipped.
        _insert_screenplay_content(db_session, project.id, 1, "")
        # Row with no episode_index in formatted_content -> skipped.
        noidx = ScreenplayContent(
            id=str(uuid.uuid4()),
            project_id=str(project.id),
            content="ORPHAN",
            formatted_content={},
        )
        db_session.add(noidx)
        db_session.commit()

        text = _read_episode_text_by_index(db_session, project.id)
        assert text == "REAL SCENE"

    def test_by_index_dedupes_duplicate_index_to_one_value(self, db_session):
        """Duplicate episode_index collapses to exactly ONE value (de-duped).

        Which duplicate wins is best-effort (created_at.desc tiebreaker): on SQLite
        created_at is only second-resolution and ids are random UUIDs, so insertion
        order is not reliably recoverable — the breakdown_service precedent documents
        the same limitation. The deterministic, meaningful guarantee is that a
        duplicate index yields a SINGLE scene value, not a doubled one.
        """
        from app.services.template_ai_service import _read_episode_text_by_index

        project = _create_project(db_session)
        _insert_screenplay_content(db_session, project.id, 0, "FIRST VERSION")
        _insert_screenplay_content(db_session, project.id, 0, "SECOND VERSION")
        text = _read_episode_text_by_index(db_session, project.id)
        assert text in ("FIRST VERSION", "SECOND VERSION")
        assert "\n\n" not in text  # only one scene value, not both joined


class TestSummarizeEpisodeService:
    """summarize_episode is bounded prose via chat_completion(json_mode=False)."""

    def test_initial_summarizer_calls_chat_completion_bounded_prose(self, db_session):
        """summarize_episode calls chat_completion(json_mode=False, max_tokens~500) and
        returns the stripped provider text — not the full script."""
        import asyncio
        from app.services.template_ai_service import template_ai_service

        project = _create_project(db_session, title="The Heist")
        _insert_screenplay_content(db_session, project.id, 0, "INT. VAULT - NIGHT\nThe crew breaks in.")

        with _patch_chat_completion(return_value="  Walt robs the vault.  ") as mock:
            result = asyncio.run(template_ai_service.summarize_episode(db_session, project))

        assert result == "Walt robs the vault."  # stripped
        assert mock.await_count == 1
        _, kwargs = mock.call_args
        assert kwargs.get("json_mode") is False
        assert 400 <= kwargs.get("max_tokens", 0) <= 600  # bounded ~500
        # The prompt instructs a bounded prose summary, not the full script.
        prompt = mock.call_args.kwargs["messages"][-1]["content"]
        assert "The Heist" in prompt  # project title injected
        assert "INT. VAULT" in prompt  # source scene text injected

    def test_initial_summarizer_empty_source_returns_empty(self, db_session):
        """Empty/whitespace source text returns "" with no provider call required."""
        import asyncio
        from app.services.template_ai_service import template_ai_service

        project = _create_project(db_session, title="No Scenes")
        # No ScreenplayContent rows at all -> empty source text.
        with _patch_chat_completion(return_value="should not be used") as mock:
            result = asyncio.run(template_ai_service.summarize_episode(db_session, project))
        assert result == ""
        assert mock.await_count == 0

    def test_initial_summarizer_does_not_commit_or_mutate_project(self, db_session):
        """summarize_episode performs no commit and does not set project.episode_summary
        (caller owns the write — Phase 67 convention)."""
        import asyncio
        from app.services.template_ai_service import template_ai_service

        project = _create_project(db_session, title="Caller Commits")
        _insert_screenplay_content(db_session, project.id, 0, "INT. ROOM - DAY")

        with _patch_chat_completion(return_value="A summary."):
            asyncio.run(template_ai_service.summarize_episode(db_session, project))

        assert project.episode_summary is None  # helper did not write
        # Flag untouched (defaults False); helper did not clear/set it.
        assert project.episode_summary_stale in (False, None)


# ---------------------------------------------------------------------------
# Task 3 — POST /api/projects/{id}/episode-summary eager trigger (ESUM-01)
# ---------------------------------------------------------------------------

class TestEpisodeSummaryEndpoint:
    """ESUM-01: owner-scoped eager trigger writes + clears + commits."""

    def test_initial_endpoint_generates_stores_and_clears_flag(
        self, client, db_session, mock_auth_headers
    ):
        """POST returns 200 for an owned project, stores a non-empty episode_summary,
        sets episode_summary_stale=False, and commits."""
        project_id = _create_project_via_api(client, mock_auth_headers, "Endpoint Owned")
        # Pre-set stale=True so we can prove the endpoint clears it.
        project = _get_project(db_session, project_id)
        project.episode_summary_stale = True
        db_session.commit()
        _insert_screenplay_content(db_session, project_id, 0, "INT. OFFICE - DAY\nThe pitch.")

        with _patch_chat_completion(return_value="Generated episode summary.") as mock:
            resp = client.post(
                f"/api/projects/{project_id}/episode-summary",
                headers=mock_auth_headers,
            )

        assert resp.status_code == 200, resp.text
        assert mock.await_count == 1
        body = resp.json()
        assert body["episode_summary_stale"] is False

        refreshed = _get_project(db_session, project_id)
        assert refreshed.episode_summary == "Generated episode summary."
        assert refreshed.episode_summary_stale is False

    def test_initial_endpoint_cross_owner_returns_404(
        self, client, db_session, mock_auth_headers
    ):
        """A project owned by another user returns 404 (no cross-user write)."""
        other_project = _create_project(
            db_session, owner_id=str(uuid.uuid4()), title="Someone Else's Episode"
        )
        db_session.commit()
        _insert_screenplay_content(db_session, other_project.id, 0, "INT. SECRET - NIGHT")

        with _patch_chat_completion(return_value="should not run") as mock:
            resp = client.post(
                f"/api/projects/{other_project.id}/episode-summary",
                headers=mock_auth_headers,
            )

        assert resp.status_code == 404, resp.text
        assert mock.await_count == 0
        # No write occurred on the other user's project.
        refreshed = _get_project(db_session, other_project.id)
        assert refreshed.episode_summary is None

    def test_initial_endpoint_empty_source_does_not_clobber_existing(
        self, client, db_session, mock_auth_headers
    ):
        """When the summarizer returns "" (no source text), the endpoint returns 422
        and does NOT overwrite an existing summary with empty (documented choice)."""
        project_id = _create_project_via_api(client, mock_auth_headers, "Empty Source")
        project = _get_project(db_session, project_id)
        project.episode_summary = "An existing, valuable summary."
        db_session.commit()
        # No ScreenplayContent rows -> summarizer returns "".

        with _patch_chat_completion(return_value="unused") as mock:
            resp = client.post(
                f"/api/projects/{project_id}/episode-summary",
                headers=mock_auth_headers,
            )

        assert resp.status_code == 422, resp.text
        refreshed = _get_project(db_session, project_id)
        # Existing summary preserved (not clobbered with empty).
        assert refreshed.episode_summary == "An existing, valuable summary."

    def test_read_schema_does_not_expose_episode_summary_text(self):
        """D-04 preserved: the Project read schema does not expose episode_summary."""
        from app.models import schemas

        assert "episode_summary_stale" in schemas.Project.model_fields
        assert "episode_summary" not in schemas.Project.model_fields


# ---------------------------------------------------------------------------
# Plan 69-02 Task 1 — regenerate_stale_priors helper (ESUM-03 core + SC-3)
# ---------------------------------------------------------------------------

class TestRegenerateStalePriorsHelper:
    """regenerate_stale_priors regenerates ONLY stale-with-summary strictly-prior
    episodes of the same show, clears the flag on success, and degrades gracefully
    on AI failure (leaves the flag True, never raises)."""

    def test_existence_gate_skips_summary_less_and_regens_stale_with_summary(
        self, db_session
    ):
        """existence_gate: a stale prior WITH a non-empty summary is regenerated and
        its flag cleared; a stale prior with an empty/whitespace summary is NOT passed
        to summarize_episode (existence-gate)."""
        import asyncio
        from app.utils.episode_summary import regenerate_stale_priors

        show = _create_show(db_session, continuity_mode="connected")
        # Later episode (the one being generated).
        current = _create_project(db_session, show=show, episode_number=3, title="Ep 3")
        # Stale prior WITH a summary -> should regenerate.
        prior_has = _create_project(
            db_session, show=show, episode_number=1, title="Ep 1",
            episode_summary="Old stale summary for ep 1.", episode_summary_stale=True,
        )
        # Source text so summarize_episode has something to read.
        _insert_screenplay_content(db_session, prior_has.id, 0, "INT. EP1 - DAY\nStuff happens.")
        # Stale prior with WHITESPACE summary -> existence-gate skips it.
        prior_empty = _create_project(
            db_session, show=show, episode_number=2, title="Ep 2",
            episode_summary="   ", episode_summary_stale=True,
        )
        db_session.commit()

        with _patch_chat_completion(return_value="Fresh regenerated summary.") as mock:
            asyncio.run(regenerate_stale_priors(db_session, show, current))

        # Only the with-summary prior triggered a provider call.
        assert mock.await_count == 1

        refreshed_has = _get_project(db_session, prior_has.id)
        assert refreshed_has.episode_summary == "Fresh regenerated summary."
        assert refreshed_has.episode_summary_stale is False

        refreshed_empty = _get_project(db_session, prior_empty.id)
        # Whitespace summary untouched, flag stays True (never regenerated).
        assert refreshed_empty.episode_summary == "   "
        assert refreshed_empty.episode_summary_stale is True

    def test_preserves_fresh_does_not_touch_up_to_date_prior(self, db_session):
        """preserves_fresh (SC-3): an up-to-date prior (stale=False) is byte-identical
        after the call and triggers no provider call."""
        import asyncio
        from app.utils.episode_summary import regenerate_stale_priors

        show = _create_show(db_session, continuity_mode="connected")
        current = _create_project(db_session, show=show, episode_number=2, title="Ep 2")
        fresh_prior = _create_project(
            db_session, show=show, episode_number=1, title="Ep 1",
            episode_summary="A perfectly up-to-date summary.", episode_summary_stale=False,
        )
        _insert_screenplay_content(db_session, fresh_prior.id, 0, "INT. EP1 - DAY")
        db_session.commit()

        with _patch_chat_completion(return_value="SHOULD NOT BE USED") as mock:
            asyncio.run(regenerate_stale_priors(db_session, show, current))

        assert mock.await_count == 0
        refreshed = _get_project(db_session, fresh_prior.id)
        assert refreshed.episode_summary == "A perfectly up-to-date summary."
        assert refreshed.episode_summary_stale is False

    def test_preserves_fresh_ignores_current_and_later_episodes(self, db_session):
        """preserves_fresh: only strictly-prior episodes (episode_number < current) of
        THIS show are considered — the current and later episodes are untouched."""
        import asyncio
        from app.utils.episode_summary import regenerate_stale_priors

        show = _create_show(db_session, continuity_mode="connected")
        current = _create_project(
            db_session, show=show, episode_number=2, title="Ep 2 (current)",
            episode_summary="Current ep stale summary.", episode_summary_stale=True,
        )
        later = _create_project(
            db_session, show=show, episode_number=5, title="Ep 5 (later)",
            episode_summary="Later ep stale summary.", episode_summary_stale=True,
        )
        _insert_screenplay_content(db_session, current.id, 0, "INT. CURRENT - DAY")
        _insert_screenplay_content(db_session, later.id, 0, "INT. LATER - DAY")
        db_session.commit()

        with _patch_chat_completion(return_value="SHOULD NOT BE USED") as mock:
            asyncio.run(regenerate_stale_priors(db_session, show, current))

        # Neither current nor later is a strict prior -> no provider call.
        assert mock.await_count == 0
        assert _get_project(db_session, current.id).episode_summary_stale is True
        assert _get_project(db_session, later.id).episode_summary_stale is True

    def test_preserves_fresh_no_op_when_current_episode_number_none(self, db_session):
        """preserves_fresh: a current project with episode_number None is a no-op."""
        import asyncio
        from app.utils.episode_summary import regenerate_stale_priors

        show = _create_show(db_session, continuity_mode="connected")
        current = _create_project(db_session, show=show, title="No Number")
        current.episode_number = None
        prior = _create_project(
            db_session, show=show, episode_number=1, title="Ep 1",
            episode_summary="Stale ep 1 summary.", episode_summary_stale=True,
        )
        _insert_screenplay_content(db_session, prior.id, 0, "INT. EP1 - DAY")
        db_session.commit()

        with _patch_chat_completion(return_value="SHOULD NOT BE USED") as mock:
            asyncio.run(regenerate_stale_priors(db_session, show, current))

        assert mock.await_count == 0
        assert _get_project(db_session, prior.id).episode_summary_stale is True

    def test_regen_failure_helper_leaves_flag_true_no_raise(self, db_session):
        """regen_failure (helper-level): when summarize_episode raises for a prior, that
        prior keeps episode_summary_stale=True, the loop continues, and no exception
        escapes regenerate_stale_priors."""
        import asyncio
        from app.utils.episode_summary import regenerate_stale_priors

        show = _create_show(db_session, continuity_mode="connected")
        current = _create_project(db_session, show=show, episode_number=3, title="Ep 3")
        prior_fail = _create_project(
            db_session, show=show, episode_number=1, title="Ep 1",
            episode_summary="Stale ep 1 (regen will fail).", episode_summary_stale=True,
        )
        prior_ok = _create_project(
            db_session, show=show, episode_number=2, title="Ep 2",
            episode_summary="Stale ep 2 (regen will succeed).", episode_summary_stale=True,
        )
        _insert_screenplay_content(db_session, prior_fail.id, 0, "INT. EP1 - DAY")
        _insert_screenplay_content(db_session, prior_ok.id, 0, "INT. EP2 - DAY")
        db_session.commit()

        call_count = {"n": 0}

        async def _side_effect(*args, **kwargs):
            call_count["n"] += 1
            # First prior (ep 1) fails; the loop must continue to ep 2.
            if call_count["n"] == 1:
                raise RuntimeError("provider boom")
            return "Fresh ep 2 summary."

        with _patch_chat_completion() as mock:
            mock.side_effect = _side_effect
            # Must NOT raise.
            asyncio.run(regenerate_stale_priors(db_session, show, current))

        refreshed_fail = _get_project(db_session, prior_fail.id)
        # Failure leaves the flag True and text unchanged.
        assert refreshed_fail.episode_summary_stale is True
        assert refreshed_fail.episode_summary == "Stale ep 1 (regen will fail)."

        refreshed_ok = _get_project(db_session, prior_ok.id)
        # The loop continued and regenerated the second prior.
        assert refreshed_ok.episode_summary_stale is False
        assert refreshed_ok.episode_summary == "Fresh ep 2 summary."


# ---------------------------------------------------------------------------
# Plan 69-02 Task 2 — pre-pass + build_bible_context end-to-end (ESUM-03)
# ---------------------------------------------------------------------------
#
# These exercise the pre-pass -> build_bible_context COMPOSITION directly (the
# exact ordering run_wizard performs: regenerate_stale_priors BEFORE the sync
# build_bible_context read). Driving the full run_wizard endpoint would require
# standing up the async BackgroundTasks generation plumbing + WizardRun lifecycle,
# which is heavy and orthogonal to the ESUM-03 behavior under test; the wiring
# itself (call site + connected gate) is asserted structurally in
# TestRunWizardPrePassWiring below. (Documented choice per the plan's Task 2 note.)


class TestLazyRegenEndToEnd:
    """After the pre-pass runs in connected mode, build_bible_context for the later
    episode shows FRESH prior text with NO stale marker (lazy_regen); on regen
    failure the stale text is injected WITH the marker and generation proceeds."""

    def test_lazy_regen_fresh_text_no_marker_after_prepass(self, db_session):
        """lazy_regen: a stale-with-summary prior is regenerated before the connected
        read; build_bible_context shows the fresh text WITHOUT the
        '(summary may be out of date)' marker and the flag is cleared."""
        import asyncio
        from app.utils.episode_summary import regenerate_stale_priors
        from app.utils.bible_context import build_bible_context, STALE_SUMMARY_MARKER

        show = _create_show(db_session, continuity_mode="connected")
        current = _create_project(db_session, show=show, episode_number=2, title="Ep 2")
        prior = _create_project(
            db_session, show=show, episode_number=1, title="Ep 1",
            episode_summary="STALE original ep1 text.", episode_summary_stale=True,
        )
        _insert_screenplay_content(db_session, prior.id, 0, "INT. EP1 - DAY\nThe pilot.")
        db_session.commit()

        with _patch_chat_completion(return_value="FRESH regenerated ep1 summary.") as mock:
            asyncio.run(regenerate_stale_priors(db_session, show, current))
        assert mock.await_count == 1

        # The sync reader now sees the fresh rows (run_wizard order).
        context = build_bible_context(db_session, current)
        assert "FRESH regenerated ep1 summary." in context
        assert "STALE original ep1 text." not in context
        assert STALE_SUMMARY_MARKER not in context

        refreshed = _get_project(db_session, prior.id)
        assert refreshed.episode_summary_stale is False

    def test_regen_failure_injects_stale_with_marker_generation_proceeds(self, db_session):
        """regen_failure (end-to-end): when the provider raises during the pre-pass,
        the pre-pass leaves the flag True and does NOT raise; build_bible_context then
        injects the stale text WITH the marker (Phase 68 fallback path)."""
        import asyncio
        from app.utils.episode_summary import regenerate_stale_priors
        from app.utils.bible_context import build_bible_context, STALE_SUMMARY_MARKER

        show = _create_show(db_session, continuity_mode="connected")
        current = _create_project(db_session, show=show, episode_number=2, title="Ep 2")
        prior = _create_project(
            db_session, show=show, episode_number=1, title="Ep 1",
            episode_summary="STALE ep1 text kept on failure.", episode_summary_stale=True,
        )
        _insert_screenplay_content(db_session, prior.id, 0, "INT. EP1 - DAY")
        db_session.commit()

        with _patch_chat_completion() as mock:
            mock.side_effect = RuntimeError("provider down")
            # Pre-pass must NOT raise (generation proceeds).
            asyncio.run(regenerate_stale_priors(db_session, show, current))

        refreshed = _get_project(db_session, prior.id)
        assert refreshed.episode_summary_stale is True
        assert refreshed.episode_summary == "STALE ep1 text kept on failure."

        # Phase 68 fallback: stale text injected WITH the marker.
        context = build_bible_context(db_session, current)
        assert "STALE ep1 text kept on failure." in context
        assert STALE_SUMMARY_MARKER in context


class TestRunWizardPrePassWiring:
    """The pre-pass is wired into run_wizard BEFORE build_bible_context and gated on
    connected mode (anthology/standalone/show_id-NULL skip it)."""

    def test_lazy_regen_call_precedes_build_bible_context_in_run_wizard(self):
        """Structural: regenerate_stale_priors is called in run_wizard ABOVE the
        build_bible_context(db, project) line, and build_bible_context stays sync."""
        import inspect
        import app.api.endpoints.wizards as wiz
        import app.utils.bible_context as bc

        src = inspect.getsource(wiz.run_wizard)
        assert "regenerate_stale_priors" in src, "pre-pass not wired into run_wizard"
        regen_pos = src.index("regenerate_stale_priors")
        build_pos = src.index("build_bible_context(db, project)")
        assert regen_pos < build_pos, "regen pre-pass must precede build_bible_context"
        # The gate compares to the VARCHAR string .value, not the enum object.
        assert "ContinuityMode.CONNECTED.value" in src
        # build_bible_context remains a pure sync reader (no await added).
        assert not inspect.iscoroutinefunction(bc.build_bible_context)

    def test_existence_gate_anthology_skips_prepass(self, db_session, monkeypatch):
        """An anthology show must NOT invoke summarize_episode during the pre-pass.

        Drives the connected-mode gate logic exactly as run_wizard does: only call the
        pre-pass when show.continuity_mode == ContinuityMode.CONNECTED.value.
        """
        import asyncio
        from app.models.schemas import ContinuityMode
        from app.utils.episode_summary import regenerate_stale_priors

        show = _create_show(db_session, continuity_mode="anthology")
        current = _create_project(db_session, show=show, episode_number=2, title="Ep 2")
        prior = _create_project(
            db_session, show=show, episode_number=1, title="Ep 1",
            episode_summary="Stale ep1 in an anthology show.", episode_summary_stale=True,
        )
        _insert_screenplay_content(db_session, prior.id, 0, "INT. EP1 - DAY")
        db_session.commit()

        async def _gated_prepass():
            # Mirror run_wizard's gate.
            if show and show.continuity_mode == ContinuityMode.CONNECTED.value:
                await regenerate_stale_priors(db_session, show, current)

        with _patch_chat_completion(return_value="SHOULD NOT RUN") as mock:
            asyncio.run(_gated_prepass())

        assert mock.await_count == 0
        assert _get_project(db_session, prior.id).episode_summary_stale is True
