"""Unit and integration tests for authentication and user management endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models import Base, User, UserRole


@pytest.fixture
async def test_session() -> AsyncIterator[AsyncSession]:
    """Provide isolated SQLite database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def client(test_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Create async HTTP client with database dependency override."""
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield test_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def seed_users(test_session: AsyncSession) -> dict[str, User]:
    """Seed baseline admin and operator accounts into test DB."""
    admin = User(
        email="admin@halocas.safety",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Safety Admin",
        role=UserRole.ADMIN,
        is_active=True,
        is_superuser=True,
    )
    operator = User(
        email="operator@halocas.safety",
        hashed_password=get_password_hash("OperatorPass123!"),
        full_name="Console Operator",
        role=UserRole.OPERATOR,
        is_active=True,
        is_superuser=False,
    )
    inactive = User(
        email="inactive@halocas.safety",
        hashed_password=get_password_hash("InactivePass123!"),
        full_name="Inactive User",
        role=UserRole.OPERATOR,
        is_active=False,
        is_superuser=False,
    )
    test_session.add_all([admin, operator, inactive])
    await test_session.commit()
    await test_session.refresh(admin)
    await test_session.refresh(operator)
    await test_session.refresh(inactive)
    return {"admin": admin, "operator": operator, "inactive": inactive}


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, seed_users: dict[str, User]) -> None:
    """Verify login with correct credentials yields valid JWT token."""
    assert seed_users
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "operator@halocas.safety", "password": "OperatorPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, seed_users: dict[str, User]) -> None:
    """Verify rejection of incorrect password."""
    assert seed_users
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "operator@halocas.safety", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["message"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient, seed_users: dict[str, User]) -> None:
    """Verify rejection of unknown email address."""
    assert seed_users
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@halocas.safety", "password": "Password123!"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_deactivated_user(client: AsyncClient, seed_users: dict[str, User]) -> None:
    """Verify deactivated user account receives 403 Forbidden."""
    assert seed_users
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@halocas.safety", "password": "InactivePass123!"},
    )
    assert response.status_code == 403
    assert "deactivated" in response.json()["message"]


@pytest.mark.asyncio
async def test_register_user_as_admin(client: AsyncClient, seed_users: dict[str, User]) -> None:
    """Verify administrator can register new accounts."""
    admin_token = create_access_token(subject=seed_users["admin"].email, role="admin")

    response = await client.post(
        "/api/v1/auth/register",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": "newsupervisor@halocas.safety",
            "password": "SecurePassword123!",
            "full_name": "New Supervisor",
            "role": "supervisor",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newsupervisor@halocas.safety"
    assert data["role"] == "supervisor"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, seed_users: dict[str, User]) -> None:
    """Verify rejection when registering duplicate email address."""
    admin_token = create_access_token(subject=seed_users["admin"].email, role="admin")

    response = await client.post(
        "/api/v1/auth/register",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": "operator@halocas.safety",
            "password": "SecurePassword123!",
            "full_name": "Duplicate Operator",
            "role": "operator",
        },
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["message"]


@pytest.mark.asyncio
async def test_register_forbidden_for_non_admin(client: AsyncClient, seed_users: dict[str, User]) -> None:
    """Verify non-admin users cannot register new accounts."""
    operator_token = create_access_token(subject=seed_users["operator"].email, role="operator")

    response = await client.post(
        "/api/v1/auth/register",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "email": "another@halocas.safety",
            "password": "SecurePassword123!",
            "full_name": "Another User",
            "role": "operator",
        },
    )
    assert response.status_code == 403
