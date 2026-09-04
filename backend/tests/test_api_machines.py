"""Integration tests for Machine management API endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.deps import get_current_user, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.base import Base
from app.models.machine import Machine
from app.models.user import User, UserRole


@pytest.fixture
async def test_engine() -> AsyncIterator[AsyncEngine]:
    """Create isolated in-memory SQLite async engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Provide transactional session bound to test database."""
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
async def test_user(test_session: AsyncSession) -> User:
    """Create an authenticated operator user."""
    user = User(
        email="operator@halocas.safety",
        hashed_password="mock_hashed_password",
        full_name="Machine Operator",
        role=UserRole.OPERATOR,
        is_active=True,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest.fixture
async def auth_headers(test_user: User) -> dict[str, str]:
    """Generate Authorization header with valid JWT."""
    token = create_access_token(subject=test_user.id, role=test_user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def seed_machines(test_session: AsyncSession) -> list[Machine]:
    """Seed sample machines into database."""
    machines = [
        Machine(
            name="Forklift Alpha",
            type="Forklift",
            zone="Zone A",
            status="ACTIVE",
        ),
        Machine(
            name="Excavator Beta",
            type="Excavator",
            zone="Zone B",
            status="ACTIVE",
        ),
        Machine(
            name="Haul Truck Gamma",
            type="Haul Truck",
            zone="Zone A",
            status="MAINTENANCE",
        ),
    ]
    test_session.add_all(machines)
    await test_session.commit()
    for m in machines:
        await test_session.refresh(m)
    return machines


@pytest.fixture
async def test_client(
    test_session: AsyncSession,
    test_user: User,
) -> AsyncIterator[AsyncClient]:
    """FastAPI async client with overridden database and user dependencies."""

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield test_session

    async def override_get_current_user() -> User:
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_machines(
    test_client: AsyncClient,
    auth_headers: dict[str, str],
    seed_machines: list[Machine],
) -> None:
    """Verify paginated listing of machines with X-Total-Count header."""
    assert seed_machines
    response = await test_client.get(
        "/api/v1/machines",
        headers=auth_headers,
        params={"limit": 2, "offset": 0},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert response.headers.get("X-Total-Count") == "3"


@pytest.mark.asyncio
async def test_create_machine_success(
    test_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Verify registration of a new industrial machine."""
    payload = {
        "name": "Reach Stacker Delta",
        "type": "Reach Stacker",
        "zone": "Bay 4",
        "status": "ACTIVE",
    }
    response = await test_client.post(
        "/api/v1/machines",
        headers=auth_headers,
        json=payload,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Reach Stacker Delta"
    assert data["type"] == "Reach Stacker"
    assert data["zone"] == "Bay 4"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_update_machine_status_success(
    test_client: AsyncClient,
    auth_headers: dict[str, str],
    seed_machines: list[Machine],
) -> None:
    """Verify updating a machine's operational status."""
    target_machine = seed_machines[0]
    payload = {
        "status": "OFFLINE",
    }
    response = await test_client.put(
        f"/api/v1/machines/{target_machine.id}/status",
        headers=auth_headers,
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == target_machine.id
    assert data["status"] == "OFFLINE"


@pytest.mark.asyncio
async def test_update_machine_status_not_found(
    test_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Verify 404 response when attempting to update nonexistent machine."""
    payload = {
        "status": "MAINTENANCE",
    }
    response = await test_client.put(
        "/api/v1/machines/99999/status",
        headers=auth_headers,
        json=payload,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Machine with ID 99999 not found"
