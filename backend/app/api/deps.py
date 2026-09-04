"""FastAPI dependencies for database sessions, JWT authentication, and core singletons."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.buffer import BufferManager
from app.core.detector import Detector
from app.core.face_verifier import FaceVerifier
from app.core.logging import get_logger
from app.core.security import InvalidTokenError, decode_access_token
from app.db.session import get_db_session
from app.models.user import User, UserRole
from app.services.notification import NotificationService
from app.services.storage import StorageService

logger = get_logger("halocas.api.deps")

# OAuth2 scheme extracting Bearer tokens from the Authorization header
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=True,
)

# Core subsystem singletons
_detector_instance: Detector | None = None
_face_verifier_instance: FaceVerifier | None = None
_buffer_manager_instance: BufferManager | None = None
_storage_service_instance: StorageService | None = None
_notification_service_instance: NotificationService | None = None


async def get_db() -> AsyncIterator[AsyncSession]:
    """Dependency yielding a scoped asynchronous SQLAlchemy database session."""
    async for session in get_db_session():
        yield session


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    """Validate bearer JWT token and return active authenticated User.

    Args:
        db: Database session.
        token: Bearer JWT string from Authorization header.

    Returns:
        User: Active database user record.

    Raises:
        HTTPException: 401 if token is invalid, expired, or user not found/inactive.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        subject: str | None = payload.get("sub")
        if subject is None:
            raise credentials_exception
    except InvalidTokenError as exc:
        logger.debug("Token validation failed: %s", exc)
        raise credentials_exception from exc

    # Look up user by email or integer ID
    stmt = select(User).where(
        (User.email == subject) if "@" in subject else (User.id == int(subject))
    )
    result = await db.execute(stmt)
    user = result.scalars().first()

    if user is None:
        logger.warning("User corresponding to token subject %s not found", subject)
        raise credentials_exception

    if not user.is_active:
        logger.warning("Authentication attempted for inactive user %s", user.email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Validate that the authenticated user possesses administrative privileges.

    Args:
        current_user: Authenticated user model.

    Returns:
        User: Admin user model.

    Raises:
        HTTPException: 403 Forbidden if user lacks admin credentials.
    """
    if current_user.role != UserRole.ADMIN and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required to access this resource",
        )
    return current_user


def get_detector() -> Detector:
    """Provide singleton Detector computer vision model instance."""
    global _detector_instance
    if _detector_instance is None:
        settings = get_settings()
        _detector_instance = Detector(model_path=settings.YOLO_MODEL_PATH)
    return _detector_instance


def get_face_verifier() -> FaceVerifier:
    """Provide singleton FaceVerifier biometric engine instance."""
    global _face_verifier_instance
    if _face_verifier_instance is None:
        settings = get_settings()
        _face_verifier_instance = FaceVerifier(model_name=settings.DEEPFACE_MODEL)
    return _face_verifier_instance


def get_buffer_manager() -> BufferManager:
    """Provide singleton multi-camera BufferManager instance."""
    global _buffer_manager_instance
    if _buffer_manager_instance is None:
        _buffer_manager_instance = BufferManager()
    return _buffer_manager_instance


def get_storage_service() -> StorageService:
    """Provide singleton Cloudflare R2 StorageService instance."""
    global _storage_service_instance
    if _storage_service_instance is None:
        _storage_service_instance = StorageService()
    return _storage_service_instance


def get_notification_service() -> NotificationService:
    """Provide singleton NotificationService email dispatch instance."""
    global _notification_service_instance
    if _notification_service_instance is None:
        _notification_service_instance = NotificationService()
    return _notification_service_instance
