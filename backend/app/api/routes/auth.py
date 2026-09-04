"""Authentication and user management API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user, get_db
from app.config import get_settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, Token, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate user and issue JWT token",
    responses={
        401: {"description": "Invalid email or password"},
        403: {"description": "User account inactive"},
    },
)
async def login(
    payload: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """Authenticate with email and password to receive a bearer JWT token.

    Args:
        payload: Login credentials.
        db: Database session.

    Returns:
        Token: JWT access token and expiration.
    """
    stmt = select(User).where(User.email == payload.email.lower().strip())
    result = await db.execute(stmt)
    user = result.scalars().first()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact site administrator.",
        )

    # Record last login timestamp
    user.last_login_at = datetime.now(UTC)
    await db.commit()

    settings = get_settings()
    expires_in_seconds = settings.JWT_EXPIRY_MINUTES * 60
    access_token = create_access_token(
        subject=user.email,
        role=user.role.value,
        expires_delta=timedelta(seconds=expires_in_seconds),
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in_seconds,
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user (Admin only)",
    responses={
        400: {"description": "Email already registered"},
        403: {"description": "Insufficient permissions"},
    },
)
async def register(
    payload: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_admin_user)],
) -> UserResponse:
    """Register a new user account with role assignment.

    Requires administrative privileges.

    Args:
        payload: User creation data.
        db: Database session.

    Returns:
        UserResponse: Created user profile.
    """
    clean_email = payload.email.lower().strip()
    stmt = select(User).where(User.email == clean_email)
    result = await db.execute(stmt)
    existing = result.scalars().first()

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{clean_email}' already exists.",
        )

    new_user = User(
        email=clean_email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name.strip(),
        role=payload.role,
        is_active=True,
        is_superuser=False,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return UserResponse.model_validate(new_user)
