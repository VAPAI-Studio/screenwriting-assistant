# backend/app/api/dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime
from uuid import UUID

from ..config import settings
from ..models import schemas, database
from ..services.auth_service import auth_service, mock_auth_service
from ..db import get_db

# Auth dependency
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> schemas.User:
    """Get current authenticated user"""
    try:
        # Mock authentication - only available in development
        if settings.ENVIRONMENT == "development" and credentials.credentials == "mock-token":
            return mock_auth_service.get_current_user()
        
        # Production authentication flow
        user_id = auth_service.verify_token(credentials.credentials)
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # In production, you would query the user from database here
        # For MVP, return mock user
        return schemas.User(
            id=UUID(user_id),
            email="user@example.com",
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
