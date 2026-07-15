# backend/app/tests/test_vapai_scope.py

"""
Tests for the series-aware scope of POST /projects/{id}/send-to-vapai.

A series episode (project.show_id set) must NOT be silently sent as a standalone
vapai project. Instead:
  - no scope           -> 409 with is_series_episode=true (UI asks the user)
  - scope=series       -> send_episode_within_series (into the show's vapai project)
  - scope=standalone   -> send_screenplay (legacy per-episode project)
A non-series project ignores scope and always uses send_screenplay.

vapai_service is patched (no network); we assert which method the endpoint routes to.
"""

import uuid
from unittest.mock import patch, AsyncMock

from app.models.database import Project, Show, ScreenplayContent

# Must match the mock-auth user (auth_service.generate_mock_token default) so the
# owner-scoped endpoint finds these rows.
MOCK_USER_ID = "12345678-1234-5678-1234-567812345678"


def _show(db, **ov):
    d = {"id": str(uuid.uuid4()), "owner_id": MOCK_USER_ID, "title": "My Series",
         "continuity_mode": "connected", "bible_characters": "Ana - lead"}
    d.update(ov)
    s = Show(**d)
    db.add(s); db.flush()
    return s


def _project(db, show=None, **ov):
    d = {"id": str(uuid.uuid4()), "owner_id": MOCK_USER_ID, "title": "Ep One"}
    if show:
        d["show_id"] = str(show.id)
        d["episode_number"] = 1
    d.update(ov)
    p = Project(**d)
    db.add(p); db.flush()
    return p


def _screenplay(db, project_id, text="INT. ROOM - DAY\nAna enters."):
    db.add(ScreenplayContent(id=str(uuid.uuid4()), project_id=str(project_id),
                             content=text, formatted_content={"episode_index": 0}, version=1))
    db.commit()


_EP_RESULT = {"vapai_project_id": "vp1", "vapai_episode_id": "ve1",
              "vapai_script_id": "vs1", "deep_link": "http://x/projects/vp1"}


class TestSendToVapaiScope:
    def test_series_episode_no_scope_returns_409(self, client, db_session, mock_auth_headers):
        show = _show(db_session)
        p = _project(db_session, show=show)
        _screenplay(db_session, p.id)
        db_session.commit()

        r = client.post(f"/api/projects/{p.id}/send-to-vapai", headers=mock_auth_headers)
        assert r.status_code == 409, r.text
        detail = r.json()["detail"]
        assert detail["is_series_episode"] is True
        assert detail["show_id"] == str(show.id)

    def test_series_episode_scope_series_routes_into_series(self, client, db_session, mock_auth_headers):
        show = _show(db_session)
        p = _project(db_session, show=show)
        _screenplay(db_session, p.id)
        db_session.commit()

        with patch("app.api.endpoints.projects.vapai_service.send_episode_within_series",
                   new_callable=AsyncMock, return_value=_EP_RESULT) as m_series, \
             patch("app.api.endpoints.projects.vapai_service.send_screenplay",
                   new_callable=AsyncMock) as m_standalone:
            r = client.post(f"/api/projects/{p.id}/send-to-vapai?scope=series",
                            headers=mock_auth_headers)

        assert r.status_code == 200, r.text
        m_series.assert_awaited_once()
        m_standalone.assert_not_awaited()
        # bible + episode number threaded through
        kwargs = m_series.await_args.kwargs
        assert kwargs["episode_number"] == 1
        assert "Ana" in kwargs["bible_text"]

    def test_series_episode_scope_standalone_routes_standalone(self, client, db_session, mock_auth_headers):
        show = _show(db_session)
        p = _project(db_session, show=show)
        _screenplay(db_session, p.id)
        db_session.commit()

        with patch("app.api.endpoints.projects.vapai_service.send_screenplay",
                   new_callable=AsyncMock, return_value=_EP_RESULT) as m_standalone, \
             patch("app.api.endpoints.projects.vapai_service.send_episode_within_series",
                   new_callable=AsyncMock) as m_series:
            r = client.post(f"/api/projects/{p.id}/send-to-vapai?scope=standalone",
                            headers=mock_auth_headers)

        assert r.status_code == 200, r.text
        m_standalone.assert_awaited_once()
        m_series.assert_not_awaited()

    def test_non_series_project_ignores_scope_uses_standalone(self, client, db_session, mock_auth_headers):
        p = _project(db_session)  # no show
        _screenplay(db_session, p.id)
        db_session.commit()

        with patch("app.api.endpoints.projects.vapai_service.send_screenplay",
                   new_callable=AsyncMock, return_value=_EP_RESULT) as m_standalone:
            # No scope, no show_id -> should just send standalone (no 409).
            r = client.post(f"/api/projects/{p.id}/send-to-vapai", headers=mock_auth_headers)

        assert r.status_code == 200, r.text
        m_standalone.assert_awaited_once()

    def test_bad_scope_value_is_400(self, client, db_session, mock_auth_headers):
        p = _project(db_session)
        _screenplay(db_session, p.id)
        db_session.commit()

        r = client.post(f"/api/projects/{p.id}/send-to-vapai?scope=bogus", headers=mock_auth_headers)
        assert r.status_code == 400, r.text

    def test_no_screenplay_is_400(self, client, db_session, mock_auth_headers):
        show = _show(db_session)
        p = _project(db_session, show=show)  # no screenplay rows
        db_session.commit()

        r = client.post(f"/api/projects/{p.id}/send-to-vapai?scope=series", headers=mock_auth_headers)
        assert r.status_code == 400, r.text
