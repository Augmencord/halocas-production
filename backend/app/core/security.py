"""Cryptographic security, password hashing, and JWT token management."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger("halocas.core.security")


class SecurityError(Exception):
    """Base exception for cryptographic and authorization validation failures."""


class InvalidTokenError(SecurityError):
    """Raised when an authentication token is expired, malformed, or invalid."""


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a raw plaintext password against a stored bcrypt hash.

    Args:
        plain_password: Cleartext password string.
        hashed_password: Stored bcrypt hash string.

    Returns:
        bool: True if password matches hash, False otherwise.
    """
    try:
        return bool(
            bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Password verification failed unexpectedly: %s", exc)
        return False


def get_password_hash(password: str) -> str:
    """Hash a plaintext password with bcrypt.

    Args:
        password: Raw cleartext password.

    Returns:
        str: Bcrypt cryptographic hash string.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(
    subject: str | int,
    role: str = "operator",
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Generate a signed JSON Web Token (JWT) access token.

    Args:
        subject: Subject identifier (typically user_id or email).
        role: User RBAC access level.
        expires_delta: Optional custom token lifespan.
        extra_claims: Optional dictionary of auxiliary payload claims.

    Returns:
        str: Encoded, cryptographically signed JWT string.
    """
    settings = get_settings()
    now = datetime.now(UTC)

    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)

    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    if extra_claims:
        to_encode.update(extra_claims)

    encoded_jwt: str = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode, verify signature, and validate expiration of a JWT access token.

    Args:
        token: Cryptographic JWT token string.

    Returns:
        dict[str, Any]: Validated payload claims dictionary.

    Raises:
        InvalidTokenError: If token signature fails verification or has expired.
    """
    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as exc:
        logger.debug("JWT decoding/validation failed: %s", exc)
        raise InvalidTokenError(f"Invalid or expired access token: {exc}") from exc
