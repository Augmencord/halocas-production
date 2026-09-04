"""Integration tests for telemetry streaming, WebSocket, dashboard summary, and core app endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from starlette.testclient import TestClient

from app.api.deps import get_current_user, get_db
from app.api.routes.telemetry import manager
from app.core.security import create_access_token
from app.main import app
from app.models.base import Base
from app.models.incident import Incident, IncidentSeverity
from app.models.machine import Machine
from app.models.user import User, UserRole
from app.models.worker import Worker


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
        email="supervisor@halocas.safety",
        hashed_password="mock_hashed_password",
        full_name="Safety Supervisor",
        role=UserRole.SUPERVISOR,
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
async def seed_dashboard_data(test_session: AsyncSession) -> None:
    """Populate database with workers, machines, and incidents for dashboard testing."""
    worker = Worker(
        name="Alex Smith",
        role="Rigger",
        department="Rigging",
        is_authorized=True,
    )
    machine = Machine(
        name="Crane One",
        type="Crane",
        zone="Sector 1",
        status="ACTIVE",
    )
    test_session.add_all([worker, machine])
    await test_session.flush()

    incidents = [
        Incident(
            timestamp=datetime.now(UTC),
            machine_id=machine.id,
            worker_id=worker.id,
            worker_name=worker.name,
            distance_meters=1.8,
            severity=IncidentSeverity.CRITICAL,
            closing_velocity=0.5,
            zone="Sector 1",
        ),
        Incident(
            timestamp=datetime.now(UTC),
            machine_id=machine.id,
            worker_id=worker.id,
            worker_name=worker.name,
            distance_meters=4.2,
            severity=IncidentSeverity.WARNING,
            closing_velocity=0.2,
            zone="Sector 1",
        ),
    ]
    test_session.add_all(incidents)
    await test_session.commit()


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
async def test_dashboard_summary(
    test_client: AsyncClient,
    auth_headers: dict[str, str],
    seed_dashboard_data: None,
) -> None:
    """Verify aggregated safety metrics on the dashboard summary route."""
    assert seed_dashboard_data is None
    response = await test_client.get(
        "/api/v1/dashboard/summary",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["incidents_last_24h_count"] == 2
    assert data["critical_incidents_count"] >= 1
    assert data["active_machines_count"] == 1
    assert data["total_workers_count"] == 1
    assert len(data["recent_incidents"]) == 2


@pytest.mark.asyncio
async def test_live_mjpeg_stream() -> None:
    """Verify streaming multipart/x-mixed-replace generator produces valid MJPEG frames."""
    from app.api.routes.telemetry import mjpeg_frame_generator
    from app.core.buffer import BufferManager

    buf_mgr = BufferManager()
    gen = mjpeg_frame_generator("cam_front", buf_mgr)
    first_chunk = await anext(gen)
    assert b"--frame\r\n" in first_chunk
    assert b"Content-Type: image/jpeg\r\n" in first_chunk
    await gen.aclose()


def test_websocket_telemetry_flow() -> None:
    """Verify WebSocket handshake, ping-pong communication, and broadcast."""
    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/ws/telemetry") as websocket:
            # First frame is connection handshake
            handshake = websocket.receive_json()
            assert handshake["event"] == "connected"
            assert "HALOCAS" in handshake["message"]

            # Ping-pong heartbeat
            websocket.send_text("ping")
            pong = websocket.receive_json()
            assert pong["event"] == "pong"


@pytest.mark.asyncio
async def test_websocket_broadcast_manager() -> None:
    """Verify ConnectionManager broadcast method handles active/empty connections."""
    await manager.broadcast_json({"test": "data"})
    assert isinstance(manager.active_connections, list)


@pytest.mark.asyncio
async def test_root_endpoint(test_client: AsyncClient) -> None:
    """Verify root API metadata endpoint."""
    response = await test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "HALOCAS" in data["name"]
    assert "version" in data
    assert data["docs_url"] == "/docs"


@pytest.mark.asyncio
async def test_health_endpoint(test_client: AsyncClient) -> None:
    """Verify healthcheck endpoint reports healthy status."""
    response = await test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "timestamp" in data
    assert "service" in data


@pytest.mark.asyncio
async def test_404_not_found_handler(test_client: AsyncClient) -> None:
    """Verify global handling of nonexistent endpoints."""
    response = await test_client.get("/api/v1/nonexistent/resource")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_422_validation_error_handler(test_client: AsyncClient) -> None:
    """Verify global handling and formatting of request validation errors."""
    response = await test_client.post(
        "/api/v1/auth/login",
        json={"invalid_field": "test"},
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
