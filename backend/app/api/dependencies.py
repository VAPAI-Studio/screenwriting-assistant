# backend/app/api/dependencies.py

import hashlib
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime
from uuid import UUID

from ..config import settings
from ..models import schemas, database
from ..services.auth_service import auth_service, mock_auth_service
from ..db import get_db

# Auth dependency
security = HTTPBearer()

def authenticate_token(token: str, db: Session) -> schemas.User:
    """Resolve a bearer token to a User — shared by REST (get_current_user) and MCP.

    Framework-neutral: takes a raw token string + DB session, does NOT use
    FastAPI Depends/HTTPBearer, so it is callable from a mounted MCP sub-app
    that never runs FastAPI's dependency chain. Behavior is byte-identical to
    the prior inline get_current_user logic, including the atomic request_count
    / last_used_at increment for sa_ keys (so MCP calls are counted too).

    Raises HTTPException(401) on any failure — preserved verbatim so REST
    responses are unchanged. MCP's TokenVerifier catches this and rejects.
    """
    try:
        # Mock authentication - only available in development
        if settings.ENVIRONMENT == "development" and token == "mock-token":
            return mock_auth_service.get_current_user()

        # API key authentication (sa_<prefix>_<secret> format)
        if token.startswith("sa_"):
            key_hash = hashlib.sha256(token.encode()).hexdigest()
            api_key = db.query(database.ApiKey).filter(
                database.ApiKey.key_hash == key_hash,
                database.ApiKey.is_active == True,
            ).first()
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            if api_key.expires_at and api_key.expires_at.replace(tzinfo=None) < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            # Atomic increment request_count + update last_used_at
            db.execute(
                text(
                    "UPDATE api_keys SET request_count = request_count + 1, "
                    "last_used_at = :now WHERE id = :id"
                ),
                {"now": datetime.utcnow(), "id": str(api_key.id)}
            )
            db.commit()
            # Return user associated with this key
            user = db.query(database.User).filter(database.User.id == api_key.user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return schemas.User(
                id=user.id,
                email=user.email,
                display_name=user.display_name,
                created_at=user.created_at,
            )

        # Production JWT authentication flow
        user_id = auth_service.verify_token(token)
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Query real user from database
        user = db.query(database.User).filter(database.User.id == user_id).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return schemas.User(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            created_at=user.created_at,
        )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def validate_token(token: str, db: Session):
    """Non-incrementing validity check for a bearer token — used by the MCP
    TokenVerifier gate so the request_count increment fires exactly once
    (in authenticate_token via require_user), not twice.

    Returns a short client identifier string (key_prefix for sa_ keys, "mock"
    for the dev mock token, "jwt" for a valid JWT) when the token is valid, or
    None when it is invalid/expired/unresolvable. Never mutates the DB.
    """
    try:
        if settings.ENVIRONMENT == "development" and token == "mock-token":
            return "mock"

        if token.startswith("sa_"):
            key_hash = hashlib.sha256(token.encode()).hexdigest()
            api_key = db.query(database.ApiKey).filter(
                database.ApiKey.key_hash == key_hash,
                database.ApiKey.is_active == True,
            ).first()
            if not api_key:
                return None
            if api_key.expires_at and api_key.expires_at.replace(tzinfo=None) < datetime.utcnow():
                return None
            user = db.query(database.User).filter(database.User.id == api_key.user_id).first()
            if not user:
                return None
            return api_key.key_prefix or "sa"

        user_id = auth_service.verify_token(token)
        if user_id is None:
            return None
        user = db.query(database.User).filter(database.User.id == user_id).first()
        if user is None:
            return None
        return "jwt"
    except Exception:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> schemas.User:
    """Get current authenticated user (JWT or API key) — thin REST wrapper over authenticate_token."""
    return authenticate_token(credentials.credentials, db)
