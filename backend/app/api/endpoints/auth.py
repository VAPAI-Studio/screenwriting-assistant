# backend/app/api/endpoints/auth.py

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session

from ...models import schemas, database
from ...services.auth_service import auth_service, mock_auth_service
from ...db import get_db
from ..dependencies import get_current_user

router = APIRouter()


@router.post("/register", response_model=schemas.Token)
async def register(data: schemas.RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user with email + password, return JWT."""
    existing = db.query(database.User).filter(database.User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = auth_service.get_password_hash(data.password)
    user = database.User(
        email=data.email,
        hashed_password=hashed,
        display_name=data.display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = auth_service.create_access_token({"sub": str(user.id)})
    return schemas.Token(access_token=token)


@router.post("/login", response_model=schemas.Token)
async def login(data: schemas.LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email + password, return JWT."""
    user = db.query(database.User).filter(database.User.email == data.email).first()
    if not user or not auth_service.verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = auth_service.create_access_token({"sub": str(user.id)})
    return schemas.Token(access_token=token)


@router.get("/me", response_model=schemas.User)
async def get_profile(current_user: schemas.User = Depends(get_current_user)):
    """Get current user profile."""
    return current_user


@router.patch("/me", response_model=schemas.User)
async def update_profile(
    data: schemas.UserUpdate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user profile (display_name)."""
    user = db.query(database.User).filter(database.User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.display_name is not None:
        user.display_name = data.display_name
    db.commit()
    db.refresh(user)

    return schemas.User(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        created_at=user.created_at,
    )


@router.post("/token/mock", response_model=schemas.Token)
async def create_mock_token():
    """Create a mock token for development."""
    token = mock_auth_service.create_mock_token()
    return schemas.Token(access_token=token)


# Legacy endpoints (kept for backward compat)

class MagicLinkRequest(schemas.MagicLinkRequest):
    pass

class MagicLinkResponse(schemas.MagicLinkResponse):
    pass

@router.post("/magic-link", response_model=MagicLinkResponse)
async def request_magic_link(request: MagicLinkRequest):
    """Request a magic link for email authentication (legacy)."""
    token = auth_service.create_magic_link_token(request.email)
    magic_link = f"http://localhost:5173/auth/verify?token={token}"

    return MagicLinkResponse(
        message="Magic link created (in production, this would be sent via email)",
        magic_link=magic_link
    )


@router.post("/verify-magic-link", response_model=schemas.Token)
async def verify_magic_link(token: str):
    """Verify magic link and return access token (legacy)."""
    email = auth_service.verify_magic_link_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired magic link"
        )

    user_id = "12345678-1234-5678-1234-567812345678"
    access_token = auth_service.create_access_token({"sub": user_id, "email": email})

    return schemas.Token(access_token=access_token)
