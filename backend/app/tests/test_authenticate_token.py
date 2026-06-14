"""Tests for the shared authenticate_token core (Phase 55, MCPF-02/03).

authenticate_token is the Depends-free auth core extracted from get_current_user
so that the mounted MCP sub-app (which never runs FastAPI's dependency chain)
can authenticate sa_/JWT/mock tokens through the SAME logic — including the
atomic request_count / last_used_at increment for sa_ keys.

These tests prove the core works without FastAPI request context and that the
sa_ increment lives in the core (so MCP calls are counted), and that REST
behavior is preserved (HTTPException 401 on every failure path).
"""

import hashlib
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from fastapi import HTTPException

from app.api.dependencies import authenticate_token
from app.models.database import ApiKey as ApiKeyModel, User as UserModel

MOCK_USER_ID = "12345678-1234-5678-1234-567812345678"


def _ensure_mock_user(db_session):
    existing = db_session.query(UserModel).filter(UserModel.id == MOCK_USER_ID).first()
    if not existing:
        db_session.add(UserModel(
            id=MOCK_USER_ID,
            email="authtest@example.com",
            hashed_password="fakehash",
            display_name="AuthTest",
        ))
        db_session.flush()


def _make_user(db_session, email):
    uid = str(uuid.uuid4())
    db_session.add(UserModel(
        id=uid,
        email=email,
        hashed_password="fakehash",
        display_name="KeyOwner",
    ))
    db_session.flush()
    return uid


def _make_sa_key(db_session, user_id, token, *, expires_at=None, is_active=True):
    key_hash = hashlib.sha256(token.encode()).hexdigest()
    key = ApiKeyModel(
        user_id=user_id,
        name="MCP Test Key",
        key_prefix=token[:8],
        key_hash=key_hash,
        expires_at=expires_at,
        is_active=is_active,
    )
    db_session.add(key)
    db_session.commit()
    db_session.refresh(key)
    return key


class TestAuthenticateTokenCore:
    """authenticate_token is callable WITHOUT FastAPI Depends and behaves correctly."""

    def test_mock_token_returns_mock_user(self, db_session):
        # ENVIRONMENT is 'development' in the test config; mock-token resolves.
        user = authenticate_token("mock-token", db_session)
        assert str(user.id) == MOCK_USER_ID

    def test_valid_sa_key_returns_owner_and_increments(self, db_session):
        owner_id = _make_user(db_session, "owner1@example.com")
        token = "sa_owner1_secretvalue"
        key = _make_sa_key(db_session, owner_id, token)
        assert key.request_count == 0

        user = authenticate_token(token, db_session)
        assert str(user.id) == owner_id

        db_session.refresh(key)
        assert key.request_count == 1
        assert key.last_used_at is not None

    def test_increment_lives_in_core_not_wrapper(self, db_session):
        """Two calls => request_count == 2 (proves the increment is in the shared core)."""
        owner_id = _make_user(db_session, "owner2@example.com")
        token = "sa_owner2_secretvalue"
        key = _make_sa_key(db_session, owner_id, token)

        authenticate_token(token, db_session)
        authenticate_token(token, db_session)

        db_session.refresh(key)
        assert key.request_count == 2

    def test_invalid_sa_key_raises_401(self, db_session):
        with pytest.raises(HTTPException) as exc:
            authenticate_token("sa_nope_doesnotexist", db_session)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Invalid API key"

    def test_expired_sa_key_raises_401(self, db_session):
        owner_id = _make_user(db_session, "owner3@example.com")
        token = "sa_owner3_secretvalue"
        _make_sa_key(
            db_session, owner_id, token,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        with pytest.raises(HTTPException) as exc:
            authenticate_token(token, db_session)
        assert exc.value.status_code == 401
        assert exc.value.detail == "API key expired"

    def test_inactive_sa_key_raises_401(self, db_session):
        owner_id = _make_user(db_session, "owner4@example.com")
        token = "sa_owner4_secretvalue"
        _make_sa_key(db_session, owner_id, token, is_active=False)
        with pytest.raises(HTTPException) as exc:
            authenticate_token(token, db_session)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Invalid API key"

    def test_garbage_token_raises_401(self, db_session):
        with pytest.raises(HTTPException) as exc:
            authenticate_token("not-a-real-token", db_session)
        assert exc.value.status_code == 401


class TestGetCurrentUserDelegates:
    """get_current_user is a thin wrapper that still authenticates REST correctly."""

    def test_mock_token_via_endpoint(self, client):
        # /api/projects requires auth; mock-token must still work end-to-end.
        resp = client.get("/api/projects", headers={"Authorization": "Bearer mock-token"})
        assert resp.status_code == 200

    def test_invalid_token_via_endpoint_401(self, client):
        resp = client.get("/api/projects", headers={"Authorization": "Bearer sa_bad_nope"})
        assert resp.status_code == 401
