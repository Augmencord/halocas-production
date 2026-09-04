"""Comprehensive unit tests for security, authentication dependencies, session generators, and auth routes."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api import deps
from app.api.deps import (
    get_buffer_manager,
    get_current_admin_user,
    get_current_user,
    get_db,
    get_detector,
    get_face_verifier,
    get_notification_service,
    get_storage_service,
)
from app.api.routes.auth import login, register
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.db.session import get_db_session
from app.models import Base, User, UserRole
from app.schemas.auth import LoginRequest, UserCreate


@pytest.fixture
async def auth_db_session() -> AsyncIterator[AsyncSession]:
    """Provide an isolated in-memory SQLite database session for auth tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


# ==============================================================================
# 1. Cryptographic Security & Password Hashing Unit Tests (app.core.security)
# ==============================================================================


def test_password_hashing_and_verification() -> None:
    """Verify password hashing produces salted hashes and verifies accurately."""
    raw_secret = "UltraSecurePassword2026!"
    hashed = get_password_hash(raw_secret)

    assert hashed != raw_secret
    assert hashed.startswith("$2b$")
    assert verify_password(raw_secret, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


def test_verify_password_invalid_hash_exception_handling() -> None:
    """Verify corrupted or malformed bcrypt hash triggers exception handler and returns False."""
    malformed_hash = "not_a_real_bcrypt_hash_value"
    assert verify_password("AnyPassword!", malformed_hash) is False
    assert verify_password("", "") is False


def test_jwt_create_and_decode_token_standard() -> None:
    """Verify JWT access token creation and decoding with standard claims."""
    subject = "engineer@halocas.safety"
    token = create_access_token(subject=subject, role="operator")

    payload = decode_access_token(token)
    assert payload["sub"] == subject
    assert payload["role"] == "operator"
    assert "iat" in payload
    assert "exp" in payload
    assert payload["exp"] > payload["iat"]


def test_jwt_create_and_decode_token_custom_claims_and_expiry() -> None:
    """Verify JWT creation with custom expiry delta and auxiliary claims dictionary."""
    subject = "supervisor@halocas.safety"
    extra_data = {"department": "Underground Safety", "site_id": "pit-alpha-4"}
    custom_delta = timedelta(hours=2)

    token = create_access_token(
        subject=subject,
        role="supervisor",
        expires_delta=custom_delta,
        extra_claims=extra_data,
    )

    payload = decode_access_token(token)
    assert payload["sub"] == subject
    assert payload["role"] == "supervisor"
    assert payload["department"] == "Underground Safety"
    assert payload["site_id"] == "pit-alpha-4"
    assert payload["exp"] - payload["iat"] >= 7190


def test_jwt_decode_expired_token_raises_invalid_token_error() -> None:
    """Verify expired token causes decode_access_token to raise InvalidTokenError."""
    negative_delta = timedelta(seconds=-10)
    expired_token = create_access_token(
        subject="expired_user@halocas.safety",
        expires_delta=negative_delta,
    )

    with pytest.raises(InvalidTokenError) as exc_info:
        decode_access_token(expired_token)
    assert "Invalid or expired access token" in str(exc_info.value)


def test_jwt_decode_tampered_token_raises_invalid_token_error() -> None:
    """Verify malformed or signature-tampered JWT causes decode_access_token to raise InvalidTokenError."""
    valid_token = create_access_token(subject="valid@halocas.safety")
    tampered_token = valid_token[:-6] + "xxxxxx"

    with pytest.raises(InvalidTokenError):
        decode_access_token(tampered_token)

    with pytest.raises(InvalidTokenError):
        decode_access_token("completely.bogus.jwt")


# ==============================================================================
# 2. Database Session Generator Unit Tests (app.db.session & app.api.deps)
# ==============================================================================


@pytest.mark.asyncio
async def test_get_db_session_lifecycle() -> None:
    """Verify get_db_session yields an active AsyncSession and properly closes."""
    session_count = 0
    async for session in get_db_session():
        assert isinstance(session, AsyncSession)
        session_count += 1
    assert session_count == 1


@pytest.mark.asyncio
async def test_get_db_session_exception_rollback() -> None:
    """Verify get_db_session executes rollback when an unhandled exception occurs."""
    with pytest.raises(RuntimeError, match="Simulated transaction failure"):
        async for session in get_db_session():
            assert isinstance(session, AsyncSession)
            raise RuntimeError("Simulated transaction failure")


@pytest.mark.asyncio
async def test_get_db_dependency_generator() -> None:
    """Verify FastAPI get_db dependency yields active database session."""
    session_count = 0
    async for session in get_db():
        assert isinstance(session, AsyncSession)
        session_count += 1
    assert session_count == 1


# ==============================================================================
# 3. Authentication & Authorization Dependency Unit Tests (app.api.deps)
# ==============================================================================


@pytest.mark.asyncio
async def test_get_current_user_by_email_success(auth_db_session: AsyncSession) -> None:
    """Verify get_current_user successfully resolves active user from token email subject."""
    user = User(
        email="operator1@halocas.safety",
        hashed_password=get_password_hash("SecretPassword123!"),
        full_name="Console Operator",
        role=UserRole.OPERATOR,
        is_active=True,
    )
    auth_db_session.add(user)
    await auth_db_session.commit()
    await auth_db_session.refresh(user)

    token = create_access_token(subject=user.email, role="operator")
    authenticated = await get_current_user(db=auth_db_session, token=token)

    assert authenticated.id == user.id
    assert authenticated.email == user.email


@pytest.mark.asyncio
async def test_get_current_user_by_integer_id_success(auth_db_session: AsyncSession) -> None:
    """Verify get_current_user resolves user when token subject is an integer primary key."""
    user = User(
        email="tech@halocas.safety",
        hashed_password=get_password_hash("SecretPassword123!"),
        full_name="Technician",
        role=UserRole.OPERATOR,
        is_active=True,
    )
    auth_db_session.add(user)
    await auth_db_session.commit()
    await auth_db_session.refresh(user)

    token = create_access_token(subject=str(user.id), role="operator")
    authenticated = await get_current_user(db=auth_db_session, token=token)

    assert authenticated.id == user.id
    assert authenticated.email == user.email


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(auth_db_session: AsyncSession) -> None:
    """Verify get_current_user raises 401 Unauthorized on invalid token."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(db=auth_db_session, token="invalid.token.string")
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


@pytest.mark.asyncio
async def test_get_current_user_missing_sub_claim(auth_db_session: AsyncSession) -> None:
    """Verify get_current_user raises 401 when token payload lacks 'sub' claim."""
    with patch("app.api.deps.decode_access_token", return_value={"role": "operator"}):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(db=auth_db_session, token="dummy.token")
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_current_user_not_found(auth_db_session: AsyncSession) -> None:
    """Verify get_current_user raises 401 when token subject does not exist in DB."""
    token = create_access_token(subject="nonexistent@halocas.safety")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(db=auth_db_session, token=token)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_current_user_inactive_account(auth_db_session: AsyncSession) -> None:
    """Verify get_current_user raises 403 Forbidden when user account is deactivated."""
    user = User(
        email="inactive_op@halocas.safety",
        hashed_password=get_password_hash("SecretPassword123!"),
        full_name="Inactive Operator",
        role=UserRole.OPERATOR,
        is_active=False,
    )
    auth_db_session.add(user)
    await auth_db_session.commit()
    await auth_db_session.refresh(user)

    token = create_access_token(subject=user.email)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(db=auth_db_session, token=token)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "deactivated" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_admin_user_success() -> None:
    """Verify get_current_admin_user permits admin role and superusers."""
    admin_user = User(
        id=1,
        email="admin@halocas.safety",
        hashed_password="hash",
        full_name="Admin",
        role=UserRole.ADMIN,
        is_active=True,
        is_superuser=False,
    )
    res = await get_current_admin_user(current_user=admin_user)
    assert res == admin_user

    superuser = User(
        id=2,
        email="super@halocas.safety",
        hashed_password="hash",
        full_name="Superuser",
        role=UserRole.OPERATOR,
        is_active=True,
        is_superuser=True,
    )
    res_super = await get_current_admin_user(current_user=superuser)
    assert res_super == superuser


@pytest.mark.asyncio
async def test_get_current_admin_user_forbidden() -> None:
    """Verify get_current_admin_user raises 403 Forbidden for non-admin accounts."""
    operator_user = User(
        id=3,
        email="operator@halocas.safety",
        hashed_password="hash",
        full_name="Standard Operator",
        role=UserRole.OPERATOR,
        is_active=True,
        is_superuser=False,
    )
    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin_user(current_user=operator_user)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "Administrative privileges required" in exc_info.value.detail


def test_core_singleton_getters() -> None:
    """Verify singletons returned by get_detector, get_storage_service, etc."""
    mock_detector = MagicMock()
    mock_verifier = MagicMock()
    mock_buffer = MagicMock()
    mock_storage = MagicMock()
    mock_notification = MagicMock()

    with patch.object(deps, "_detector_instance", mock_detector):
        assert get_detector() == mock_detector

    with patch.object(deps, "_face_verifier_instance", mock_verifier):
        assert get_face_verifier() == mock_verifier

    with patch.object(deps, "_buffer_manager_instance", mock_buffer):
        assert get_buffer_manager() == mock_buffer

    with patch.object(deps, "_storage_service_instance", mock_storage):
        assert get_storage_service() == mock_storage

    with patch.object(deps, "_notification_service_instance", mock_notification):
        assert get_notification_service() == mock_notification


def test_core_singleton_lazy_initialization() -> None:
    """Verify singleton getters instantiate new instances when global reference is None."""
    with patch("app.api.deps.Detector") as mock_det_cls:
        with patch.object(deps, "_detector_instance", None):
            res_det = get_detector()
            assert res_det == mock_det_cls.return_value

    with patch("app.api.deps.FaceVerifier") as mock_face_cls:
        with patch.object(deps, "_face_verifier_instance", None):
            res_face = get_face_verifier()
            assert res_face == mock_face_cls.return_value

    with patch("app.api.deps.BufferManager") as mock_buf_cls:
        with patch.object(deps, "_buffer_manager_instance", None):
            res_buf = get_buffer_manager()
            assert res_buf == mock_buf_cls.return_value

    with patch("app.api.deps.StorageService") as mock_storage_cls:
        with patch.object(deps, "_storage_service_instance", None):
            res_storage = get_storage_service()
            assert res_storage == mock_storage_cls.return_value

    with patch("app.api.deps.NotificationService") as mock_notif_cls:
        with patch.object(deps, "_notification_service_instance", None):
            res_notif = get_notification_service()
            assert res_notif == mock_notif_cls.return_value


# ==============================================================================
# 4. Authentication API Route Function Unit Tests (app.api.routes.auth)
# ==============================================================================


@pytest.mark.asyncio
async def test_auth_route_login_direct(auth_db_session: AsyncSession) -> None:
    """Verify login route function executes full authentication and returns token."""
    user = User(
        email="direct_user@halocas.safety",
        hashed_password=get_password_hash("DirectSecret123!"),
        full_name="Direct Tester",
        role=UserRole.SUPERVISOR,
        is_active=True,
    )
    auth_db_session.add(user)
    await auth_db_session.commit()
    await auth_db_session.refresh(user)

    payload = LoginRequest(email="direct_user@halocas.safety", password="DirectSecret123!")
    token_response = await login(payload=payload, db=auth_db_session)

    assert token_response.access_token is not None
    assert token_response.token_type == "bearer"
    assert token_response.expires_in > 0
    assert user.last_login_at is not None


@pytest.mark.asyncio
async def test_auth_route_login_incorrect_password(auth_db_session: AsyncSession) -> None:
    """Verify login route raises 401 when given an invalid password."""
    user = User(
        email="pwd_user@halocas.safety",
        hashed_password=get_password_hash("CorrectSecret123!"),
        full_name="Password Tester",
        role=UserRole.OPERATOR,
        is_active=True,
    )
    auth_db_session.add(user)
    await auth_db_session.commit()

    payload = LoginRequest(email="pwd_user@halocas.safety", password="WrongPassword!")
    with pytest.raises(HTTPException) as exc_info:
        await login(payload=payload, db=auth_db_session)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_auth_route_login_deactivated_account(auth_db_session: AsyncSession) -> None:
    """Verify login route raises 403 when attempting to login with deactivated account."""
    user = User(
        email="deactivated@halocas.safety",
        hashed_password=get_password_hash("Secret123!"),
        full_name="Deactivated Tester",
        role=UserRole.OPERATOR,
        is_active=False,
    )
    auth_db_session.add(user)
    await auth_db_session.commit()

    payload = LoginRequest(email="deactivated@halocas.safety", password="Secret123!")
    with pytest.raises(HTTPException) as exc_info:
        await login(payload=payload, db=auth_db_session)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_auth_route_register_direct(auth_db_session: AsyncSession) -> None:
    """Verify register route successfully creates user record in database."""
    admin_user = User(
        email="admin_creator@halocas.safety",
        hashed_password="hash",
        full_name="Admin Creator",
        role=UserRole.ADMIN,
        is_active=True,
    )
    payload = UserCreate(
        email="new_worker@halocas.safety",
        password="SecureWorkerPass123!",
        full_name="New Site Worker",
        role=UserRole.OPERATOR,
    )

    created = await register(payload=payload, db=auth_db_session, _=admin_user)
    assert created.email == "new_worker@halocas.safety"
    assert created.full_name == "New Site Worker"
    assert created.role == UserRole.OPERATOR
    assert created.is_active is True


@pytest.mark.asyncio
async def test_auth_route_register_duplicate_email(auth_db_session: AsyncSession) -> None:
    """Verify register route raises 400 when attempting to register duplicate email."""
    existing_user = User(
        email="existing@halocas.safety",
        hashed_password="hash",
        full_name="Existing User",
        role=UserRole.OPERATOR,
        is_active=True,
    )
    auth_db_session.add(existing_user)
    await auth_db_session.commit()

    admin_user = User(
        email="admin@halocas.safety",
        hashed_password="hash",
        full_name="Admin",
        role=UserRole.ADMIN,
    )
    payload = UserCreate(
        email="existing@halocas.safety",
        password="AnotherPassword123!",
        full_name="Duplicate Attempt",
        role=UserRole.OPERATOR,
    )

    with pytest.raises(HTTPException) as exc_info:
        await register(payload=payload, db=auth_db_session, _=admin_user)
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in exc_info.value.detail
