# backend/app/tests/test_episode_summary_staleness.py
"""
Integration tests for ESUM-02: episode-summary staleness hook.

Mirrors test_staleness.py (breakdown_stale). Verifies that
episode_summary_stale=True is set on a Project when:
  - PATCH phase_data for a write or scenes phase
  - AND the Project already has a non-empty episode_summary (existence gating, D-02)

And that episode_summary_stale is NOT set when:
  - the episode_summary is empty/null (nothing to invalidate)
  - the edited phase is not write/scenes (phase gating)

Standalone projects (show_id NULL) follow the SAME existence gate -- the hook
keys on summary existence, not show linkage.

Idempotency of the boot migration is asserted by STATIC FILE INSPECTION of
011_continuity_columns.sql (every ADD COLUMN uses IF NOT EXISTS). The test
fixture is SQLite-backed (conftest.py SQLALCHEMY_TEST_DATABASE_URL = "sqlite://"),
which cannot execute Postgres-style `ADD COLUMN IF NOT EXISTS`; the DEFINITIVE
runtime idempotency proof is 67-01/Task 1's grep gate, not this test.

The Project read schema is asserted to surface episode_summary_stale (read-only)
while keeping episode_summary text internal (D-04).
"""

import os
import uuid

from app.models.database import Project
from app.models import schemas

MOCK_USER_ID = "12345678-1234-5678-1234-567812345678"

_MIGRATION_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "migrations", "delta",
    "011_continuity_columns.sql",
)


def _create_project_via_api(client, mock_auth_headers, title="ESum Test Project"):
    """Create a project through the API to ensure correct owner_id handling in SQLite."""
    resp = client.post(
        "/api/projects/",
        json={"title": title, "framework": "three_act"},
        headers=mock_auth_headers,
    )
    assert resp.status_code == 200, f"Project creation failed: {resp.json()}"
    return resp.json()["id"]


def _set_episode_summary(db_session, project_id, summary):
    """Set a project's episode_summary directly and commit."""
    project = db_session.query(Project).filter(Project.id == project_id).first()
    project.episode_summary = summary
    db_session.commit()


def _set_show_id(db_session, project_id, show_id):
    """Set a project's show_id directly and commit (None = standalone)."""
    project = db_session.query(Project).filter(Project.id == project_id).first()
    project.show_id = show_id
    db_session.commit()


def _make_phase_data(db_session, project_id, phase, subsection_key="main_content"):
    """Create a PhaseData row. Return phase_data."""
    from app.models.database import PhaseData
    pd = PhaseData(
        id=str(uuid.uuid4()),
        project_id=project_id,
        phase=phase,
        subsection_key=subsection_key,
        content={"some": "data"},
    )
    db_session.add(pd)
    db_session.flush()
    db_session.commit()
    return pd


def _get_project(db_session, project_id):
    """Load a fresh Project object from db for assertion."""
    db_session.expire_all()
    return db_session.query(Project).filter(Project.id == project_id).first()


class TestEpisodeSummaryStaleness:
    """ESUM-02: episode-summary staleness hook wiring."""

    # ----------------------------------------------------------------
    # 1. PATCH write phase WITH a non-empty summary sets stale
    # ----------------------------------------------------------------
    def test_patch_write_with_summary_sets_stale(self, client, db_session, mock_auth_headers):
        """PATCH write phase sets episode_summary_stale=True when a summary exists."""
        project_id = _create_project_via_api(client, mock_auth_headers)
        _set_episode_summary(db_session, project_id, "A prior episode summary.")
        pd = _make_phase_data(db_session, project_id, "write", "screenplay_editor")

        resp = client.patch(
            f"/api/phase-data/{project_id}/write/{pd.subsection_key}",
            json={"content": {"draft": "Updated screenplay content"}},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200, resp.text

        project = _get_project(db_session, project_id)
        assert project.episode_summary_stale is True

    # ----------------------------------------------------------------
    # 2. PATCH write phase WITHOUT a summary stays False (existence gating, D-02)
    # ----------------------------------------------------------------
    def test_patch_write_no_summary_stays_false(self, client, db_session, mock_auth_headers):
        """PATCH write phase does NOT set stale when episode_summary is empty/null."""
        project_id = _create_project_via_api(client, mock_auth_headers)
        # Leave episode_summary as NULL (the default).
        pd = _make_phase_data(db_session, project_id, "write", "screenplay_editor")

        resp = client.patch(
            f"/api/phase-data/{project_id}/write/{pd.subsection_key}",
            json={"content": {"draft": "Updated screenplay content"}},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200, resp.text

        project = _get_project(db_session, project_id)
        assert project.episode_summary_stale is False

        # Empty-string (whitespace-only) summary is also treated as absent.
        _set_episode_summary(db_session, project_id, "   ")
        resp = client.patch(
            f"/api/phase-data/{project_id}/write/{pd.subsection_key}",
            json={"content": {"draft": "More content"}},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200, resp.text
        project = _get_project(db_session, project_id)
        assert project.episode_summary_stale is False

    # ----------------------------------------------------------------
    # 3. PATCH non-write/scenes phase never sets stale (phase gating)
    # ----------------------------------------------------------------
    def test_patch_story_phase_no_stale(self, client, db_session, mock_auth_headers):
        """PATCH story phase does NOT set stale even with a non-empty summary."""
        project_id = _create_project_via_api(client, mock_auth_headers)
        _set_episode_summary(db_session, project_id, "A prior episode summary.")
        pd = _make_phase_data(db_session, project_id, "story", "premise")

        resp = client.patch(
            f"/api/phase-data/{project_id}/story/{pd.subsection_key}",
            json={"content": {"premise": "A story about something"}},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200, resp.text

        project = _get_project(db_session, project_id)
        assert project.episode_summary_stale is False

    # ----------------------------------------------------------------
    # 4. Standalone projects (show_id NULL) follow the SAME existence gate
    # ----------------------------------------------------------------
    def test_standalone_project_keys_on_summary_existence(self, client, db_session, mock_auth_headers):
        """Standalone (show_id None): summary present flips True; no summary stays False.

        Proves the hook is gated on episode_summary existence, NOT show linkage.
        """
        # Standalone WITH a summary -> flips True on a write edit.
        with_summary_id = _create_project_via_api(client, mock_auth_headers, "Standalone With Summary")
        _set_show_id(db_session, with_summary_id, None)
        _set_episode_summary(db_session, with_summary_id, "Standalone episode summary.")
        pd_with = _make_phase_data(db_session, with_summary_id, "write", "screenplay_editor")

        resp = client.patch(
            f"/api/phase-data/{with_summary_id}/write/{pd_with.subsection_key}",
            json={"content": {"draft": "Edit"}},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200, resp.text
        assert _get_project(db_session, with_summary_id).show_id is None
        assert _get_project(db_session, with_summary_id).episode_summary_stale is True

        # Standalone WITHOUT a summary -> stays False.
        no_summary_id = _create_project_via_api(client, mock_auth_headers, "Standalone No Summary")
        _set_show_id(db_session, no_summary_id, None)
        pd_no = _make_phase_data(db_session, no_summary_id, "write", "screenplay_editor")

        resp = client.patch(
            f"/api/phase-data/{no_summary_id}/write/{pd_no.subsection_key}",
            json={"content": {"draft": "Edit"}},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200, resp.text
        assert _get_project(db_session, no_summary_id).show_id is None
        assert _get_project(db_session, no_summary_id).episode_summary_stale is False

    # ----------------------------------------------------------------
    # 5. Migration idempotency -- STATIC inspection (SQLite cannot run PG DDL)
    # ----------------------------------------------------------------
    def test_migration_idempotency_static(self):
        """Every ADD COLUMN in 011_continuity_columns.sql uses IF NOT EXISTS.

        The db_session fixture is SQLite-backed (conftest.py
        SQLALCHEMY_TEST_DATABASE_URL = "sqlite://"), which cannot execute
        Postgres `ADD COLUMN IF NOT EXISTS`. This is therefore a STRUCTURAL
        check. The DEFINITIVE runtime idempotency proof is 67-01/Task 1's
        grep gate (all column adds use `ADD COLUMN IF NOT EXISTS`), not this
        SQLite-bound test.
        """
        with open(os.path.normpath(_MIGRATION_PATH), "r") as f:
            lines = f.read().splitlines()

        add_column_stmts = [
            ln for ln in lines
            if not ln.strip().startswith("--") and "ADD COLUMN" in ln.upper()
        ]
        assert add_column_stmts, "expected at least one ADD COLUMN statement"
        for stmt in add_column_stmts:
            assert "ADD COLUMN IF NOT EXISTS" in stmt.upper(), (
                f"non-idempotent ADD COLUMN (missing IF NOT EXISTS): {stmt!r}"
            )

    # ----------------------------------------------------------------
    # 6. Read schema surfaces the flag but NOT the summary text (D-04)
    # ----------------------------------------------------------------
    def test_read_schema_surfaces_flag_not_text(self):
        """Project read schema includes episode_summary_stale, excludes episode_summary."""
        # Schema-field assertions
        assert "episode_summary_stale" in schemas.Project.model_fields
        assert "episode_summary" not in schemas.Project.model_fields

        # Serialize an ORM-like object and confirm the dumped surface.
        class _FakeProject:
            id = uuid.UUID(MOCK_USER_ID)
            owner_id = uuid.UUID(MOCK_USER_ID)
            title = "Read Surface Test"
            framework = None
            template = None
            current_phase = None
            template_config = {}
            storyboard_style = None
            created_at = __import__("datetime").datetime.utcnow()
            updated_at = None
            show_id = None
            episode_number = None
            episode_summary = "INTERNAL SUMMARY -- must not leak"
            episode_summary_stale = True
            sections = []

        dumped = schemas.Project.model_validate(_FakeProject()).model_dump()
        assert dumped["episode_summary_stale"] is True
        assert "episode_summary" not in dumped
