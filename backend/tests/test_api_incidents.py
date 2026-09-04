"""Unit tests for safety incidents, filtering, video redirection, and stats."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db, get_storage_service
from app.core.security import create_access_token
from app.main import app
from app.models import (
    AlertLog,
    Base,
    DeliveryStatus,
    Incident,
    IncidentSeverity,
    Machine,
    User,
    UserRole,
    Worker,
)


@pytest.fixture
async def test_session() -> AsyncIterator[AsyncSession]:
    """Provide transactional in-memory database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def seed_data(test_session: AsyncSession) -> dict[str, Any]:
    """Seed test database with baseline users, machines, and incidents."""
    user = User(
        email="admin@halocas.safety",
        hashed_password="hash",
        full_name="Safety Administrator",
        role=UserRole.ADMIN,
        is_active=True,
    )
    test_session.add(user)

    machine = Machine(
        name="Excavator EX-200",
        type="Excavator",
        zone="Zone-1 Pit",
        status="ACTIVE",
    )
    test_session.add(machine)
    await test_session.flush()

    worker = Worker(
        name="John Doe",
        role="Operator",
        department="Mining Operations",
        is_authorized=True,
    )
    test_session.add(worker)
    await test_session.flush()

    inc_crit = Incident(
        timestamp=datetime.now(UTC),
        machine_id=machine.id,
        worker_id=worker.id,
        worker_name="John Doe",
        distance_meters=1.5,
        severity=IncidentSeverity.CRITICAL,
        closing_velocity=1.2,
        zone="Zone-1 Pit",
        face_match_confidence=0.88,
        clip_url="https://r2.example.com/incidents/2026/09/04/1_front.mp4",
    )
    inc_warn = Incident(
        timestamp=datetime.now(UTC) - timedelta(hours=2),
        machine_id=machine.id,
        worker_id=worker.id,
        worker_name="John Doe",
        distance_meters=4.5,
        severity=IncidentSeverity.WARNING,
        closing_velocity=0.4,
        zone="Zone-1 Pit",
        face_match_confidence=0.75,
    )
    test_session.add_all([inc_crit, inc_warn])
    await test_session.flush()

    alert_log = AlertLog(
        incident_id=inc_crit.id,
        recipient_email="supervisor@halocas.safety",
        delivery_status=DeliveryStatus.SENT,
        retry_count=0,
    )
    test_session.add(alert_log)
    await test_session.commit()

    return {
        "user": user,
        "machine": machine,
        "worker": worker,
        "inc_crit": inc_crit,
        "inc_warn": inc_warn,
    }


@pytest.fixture
async def client(test_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Create test client with DB override."""
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield test_session

    mock_storage = MagicMock()
    mock_storage.generate_presigned_url.return_value = "https://r2-presigned.example.com/clip.mp4?sig=xyz"

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage_service] = lambda: mock_storage

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_incidents_with_pagination(client: AsyncClient, seed_data: dict[str, Any]) -> None:
    """Verify list incidents pagination and X-Total-Count response header."""
    user = cast(User, seed_data["user"])
    token = create_access_token(subject=user.email, role=user.role.value)

    response = await client.get(
        "/api/v1/incidents?offset=0&limit=10",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.headers.get("X-Total-Count") == "2"
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_incidents_filter_by_severity(client: AsyncClient, seed_data: dict[str, Any]) -> None:
    """Verify filtering by severity tier."""
    user = cast(User, seed_data["user"])
    token = create_access_token(subject=user.email, role=user.role.value)

    response = await client.get(
        "/api/v1/incidents?severity=CRITICAL",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.headers.get("X-Total-Count") == "1"
    data = response.json()
    assert len(data) == 1
    assert data[0]["severity"] == "CRITICAL"


@pytest.mark.asyncio
async def test_get_incident_detail(client: AsyncClient, seed_data: dict[str, Any]) -> None:
    """Verify single incident detail retrieval with alert logs."""
    user = cast(User, seed_data["user"])
    inc_crit = cast(Incident, seed_data["inc_crit"])
    token = create_access_token(subject=user.email, role=user.role.value)

    response = await client.get(
        f"/api/v1/incidents/{inc_crit.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == inc_crit.id
    assert data["distance_meters"] == 1.5
    assert len(data["alert_logs"]) == 1
    assert data["alert_logs"][0]["delivery_status"] == "SENT"


@pytest.mark.asyncio
async def test_get_incident_not_found(client: AsyncClient, seed_data: dict[str, Any]) -> None:
    """Verify 404 response for non-existent incident ID."""
    user = cast(User, seed_data["user"])
    token = create_access_token(subject=user.email, role=user.role.value)

    response = await client.get(
        "/api/v1/incidents/99999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_incident_clip_redirect(client: AsyncClient, seed_data: dict[str, Any]) -> None:
    """Verify 307 temporary redirect to presigned R2 clip playback URL."""
    user = cast(User, seed_data["user"])
    inc_crit = cast(Incident, seed_data["inc_crit"])
    token = create_access_token(subject=user.email, role=user.role.value)

    response = await client.get(
        f"/api/v1/incidents/{inc_crit.id}/clip",
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=False,
    )
    assert response.status_code == 307
    assert "https://r2-presigned.example.com/clip.mp4" in response.headers["location"]


@pytest.mark.asyncio
async def test_get_incident_stats(client: AsyncClient, seed_data: dict[str, Any]) -> None:
    """Verify aggregate spatial proximity analytics and violation totals."""
    user = cast(User, seed_data["user"])
    token = create_access_token(subject=user.email, role=user.role.value)

    response = await client.get(
        "/api/v1/incidents/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_incidents"] == 2
    assert data["critical_count"] == 1
    assert data["warning_count"] == 1
    assert data["avg_distance_meters"] > 0
    assert "incidents_today" in data
