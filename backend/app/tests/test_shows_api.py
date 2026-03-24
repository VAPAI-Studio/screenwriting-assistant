import pytest
from app.models.database import Show as ShowModel


class TestShowModel:
    """Test the Show SQLAlchemy model directly."""

    def test_show_model_columns(self, db_session):
        show = ShowModel(
            owner_id="12345678-1234-5678-1234-567812345678",
            title="Breaking Bad",
            description="A chemistry teacher turns to cooking meth.",
        )
        db_session.add(show)
        db_session.commit()
        db_session.refresh(show)

        assert show.id is not None
        assert show.owner_id == "12345678-1234-5678-1234-567812345678"
        assert show.title == "Breaking Bad"
        assert show.description == "A chemistry teacher turns to cooking meth."
        assert show.created_at is not None


class TestShowsAPI:
    """Test Show CRUD endpoints."""

    def test_create_show(self, client, mock_auth_headers):
        resp = client.post(
            "/api/shows/",
            json={"title": "Breaking Bad", "description": "A chemistry teacher..."},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Breaking Bad"
        assert data["description"] == "A chemistry teacher..."
        assert "id" in data
        assert "owner_id" in data
        assert "created_at" in data

    def test_create_show_default_description(self, client, mock_auth_headers):
        resp = client.post(
            "/api/shows/",
            json={"title": "The Wire"},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["description"] == ""

    def test_create_show_empty_title(self, client, mock_auth_headers):
        resp = client.post(
            "/api/shows/",
            json={"title": "   "},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 422

    def test_create_show_short_title(self, client, mock_auth_headers):
        resp = client.post(
            "/api/shows/",
            json={"title": "X"},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 422

    def test_list_shows(self, client, mock_auth_headers):
        client.post("/api/shows/", json={"title": "Show A"}, headers=mock_auth_headers)
        client.post("/api/shows/", json={"title": "Show B"}, headers=mock_auth_headers)
        resp = client.get("/api/shows/", headers=mock_auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        titles = [s["title"] for s in data]
        assert "Show A" in titles
        assert "Show B" in titles

    def test_get_show(self, client, mock_auth_headers):
        create_resp = client.post(
            "/api/shows/",
            json={"title": "Get Me", "description": "Details here"},
            headers=mock_auth_headers,
        )
        show_id = create_resp.json()["id"]
        resp = client.get(f"/api/shows/{show_id}", headers=mock_auth_headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "Get Me"
        assert resp.json()["description"] == "Details here"

    def test_get_show_not_found(self, client, mock_auth_headers):
        resp = client.get(
            "/api/shows/00000000-0000-0000-0000-000000000000",
            headers=mock_auth_headers,
        )
        assert resp.status_code == 404

    def test_update_show(self, client, mock_auth_headers):
        create_resp = client.post(
            "/api/shows/",
            json={"title": "Old Title", "description": "Old desc"},
            headers=mock_auth_headers,
        )
        show_id = create_resp.json()["id"]
        update_resp = client.put(
            f"/api/shows/{show_id}",
            json={"title": "New Title", "description": "New desc"},
            headers=mock_auth_headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["title"] == "New Title"
        assert update_resp.json()["description"] == "New desc"

    def test_update_show_partial(self, client, mock_auth_headers):
        create_resp = client.post(
            "/api/shows/",
            json={"title": "Keep Title", "description": "Change me"},
            headers=mock_auth_headers,
        )
        show_id = create_resp.json()["id"]
        update_resp = client.put(
            f"/api/shows/{show_id}",
            json={"description": "Changed"},
            headers=mock_auth_headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["title"] == "Keep Title"
        assert update_resp.json()["description"] == "Changed"

    def test_update_show_not_found(self, client, mock_auth_headers):
        resp = client.put(
            "/api/shows/00000000-0000-0000-0000-000000000000",
            json={"title": "No Such Show"},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 404

    def test_delete_show(self, client, mock_auth_headers):
        create_resp = client.post(
            "/api/shows/",
            json={"title": "Doomed Show"},
            headers=mock_auth_headers,
        )
        show_id = create_resp.json()["id"]
        del_resp = client.delete(f"/api/shows/{show_id}", headers=mock_auth_headers)
        assert del_resp.status_code == 200
        # Verify it's gone
        get_resp = client.get(f"/api/shows/{show_id}", headers=mock_auth_headers)
        assert get_resp.status_code == 404

    def test_delete_show_not_found(self, client, mock_auth_headers):
        resp = client.delete(
            "/api/shows/00000000-0000-0000-0000-000000000000",
            headers=mock_auth_headers,
        )
        assert resp.status_code == 404

    def test_create_show_fields_complete(self, client, mock_auth_headers):
        resp = client.post(
            "/api/shows/",
            json={"title": "Full Fields", "description": "Test desc"},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "owner_id" in data
        assert "title" in data
        assert "description" in data
        assert "created_at" in data
        # updated_at may be None on creation
