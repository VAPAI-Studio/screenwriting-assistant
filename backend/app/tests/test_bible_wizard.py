"""
Series Bible Wizard (POST /api/shows/{id}/bible/wizard).

Synchronous preview endpoint (like /slots/{id}/reconcile): proposes AI drafts
for every bible field from a seed + the show's current partial bible, writes
NOTHING. AI is ALWAYS mocked (AsyncMock) — deterministic and offline.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.main import app
from app.middleware import RateLimitMiddleware


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """RateLimitMiddleware keeps an in-memory per-IP request log shared across the
    whole test session; in the full suite the shared 'testclient' IP accumulates
    enough requests to trip the limit, 429'ing our POSTs (and pushing later files
    like storyboard over the edge). Clear the live middleware instance's log before
    each test — same pattern as test_vapai_scope."""
    node = getattr(app, "middleware_stack", None)
    while node is not None:
        if isinstance(node, RateLimitMiddleware):
            node.requests = {}
            break
        node = getattr(node, "app", None)
    yield


def _create_show(client, headers, title="Bible Wizard Show"):
    resp = client.post(
        "/api/shows/",
        json={"title": title, "continuity_mode": "connected"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


_FAKE_BIBLE = {
    "bible_central_premise": "A washed-up magician moonlights as a con artist.",
    "bible_story_engine": "Each week a new mark walks in with a problem only a trick can solve.",
    "bible_series_questions": "Will he go straight? Does the sister know?",
    "bible_regular_cast": [
        {"name": "Milo", "role": "the magician", "arc": "from cynic to believer"},
        {"name": "", "role": "", "arc": ""},  # blank entry must be dropped
        "not a dict",  # junk must be dropped
    ],
    "bible_characters": "Milo and his estranged sister Dana.",
    "bible_world_setting": "A faded seaside casino town.",
    "bible_season_arc": "The long con that could free him or bury him.",
    "bible_tone_style": "Neon-noir, wry, melancholic.",
}


class TestBibleWizard:
    def test_wizard_proposes_all_fields_and_writes_nothing(self, client, mock_auth_headers):
        show_id = _create_show(client, mock_auth_headers)
        mock = AsyncMock(return_value=json.dumps(_FAKE_BIBLE))
        with patch("app.services.template_ai_service.chat_completion", mock):
            resp = client.post(
                f"/api/shows/{show_id}/bible/wizard",
                json={"logline": "A magician con artist.", "genre": "Crime", "tone": "Noir"},
                headers=mock_auth_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["bible_central_premise"].startswith("A washed-up magician")
        assert data["bible_story_engine"]
        # Cast sanitized: blank entry + junk dropped, only Milo survives.
        assert len(data["bible_regular_cast"]) == 1
        assert data["bible_regular_cast"][0]["name"] == "Milo"
        # Preview only — the show's bible is still empty.
        bible = client.get(f"/api/shows/{show_id}/bible", headers=mock_auth_headers).json()
        assert bible["bible_central_premise"] == ""
        assert bible["bible_regular_cast"] == []

    def test_wizard_grounds_on_current_bible(self, client, mock_auth_headers):
        """The current partial bible is fed into the prompt as grounding."""
        show_id = _create_show(client, mock_auth_headers)
        client.put(
            f"/api/shows/{show_id}/bible",
            json={"bible_central_premise": "EXISTING PREMISE MARKER"},
            headers=mock_auth_headers,
        )
        mock = AsyncMock(return_value=json.dumps(_FAKE_BIBLE))
        with patch("app.services.template_ai_service.chat_completion", mock):
            resp = client.post(
                f"/api/shows/{show_id}/bible/wizard",
                json={"logline": "seed"},
                headers=mock_auth_headers,
            )
        assert resp.status_code == 200
        # The user prompt (2nd message) must carry the current bible as grounding.
        _, kwargs = mock.call_args
        user_msg = kwargs["messages"][1]["content"]
        assert "EXISTING PREMISE MARKER" in user_msg

    def test_wizard_requires_ownership(self, client, mock_auth_headers):
        resp = client.post(
            "/api/shows/00000000-0000-0000-0000-000000000000/bible/wizard",
            json={"logline": "x"},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 404
