# backend/app/tests/test_breakdown_api.py

import uuid

import pytest
from unittest.mock import patch, AsyncMock
from app.models.database import (
    BreakdownElement,
    BreakdownRun,
    ElementSceneLink,
    ListItem,
    PhaseData,
    Project,
    ScreenplayContent,
)
from app.services.breakdown_service import (
    ExtractionResponse,
    ExtractedElement,
    ExtractedSceneAppearance,
)

MOCK_USER_ID = "12345678-1234-5678-1234-567812345678"


def _create_project_via_api(client, mock_auth_headers, title="Test Project"):
    """Create a project through the API so owner_id is stored correctly for SQLite."""
    resp = client.post(
        "/api/projects/",
        json={"title": title, "framework": "three_act"},
        headers=mock_auth_headers,
    )
    assert resp.status_code == 200, f"Project creation failed: {resp.json()}"
    return resp.json()["id"]


def _make_element(db_session, project_id, category="prop", name="Test Item", is_deleted=False):
    elem = BreakdownElement(
        id=str(uuid.uuid4()),
        project_id=project_id,
        category=category,
        name=name,
        source="ai",
        is_deleted=is_deleted,
    )
    db_session.add(elem)
    db_session.flush()
    return elem


def _make_phase_data(db_session, project_id, phase="write", subsection_key="scenes"):
    """Create a PhaseData record to parent ListItems."""
    pd = PhaseData(
        id=str(uuid.uuid4()),
        project_id=project_id,
        phase=phase,
        subsection_key=subsection_key,
        content={},
    )
    db_session.add(pd)
    db_session.flush()
    return pd


def _make_list_item(db_session, phase_data_id):
    """Create a ListItem to use as a scene for linking."""
    item = ListItem(
        id=str(uuid.uuid4()),
        phase_data_id=phase_data_id,
        item_type="scene",
        content={"title": "Scene 1"},
    )
    db_session.add(item)
    db_session.flush()
    return item


# ============================================================
# API-02: List elements
# ============================================================

class TestListElements:
    def test_list_elements(self, client, db_session, mock_auth_headers):
        """GET /elements/{project_id} returns created elements (200)."""
        project_id = _create_project_via_api(client, mock_auth_headers)
        _make_element(db_session, project_id, name="Chair")
        _make_element(db_session, project_id, name="Table")
        db_session.commit()

        resp = client.get(f"/api/breakdown/elements/{project_id}", headers=mock_auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        names = {e["name"] for e in data}
        assert names == {"Chair", "Table"}

    def test_list_elements_excludes_deleted(self, client, db_session, mock_auth_headers):
        """Soft-deleted elements excluded by default."""
        project_id = _create_project_via_api(client, mock_auth_headers)
        _make_element(db_session, project_id, name="Active")
        _make_element(db_session, project_id, name="Deleted", is_deleted=True)
        db_session.commit()

        resp = client.get(f"/api/breakdown/elements/{project_id}", headers=mock_auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Active"

    def test_list_elements_include_deleted(self, client, db_session, mock_auth_headers):
        """include_deleted=true returns all elements."""
        project_id = _create_project_via_api(client, mock_auth_headers)
        _make_element(db_session, project_id, name="Active")
        _make_element(db_session, project_id, name="Deleted", is_deleted=True)
        db_session.commit()

        resp = client.get(
            f"/api/breakdown/elements/{project_id}",
            params={"include_deleted": "true"},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_list_elements_filter_by_category(self, client, db_session, mock_auth_headers):
        """?category=prop returns only props."""
        project_id = _create_project_via_api(client, mock_auth_headers)
        _make_element(db_session, project_id, category="prop", name="Sword")
        _make_element(db_session, project_id, category="character", name="Hero")
        db_session.commit()

        resp = client.get(
            f"/api/breakdown/elements/{project_id}",
            params={"category": "prop"},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Sword"


# ============================================================
# API-04: Create element
# ============================================================

class TestCreateElement:
    def test_create_element_source_user(self, client, db_session, mock_auth_headers):
        """POST creates with source='user' (201)."""
        project_id = _create_project_via_api(client, mock_auth_headers)

        resp = client.post(
            f"/api/breakdown/elements/{project_id}",
            json={"category": "prop", "name": "Magic Wand", "description": "A wand"},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Magic Wand"
        assert data["source"] == "user"

    def test_create_element_duplicate_conflict(self, client, db_session, mock_auth_headers):
        """Duplicate active name returns 409."""
        project_id = _create_project_via_api(client, mock_auth_headers)
        _make_element(db_session, project_id, category="prop", name="Duplicate")
        db_session.commit()

        resp = client.post(
            f"/api/breakdown/elements/{project_id}",
            json={"category": "prop", "name": "Duplicate"},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 409

    def test_create_element_restores_soft_deleted(self, client, db_session, mock_auth_headers):
        """Duplicate of soft-deleted name restores it."""
        project_id = _create_project_via_api(client, mock_auth_headers)
        _make_element(db_session, project_id, category="prop", name="Restored", is_deleted=True)
        db_session.commit()

        resp = client.post(
            f"/api/breakdown/elements/{project_id}",
            json={"category": "prop", "name": "Restored", "description": "Back from the dead"},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["is_deleted"] is False
        assert data["description"] == "Back from the dead"
        assert data["source"] == "user"


# ============================================================
# API-03: Update element
# ============================================================

class TestUpdateElement:
    def test_update_element_sets_user_modified(self, client, db_session, mock_auth_headers):
        """PUT updates fields and sets user_modified=true."""
        project_id = _create_project_via_api(client, mock_auth_headers)
        elem = _make_element(db_session, project_id, name="Original")
        db_session.commit()

        resp = client.put(
            f"/api/breakdown/element/{elem.id}",
            json={"name": "Updated", "description": "new desc"},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated"
        assert data["description"] == "new desc"
        assert data["user_modified"] is True

    def test_update_element_partial(self, client, db_session, mock_auth_headers):
        """PUT with only name updates name, leaves others."""
        project_id = _create_project_via_api(client, mock_auth_headers)
        elem = _make_element(db_session, project_id, name="Partial")
        elem.description = "keep me"
        db_session.commit()

        resp = client.put(
            f"/api/breakdown/element/{elem.id}",
            json={"name": "Renamed"},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Renamed"
        assert data["description"] == "keep me"


# ============================================================
# API-05: Delete element (soft-delete)
# ============================================================

class TestDeleteElement:
    def test_delete_element_soft_deletes(self, client, db_session, mock_auth_headers):
        """DELETE sets is_deleted=true (200)."""
        project_id = _create_project_via_api(client, mock_auth_headers)
        elem = _make_element(db_session, project_id, name="ToDelete")
        db_session.commit()

        resp = client.delete(
            f"/api/breakdown/element/{elem.id}",
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"

        # Verify soft-deleted in DB
        db_session.refresh(elem)
        assert elem.is_deleted is True


# ============================================================
# API-01: Extraction trigger (stub)
# ============================================================

class TestExtraction:
    @patch("app.services.breakdown_service.chat_completion_structured", new_callable=AsyncMock)
    def test_extract_creates_completed_run(self, mock_ai, client, db_session, mock_auth_headers):
        """POST /extract creates BreakdownRun with status='completed' (mocked AI)."""
        project_id = _create_project_via_api(client, mock_auth_headers)

        # Create screenplay content so extraction doesn't fail early
        sc = ScreenplayContent(
            id=str(uuid.uuid4()),
            project_id=project_id,
            content="INT. ROOM - DAY\nA bare room.",
        )
        db_session.add(sc)
        db_session.commit()

        # Mock AI returns empty elements
        mock_ai.return_value = ExtractionResponse(elements=[])

        resp = client.post(
            f"/api/breakdown/extract/{project_id}",
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["project_id"] == str(project_id)

    @patch("app.services.breakdown_service.chat_completion_structured", new_callable=AsyncMock)
    def test_extract_response_shape(self, mock_ai, client, db_session, mock_auth_headers):
        """Response has all BreakdownRunResponse fields and reflects extracted elements."""
        project_id = _create_project_via_api(client, mock_auth_headers)

        # Create screenplay content
        sc = ScreenplayContent(
            id=str(uuid.uuid4()),
            project_id=project_id,
            content="INT. OFFICE - DAY\nJOHN enters carrying a briefcase.",
        )
        db_session.add(sc)
        db_session.commit()

        # Mock AI returns sample elements
        mock_ai.return_value = ExtractionResponse(elements=[
            ExtractedElement(
                category="character",
                canonical_name="John",
                description="A man with a briefcase",
                scene_appearances=[],
            ),
            ExtractedElement(
                category="prop",
                canonical_name="Briefcase",
                description="A leather briefcase",
                scene_appearances=[],
            ),
        ])

        resp = client.post(
            f"/api/breakdown/extract/{project_id}",
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        expected_keys = {
            "id", "project_id", "status", "config", "result_summary",
            "elements_created", "elements_updated", "error_message",
            "created_at", "completed_at",
        }
        assert expected_keys.issubset(set(data.keys()))
        assert data["elements_created"] == 2
        assert data["elements_updated"] == 0


# ============================================================
# API-06: Scene links
# ============================================================

class TestSceneLinks:
    def test_add_scene_link(self, client, db_session, mock_auth_headers):
        """POST /element/{id}/scenes creates link (201)."""
        project_id = _create_project_via_api(client, mock_auth_headers)
        elem = _make_element(db_session, project_id, name="LinkMe")
        pd = _make_phase_data(db_session, project_id)
        item = _make_list_item(db_session, pd.id)
        db_session.commit()

        resp = client.post(
            f"/api/breakdown/element/{elem.id}/scenes",
            json={"scene_item_id": str(item.id), "context": "Used in scene 1"},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["message"] == "Scene linked"
        assert "id" in data

    def test_add_scene_link_idempotent(self, client, db_session, mock_auth_headers):
        """Duplicate link returns 200, not error."""
        project_id = _create_project_via_api(client, mock_auth_headers)
        elem = _make_element(db_session, project_id, name="IdempotentLink")
        pd = _make_phase_data(db_session, project_id)
        item = _make_list_item(db_session, pd.id)
        db_session.commit()

        # First link
        resp1 = client.post(
            f"/api/breakdown/element/{elem.id}/scenes",
            json={"scene_item_id": str(item.id)},
            headers=mock_auth_headers,
        )
        assert resp1.status_code == 201

        # Duplicate link (idempotent)
        resp2 = client.post(
            f"/api/breakdown/element/{elem.id}/scenes",
            json={"scene_item_id": str(item.id)},
            headers=mock_auth_headers,
        )
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["message"] == "Scene link already exists"

    def test_add_scene_link_invalid_scene(self, client, db_session, mock_auth_headers):
        """Nonexistent scene_item_id returns 404."""
        project_id = _create_project_via_api(client, mock_auth_headers)
        elem = _make_element(db_session, project_id, name="BadLink")
        db_session.commit()

        fake_scene_id = str(uuid.uuid4())
        resp = client.post(
            f"/api/breakdown/element/{elem.id}/scenes",
            json={"scene_item_id": fake_scene_id},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 404

    def test_remove_scene_link(self, client, db_session, mock_auth_headers):
        """DELETE /element/{id}/scenes/{scene_id} removes link."""
        project_id = _create_project_via_api(client, mock_auth_headers)
        elem = _make_element(db_session, project_id, name="Removable")
        pd = _make_phase_data(db_session, project_id)
        item = _make_list_item(db_session, pd.id)
        # Create link directly in DB
        link = ElementSceneLink(
            id=str(uuid.uuid4()),
            element_id=elem.id,
            scene_item_id=item.id,
            context="test",
            source="user",
        )
        db_session.add(link)
        db_session.commit()

        resp = client.delete(
            f"/api/breakdown/element/{elem.id}/scenes/{item.id}",
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"

    def test_remove_scene_link_nonexistent(self, client, db_session, mock_auth_headers):
        """Removing nonexistent link returns 404."""
        project_id = _create_project_via_api(client, mock_auth_headers)
        elem = _make_element(db_session, project_id, name="NoLink")
        db_session.commit()

        fake_scene_id = str(uuid.uuid4())
        resp = client.delete(
            f"/api/breakdown/element/{elem.id}/scenes/{fake_scene_id}",
            headers=mock_auth_headers,
        )
        assert resp.status_code == 404


# ============================================================
# API-07: Summary
# ============================================================

class TestSummary:
    def test_summary_returns_counts(self, client, db_session, mock_auth_headers):
        """GET /summary returns category counts and total."""
        project_id = _create_project_via_api(client, mock_auth_headers)
        _make_element(db_session, project_id, category="prop", name="Prop1")
        _make_element(db_session, project_id, category="prop", name="Prop2")
        _make_element(db_session, project_id, category="character", name="Char1")
        db_session.commit()

        resp = client.get(
            f"/api/breakdown/summary/{project_id}",
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_elements"] == 3
        assert data["counts_by_category"]["prop"] == 2
        assert data["counts_by_category"]["character"] == 1

    def test_summary_staleness(self, client, db_session, mock_auth_headers):
        """Summary reflects project.breakdown_stale value."""
        project_id = _create_project_via_api(client, mock_auth_headers)
        # Set breakdown_stale directly on the DB object
        project = db_session.query(Project).filter(Project.id == project_id).first()
        project.breakdown_stale = True
        db_session.commit()

        resp = client.get(
            f"/api/breakdown/summary/{project_id}",
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_stale"] is True

    def test_summary_with_last_run(self, client, db_session, mock_auth_headers):
        """Summary includes last run info after extraction."""
        project_id = _create_project_via_api(client, mock_auth_headers)
        run = BreakdownRun(
            id=str(uuid.uuid4()),
            project_id=project_id,
            status="completed",
            config={},
            result_summary={"total": 5},
        )
        db_session.add(run)
        db_session.commit()

        resp = client.get(
            f"/api/breakdown/summary/{project_id}",
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["last_run"] is not None
        assert data["last_run"]["status"] == "completed"


# ============================================================
# Cross-cutting tests
# ============================================================

class TestCrossCutting:
    def test_nonexistent_project_404(self, client, mock_auth_headers):
        """Operations on nonexistent project return 404."""
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/api/breakdown/elements/{fake_id}", headers=mock_auth_headers)
        assert resp.status_code == 404

    def test_no_auth_returns_error(self, client):
        """Requests without auth header return 401/403."""
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/api/breakdown/elements/{fake_id}")
        assert resp.status_code in (401, 403)
