# backend/app/api/endpoints/auth.py

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from ...services.auth_service import auth_service, mock_auth_service

router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class MagicLinkRequest(BaseModel):
    email: EmailStr

class MagicLinkResponse(BaseModel):
    message: str
    magic_link: str  # In production, this would be sent via email

@router.post("/token/mock", response_model=Token)
async def create_mock_token():
    """Create a mock token for development"""
    token = mock_auth_service.create_mock_token()
    return Token(access_token=token)

@router.post("/magic-link", response_model=MagicLinkResponse)
async def request_magic_link(request: MagicLinkRequest):
    """Request a magic link for email authentication"""
    # In production, this would:
    # 1. Check if user exists or create new user
    # 2. Generate magic link token
    # 3. Send email with the link
    # 4. Return success message (without the link)
    
    # For MVP, we'll just return the magic link directly
    token = auth_service.create_magic_link_token(request.email)
    magic_link = f"http://localhost:5173/auth/verify?token={token}"
    
    return MagicLinkResponse(
        message="Magic link created (in production, this would be sent via email)",
        magic_link=magic_link
    )

@router.post("/verify-magic-link", response_model=Token)
async def verify_magic_link(token: str):
    """Verify magic link and return access token"""
    email = auth_service.verify_magic_link_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired magic link"
        )
    
    # In production, find or create user by email
    # For MVP, create a mock user token
    user_id = "12345678-1234-5678-1234-567812345678"  # Mock user ID
    access_token = auth_service.create_access_token({"sub": user_id, "email": email})
    
    return Token(access_token=access_token)
