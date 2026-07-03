"""
Phase 1.5 — Global library + admin-only writes.

Tests the require_admin dependency (ADMIN_EMAILS gate) and its wiring into a
library write endpoint. Library reads stay open to any authenticated user.
"""

import pytest
from unittest.mock import patch
from fastapi import HTTPException

from app.config import settings
from app.api.dependencies import require_admin
from app.models import schemas
from datetime import datetime
from uuid import UUID


def _user(email="user@example.com"):
    return schemas.User(
        id=UUID("12345678-1234-5678-1234-567812345678"),
        email=email,
        display_name="Dev User",
        created_at=datetime.utcnow(),
    )


class TestRequireAdmin:
    async def test_empty_admins_dev_allows(self):
        """No ADMIN_EMAILS in development -> writes stay open (mock auth flow)."""
        with patch.object(settings, "ADMIN_EMAILS", ""), \
             patch.object(settings, "ENVIRONMENT", "development"):
            user = await require_admin(current_user=_user())
        assert user.email == "user@example.com"

    async def test_empty_admins_production_refuses(self):
        """No ADMIN_EMAILS in production -> library writes are locked."""
        with patch.object(settings, "ADMIN_EMAILS", ""), \
             patch.object(settings, "ENVIRONMENT", "production"):
            with pytest.raises(HTTPException) as exc:
                await require_admin(current_user=_user())
        assert exc.value.status_code == 403

    async def test_admin_email_allowed(self):
        with patch.object(settings, "ADMIN_EMAILS", "yvesfogel@gmail.com, other@x.com"):
            user = await require_admin(current_user=_user("yvesfogel@gmail.com"))
        assert user.email == "yvesfogel@gmail.com"

    async def test_admin_email_case_insensitive(self):
        with patch.object(settings, "ADMIN_EMAILS", "YvesFogel@Gmail.com"):
            user = await require_admin(current_user=_user("yvesfogel@gmail.com"))
        assert user.email == "yvesfogel@gmail.com"

    async def test_non_admin_refused(self):
        with patch.object(settings, "ADMIN_EMAILS", "yvesfogel@gmail.com"):
            with pytest.raises(HTTPException) as exc:
                await require_admin(current_user=_user("user@example.com"))
        assert exc.value.status_code == 403


class TestAdminGateEndpoints:
    def test_agent_create_refused_for_non_admin(self, client, mock_auth_headers):
        """With ADMIN_EMAILS set and the mock user not on it, library writes 403."""
        with patch.object(settings, "ADMIN_EMAILS", "yvesfogel@gmail.com"):
            resp = client.post(
                "/api/agents/",
                json={"name": "Gate Refused Agent",
                      "system_prompt_template": "You are a strict test agent for the admin gate suite."},
                headers=mock_auth_headers,
            )
        assert resp.status_code == 403

    def test_agent_create_allowed_for_admin(self, client, mock_auth_headers):
        """Mock user (user@example.com) on ADMIN_EMAILS -> write goes through."""
        with patch.object(settings, "ADMIN_EMAILS", "user@example.com"):
            resp = client.post(
                "/api/agents/",
                json={"name": "Gate Test Agent",
                      "system_prompt_template": "You are a strict test agent for the admin gate suite."},
                headers=mock_auth_headers,
            )
        assert resp.status_code == 200

    def test_agent_list_open_to_non_admin(self, client, mock_auth_headers):
        """Reads stay open: listing agents needs no admin email."""
        with patch.object(settings, "ADMIN_EMAILS", "yvesfogel@gmail.com"):
            resp = client.get("/api/agents/", headers=mock_auth_headers)
        assert resp.status_code == 200

    def test_book_list_open_to_non_admin(self, client, mock_auth_headers):
        with patch.object(settings, "ADMIN_EMAILS", "yvesfogel@gmail.com"):
            resp = client.get("/api/books/", headers=mock_auth_headers)
        assert resp.status_code == 200
