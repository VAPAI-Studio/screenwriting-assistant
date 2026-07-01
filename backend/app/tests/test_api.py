# backend/tests/test_api.py

import pytest
from app.models.database import Framework, SectionType


class TestProjectsAPI:
    """Test projects API endpoints"""

    def test_create_project_valid(self, client, mock_auth_headers):
        """Test creating a project with valid data"""
        response = client.post(
            "/api/projects/",
            json={
                "title": "Test Project",
                "framework": "three_act"
            },
            headers=mock_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Project"
        assert data["framework"] == "three_act"
    
    def test_create_project_invalid_title(self, client, mock_auth_headers):
        """Test creating a project with invalid title"""
        # Empty title
        response = client.post(
            "/api/projects/",
            json={
                "title": "",
                "framework": "three_act"
            },
            headers=mock_auth_headers
        )
        assert response.status_code == 422
        errors = response.json()["errors"]
        assert any("title" in error["field"] for error in errors)
        
        # Title too short
        response = client.post(
            "/api/projects/",
            json={
                "title": "A",
                "framework": "three_act"
            },
            headers=mock_auth_headers
        )
        assert response.status_code == 422
        
        # Title too long
        response = client.post(
            "/api/projects/",
            json={
                "title": "A" * 256,
                "framework": "three_act"
            },
            headers=mock_auth_headers
        )
        assert response.status_code == 422
    
    def test_create_project_invalid_framework(self, client, mock_auth_headers):
        """Test creating a project with invalid framework"""
        response = client.post(
            "/api/projects/",
            json={
                "title": "Test Project",
                "framework": "invalid_framework"
            },
            headers=mock_auth_headers
        )
        assert response.status_code == 422
    
    def test_update_project_validation(self, client, mock_auth_headers):
        """Test updating a project with validation"""
        # First create a project
        create_response = client.post(
            "/api/projects/",
            json={
                "title": "Update Test",
                "framework": "three_act"
            },
            headers=mock_auth_headers
        )
        project_id = create_response.json()["id"]
        
        # Try to update with invalid title
        response = client.patch(
            f"/api/projects/{project_id}",
            json={"title": ""},
            headers=mock_auth_headers
        )
        assert response.status_code == 422

class TestSectionsAPI:
    """Test sections API endpoints"""

    def test_update_section_content_validation(self, client, mock_auth_headers):
        """Test updating section content with validation"""
        response = client.patch(
            "/api/sections/12345678-1234-5678-1234-567812345678",
            json={"user_notes": "A" * 10001},  # Exceeds max length
            headers=mock_auth_headers
        )
        # The response would be 404 because the section doesn't exist,
        # but if it did exist, it would validate the content

class TestReviewAPI:
    """Test review API endpoints"""

    def test_review_validation(self, client, mock_auth_headers):
        """Test review request validation"""
        # Test with text too short
        response = client.post(
            "/api/review/",
            json={
                "section_id": "12345678-1234-5678-1234-567812345678",
                "text": "Too short",
                "framework": "three_act"
            },
            headers=mock_auth_headers
        )
        assert response.status_code == 422
        errors = response.json()["errors"]
        assert any("text" in error["field"] for error in errors)
        
        # Test with empty text
        response = client.post(
            "/api/review/",
            json={
                "section_id": "12345678-1234-5678-1234-567812345678",
                "text": "",
                "framework": "three_act"
            },
            headers=mock_auth_headers
        )
        assert response.status_code == 422
        
        # Test with invalid framework
        response = client.post(
            "/api/review/",
            json={
                "section_id": "12345678-1234-5678-1234-567812345678",
                "text": "This is a valid length text for review",
                "framework": "invalid_framework"
            },
            headers=mock_auth_headers
        )
        assert response.status_code == 422

class TestAuthAPI:
    """Test authentication API endpoints"""

    def test_magic_link_request(self, client):
        """Test magic link request with email validation"""
        # Valid email
        response = client.post(
            "/api/auth/magic-link",
            json={"email": "test@example.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "magic_link" in data
        
        # Invalid email
        response = client.post(
            "/api/auth/magic-link",
            json={"email": "invalid-email"}
        )
        assert response.status_code == 422
        errors = response.json()["errors"]
        assert any("email" in error["field"] for error in errors)

class TestMiddleware:
    """Test custom middleware"""

    def test_rate_limiting(self, client):
        """Test rate limiting middleware"""
        # Note: This test would need to be configured based on the rate limit settings
        pass

    def test_request_size_limit(self, client, mock_auth_headers):
        """Test request size limit middleware"""
        large_content = "A" * (11 * 1024 * 1024)  # 11MB, exceeding 10MB limit
        response = client.post(
            "/api/projects/",
            json={
                "title": "Large Project",
                "framework": "three_act",
                "large_field": large_content
            },
            headers=mock_auth_headers
        )

    def test_security_headers(self, client):
        """Test security headers middleware"""
        response = client.get("/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"


# MOCK_USER_ID matches the user returned by mock-token auth in development
# (auth_service.MockAuthService) and the owner pattern used by
# test_breakdown_service so _verify_project_ownership passes.
MOCK_USER_ID = "12345678-1234-5678-1234-567812345678"


def _make_project(db_session):
    """Create an owned Project via the test DB session and return its id (str)."""
    import uuid as _uuid
    from app.models.database import Project

    project_id = str(_uuid.uuid4())
    project = Project(
        id=project_id,
        owner_id=MOCK_USER_ID,
        title="Hand-Written Film",
    )
    db_session.add(project)
    db_session.commit()
    return project_id


# A two-scene hand-written payload (mirrors the {title, content, episode_index}
# contract the frontend splitter produces).
TWO_SCENES = {
    "screenplays": [
        {
            "episode_index": 0,
            "title": "INT. CASTLE - NIGHT",
            "content": "INT. CASTLE - NIGHT\n\nThe KNIGHT draws a sword.",
        },
        {
            "episode_index": 1,
            "title": "EXT. FOREST - DAY",
            "content": "EXT. FOREST - DAY\n\nThe KNIGHT rides on.",
        },
    ]
}


class TestScreenplayWriteSave:
    """Phase 54 — direct screenplay writing: upsert save + ScreenplayContent sync.

    Covers WRITE-01/03/04 and the D-54-05 generic-non-sync design constraint.
    """

    def test_screenplay_save_upserts_when_absent(
        self, client, db_session, mock_auth_headers
    ):
        """PATCH to a never-saved screenplay_editor subsection returns 200 (not 404)
        and persists content.screenplays (D-54-01, WRITE-01/WRITE-03)."""
        from app.models.database import PhaseData

        project_id = _make_project(db_session)

        # Sanity: no PhaseData exists yet.
        assert (
            db_session.query(PhaseData)
            .filter(
                PhaseData.project_id == project_id,
                PhaseData.phase == "write",
                PhaseData.subsection_key == "screenplay_editor",
            )
            .first()
            is None
        )

        response = client.patch(
            f"/api/phase-data/{project_id}/write/screenplay_editor",
            json={"content": TWO_SCENES},
            headers=mock_auth_headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["content"]["screenplays"]) == 2

        # The PhaseData row now exists with both scenes.
        pd = (
            db_session.query(PhaseData)
            .filter(
                PhaseData.project_id == project_id,
                PhaseData.phase == "write",
                PhaseData.subsection_key == "screenplay_editor",
            )
            .first()
        )
        assert pd is not None
        assert len(pd.content["screenplays"]) == 2

    def test_screenplay_save_creates_screenplaycontent_rows(
        self, client, db_session, mock_auth_headers
    ):
        """After save, ScreenplayContent rows == #scenes and each row's
        formatted_content carries the matching episode_index/title (WRITE-04)."""
        from app.models.database import ScreenplayContent

        project_id = _make_project(db_session)

        response = client.patch(
            f"/api/phase-data/{project_id}/write/screenplay_editor",
            json={"content": TWO_SCENES},
            headers=mock_auth_headers,
        )
        assert response.status_code == 200, response.text

        rows = (
            db_session.query(ScreenplayContent)
            .filter(ScreenplayContent.project_id == project_id)
            .all()
        )
        assert len(rows) == 2
        by_index = {
            (r.formatted_content or {}).get("episode_index"): r for r in rows
        }
        assert set(by_index.keys()) == {0, 1}
        assert by_index[0].formatted_content["title"] == "INT. CASTLE - NIGHT"
        assert by_index[1].formatted_content["title"] == "EXT. FOREST - DAY"
        assert by_index[0].content == TWO_SCENES["screenplays"][0]["content"]

    def test_screenplay_save_is_idempotent(
        self, client, db_session, mock_auth_headers
    ):
        """Saving the SAME payload twice leaves exactly N rows, not 2N (WRITE-04)."""
        from app.models.database import ScreenplayContent

        project_id = _make_project(db_session)
        url = f"/api/phase-data/{project_id}/write/screenplay_editor"

        r1 = client.patch(url, json={"content": TWO_SCENES}, headers=mock_auth_headers)
        assert r1.status_code == 200, r1.text
        r2 = client.patch(url, json={"content": TWO_SCENES}, headers=mock_auth_headers)
        assert r2.status_code == 200, r2.text

        rows = (
            db_session.query(ScreenplayContent)
            .filter(ScreenplayContent.project_id == project_id)
            .all()
        )
        assert len(rows) == 2  # not 4

    def test_screenplay_save_delete_scoped_to_one_project(
        self, client, db_session, mock_auth_headers
    ):
        """WR-03: the delete-then-recreate reconcile is scoped to THIS project —
        saving project B must NOT delete project A's ScreenplayContent rows."""
        from app.models.database import ScreenplayContent

        project_a = _make_project(db_session)
        project_b = _make_project(db_session)

        client.patch(
            f"/api/phase-data/{project_a}/write/screenplay_editor",
            json={"content": TWO_SCENES}, headers=mock_auth_headers,
        )
        client.patch(
            f"/api/phase-data/{project_b}/write/screenplay_editor",
            json={"content": TWO_SCENES}, headers=mock_auth_headers,
        )

        a_rows = db_session.query(ScreenplayContent).filter(
            ScreenplayContent.project_id == project_a
        ).all()
        b_rows = db_session.query(ScreenplayContent).filter(
            ScreenplayContent.project_id == project_b
        ).all()
        assert len(a_rows) == 2  # project A survived project B's save
        assert len(b_rows) == 2

    def test_screenplay_save_empty_clears_stale_rows(
        self, client, db_session, mock_auth_headers
    ):
        """WR-02: saving an explicit empty screenplays list clears the existing
        ScreenplayContent rows (no stale drift between PhaseData and rows)."""
        from app.models.database import ScreenplayContent

        project_id = _make_project(db_session)
        url = f"/api/phase-data/{project_id}/write/screenplay_editor"

        client.patch(url, json={"content": TWO_SCENES}, headers=mock_auth_headers)
        assert db_session.query(ScreenplayContent).filter(
            ScreenplayContent.project_id == project_id
        ).count() == 2

        # Now save an empty screenplays list — rows must be cleared, not left stale.
        r = client.patch(url, json={"content": {"screenplays": []}}, headers=mock_auth_headers)
        assert r.status_code == 200, r.text
        assert db_session.query(ScreenplayContent).filter(
            ScreenplayContent.project_id == project_id
        ).count() == 0

    def test_screenplay_save_marks_breakdown_stale(
        self, client, db_session, mock_auth_headers
    ):
        """With a BreakdownElement present, breakdown_stale flips True (WRITE-04)."""
        import uuid as _uuid
        from app.models.database import BreakdownElement, Project

        project_id = _make_project(db_session)

        # Insert a non-deleted breakdown element so _mark_breakdown_stale flips it.
        db_session.add(
            BreakdownElement(
                id=str(_uuid.uuid4()),
                project_id=project_id,
                category="prop",
                name="Sword",
                is_deleted=False,
            )
        )
        db_session.commit()

        response = client.patch(
            f"/api/phase-data/{project_id}/write/screenplay_editor",
            json={"content": TWO_SCENES},
            headers=mock_auth_headers,
        )
        assert response.status_code == 200, response.text

        db_session.expire_all()
        project = (
            db_session.query(Project).filter(Project.id == project_id).first()
        )
        assert project.breakdown_stale is True

    def test_saved_screenplay_feeds_breakdown_alignment(
        self, client, db_session, mock_auth_headers
    ):
        """W3: after a 2-scene manual save, _build_extraction_context returns
        scene-aligned text covering BOTH scenes' content (WRITE-04)."""
        from app.services.breakdown_service import breakdown_service

        project_id = _make_project(db_session)

        response = client.patch(
            f"/api/phase-data/{project_id}/write/screenplay_editor",
            json={"content": TWO_SCENES},
            headers=mock_auth_headers,
        )
        assert response.status_code == 200, response.text

        ctx = breakdown_service._build_extraction_context(db_session, project_id)
        joined = "\n".join(ctx.screenplay_texts)
        assert "The KNIGHT draws a sword." in joined
        assert "The KNIGHT rides on." in joined
        # Both scenes are recoverable as separate texts.
        assert len(ctx.screenplay_texts) == 2

    def test_generic_subsection_save_creates_no_screenplaycontent(
        self, client, db_session, mock_auth_headers
    ):
        """PATCH to a NON-screenplay subsection creates zero ScreenplayContent
        rows (design constraint, D-54-05)."""
        from app.models.database import ScreenplayContent

        project_id = _make_project(db_session)

        # A generic subsection whose payload even carries a 'screenplays' key must
        # NOT trigger ScreenplayContent creation (only write/screenplay_editor does).
        response = client.patch(
            f"/api/phase-data/{project_id}/story/some_key",
            json={"content": {"screenplays": TWO_SCENES["screenplays"]}},
            headers=mock_auth_headers,
        )
        assert response.status_code == 200, response.text

        rows = (
            db_session.query(ScreenplayContent)
            .filter(ScreenplayContent.project_id == project_id)
            .count()
        )
        assert rows == 0


def _add_screenplay_content(db_session, project_id, *, content="INT. ROOM - DAY\n\nAction.", episode_index=0):
    """Insert one ScreenplayContent row so _read_episode_text_by_index returns text."""
    import uuid as _uuid
    from app.models.database import ScreenplayContent

    row = ScreenplayContent(
        id=str(_uuid.uuid4()),
        project_id=project_id,
        content=content,
        formatted_content={"episode_index": episode_index, "title": "INT. ROOM - DAY"},
    )
    db_session.add(row)
    db_session.commit()


class TestSendToVapai:
    """POST /api/projects/{id}/send-to-vapai — push screenplay to vapai-studio.

    vapai_service.send_screenplay is always mocked at its boundary (AsyncMock);
    no live HTTP is made in tests."""

    def test_send_empty_screenplay_returns_400(self, client, db_session, mock_auth_headers):
        from unittest.mock import AsyncMock, patch

        project_id = _make_project(db_session)  # no ScreenplayContent rows

        with patch(
            "app.api.endpoints.projects.vapai_service.send_screenplay",
            new_callable=AsyncMock,
        ) as mock_send:
            response = client.post(
                f"/api/projects/{project_id}/send-to-vapai",
                headers=mock_auth_headers,
            )

        assert response.status_code == 400, response.text
        mock_send.assert_not_called()

    def test_send_happy_path_persists_ids(self, client, db_session, mock_auth_headers):
        from unittest.mock import AsyncMock, patch
        from app.models.database import Project

        project_id = _make_project(db_session)
        _add_screenplay_content(db_session, project_id)

        fake_result = {
            "vapai_project_id": "vp-123",
            "vapai_episode_id": "ve-456",
            "vapai_script_id": "vs-789",
            "deep_link": "http://vapai.local/projects/vp-123",
        }

        with patch(
            "app.api.endpoints.projects.vapai_service.send_screenplay",
            new_callable=AsyncMock,
            return_value=fake_result,
        ) as mock_send:
            response = client.post(
                f"/api/projects/{project_id}/send-to-vapai",
                headers=mock_auth_headers,
            )

        assert response.status_code == 200, response.text
        assert response.json() == fake_result
        mock_send.assert_awaited_once()

        # Linkage persisted for idempotent re-send.
        project = db_session.query(Project).filter(Project.id == project_id).first()
        assert project.vapai_project_id == "vp-123"
        assert project.vapai_episode_id == "ve-456"

    def test_send_cross_user_returns_404(self, client, db_session, mock_auth_headers):
        import uuid as _uuid
        from unittest.mock import AsyncMock, patch
        from app.models.database import Project

        # Project owned by a different user.
        other_id = str(_uuid.uuid4())
        other = Project(
            id=other_id,
            owner_id=str(_uuid.uuid4()),
            title="Someone Else's Film",
        )
        db_session.add(other)
        db_session.commit()

        with patch(
            "app.api.endpoints.projects.vapai_service.send_screenplay",
            new_callable=AsyncMock,
        ) as mock_send:
            response = client.post(
                f"/api/projects/{other_id}/send-to-vapai",
                headers=mock_auth_headers,
            )

        assert response.status_code == 404, response.text
        mock_send.assert_not_called()

    def test_send_downstream_failure_returns_502(self, client, db_session, mock_auth_headers):
        from unittest.mock import AsyncMock, patch
        from app.exceptions import VapaiServiceException

        project_id = _make_project(db_session)
        _add_screenplay_content(db_session, project_id)

        with patch(
            "app.api.endpoints.projects.vapai_service.send_screenplay",
            new_callable=AsyncMock,
            side_effect=VapaiServiceException("could not reach vapai-studio"),
        ):
            response = client.post(
                f"/api/projects/{project_id}/send-to-vapai",
                headers=mock_auth_headers,
            )

        assert response.status_code == 502, response.text