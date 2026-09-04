"""Comprehensive integration tests for all HALOCAS REST and WebSocket API endpoints.

Covers:
1. Authentication (login, invalid password, inactive user, expired and invalid tokens)
2. Workers CRUD (create, list, get, update, not-found, and validation errors)
3. Incidents (list, filter by severity/machine, detail, and clip URL redirection)
4. Machines (create, update status, list, not-found, and validation errors)
5. WebSocket telemetry (connect handshake, ping-pong, broadcast message receipt)
6. Health check (/health, /api/v1/status, and root /)
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.deps import get_db, get_storage_service
from app.api.routes.telemetry import manager
from app.core.security import create_access_token, get_password_hash
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
from app.services.storage import StorageService

# ==============================================================================
# Database & Client Fixtures
# ==============================================================================


@pytest.fixture
async def api_engine() -> AsyncIterator[AsyncEngine]:
    """Provide an isolated in-memory SQLite async engine."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def api_session(api_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Yield a transactional database session."""
    session_factory = async_sessionmaker(
        bind=api_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
def mock_storage() -> StorageService:
    """Provide a mock StorageService for presigned clip URL generation."""
    storage = MagicMock(spec=StorageService)
    storage.generate_presigned_url.return_value = (
        "https://presigned.r2.cloudflarestorage.com/incidents/cam_front/clip_101.mp4?token=valid"
    )
    return storage


@pytest.fixture
async def seeded_entities(api_session: AsyncSession) -> dict[str, Any]:
    """Seed baseline admin user, inactive user, worker, machine, and incident."""
    admin_user = User(
        email="admin@halocas.safety",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Safety Administrator",
        role=UserRole.ADMIN,
        is_active=True,
        is_superuser=True,
    )
    inactive_user = User(
        email="inactive@halocas.safety",
        hashed_password=get_password_hash("InactivePass123!"),
        full_name="Deactivated Operator",
        role=UserRole.OPERATOR,
        is_active=False,
        is_superuser=False,
    )
    worker = Worker(
        name="Rajesh Kumar",
        role="Drill Operator",
        department="Drill & Blast",
        supervisor_email="mine_supervisor@halocas.safety",
        is_authorized=False,
    )
    machine = Machine(
        name="CAT 793F Haul Truck",
        type="haul_truck",
        zone="pit_a",
        status="ACTIVE",
    )
    api_session.add_all([admin_user, inactive_user, worker, machine])
    await api_session.commit()
    await api_session.refresh(admin_user)
    await api_session.refresh(inactive_user)
    await api_session.refresh(worker)
    await api_session.refresh(machine)

    incident_crit = Incident(
        timestamp=datetime.now(UTC),
        machine_id=machine.id,
        worker_id=worker.id,
        worker_name=worker.name,
        distance_meters=1.8,
        severity=IncidentSeverity.CRITICAL,
        closing_velocity=2.4,
        supervisor_notified=True,
        supervisor_email="mine_supervisor@halocas.safety",
        zone="pit_a",
        clip_url="https://storage.halocas.safety/incidents/cam_front/clip_101.mp4",
    )
    incident_warn = Incident(
        timestamp=datetime.now(UTC),
        machine_id=machine.id,
        worker_id=worker.id,
        worker_name=worker.name,
        distance_meters=6.2,
        severity=IncidentSeverity.WARNING,
        closing_velocity=0.5,
        supervisor_notified=False,
        supervisor_email=None,
        zone="pit_a",
        clip_url=None,
    )
    api_session.add_all([incident_crit, incident_warn])
    await api_session.commit()
    await api_session.refresh(incident_crit)
    await api_session.refresh(incident_warn)

    alert_log = AlertLog(
        incident_id=incident_crit.id,
        recipient_email="mine_supervisor@halocas.safety",
        delivery_status=DeliveryStatus.SENT,
        retry_count=0,
        sent_at=datetime.now(UTC),
    )
    api_session.add(alert_log)
    await api_session.commit()

    return {
        "admin": admin_user,
        "inactive": inactive_user,
        "worker": worker,
        "machine": machine,
        "incident_critical": incident_crit,
        "incident_warning": incident_warn,
    }


@pytest.fixture
async def api_client(
    api_session: AsyncSession,
    mock_storage: StorageService,
) -> AsyncIterator[AsyncClient]:
    """Provide an AsyncClient with database and storage dependency overrides."""
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield api_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage_service] = lambda: mock_storage

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(seeded_entities: dict[str, Any]) -> dict[str, str]:
    """Generate bearer authentication headers for the seeded admin user."""
    admin: User = seeded_entities["admin"]
    token = create_access_token(
        subject=str(admin.id),
        role=admin.role.value,
        expires_delta=timedelta(hours=1),
        extra_claims={"email": admin.email},
    )
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. Authentication Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_auth_login_success(
    api_client: AsyncClient,
    seeded_entities: dict[str, Any],
) -> None:
    """Verify valid credentials return a 200 OK response with a valid JWT access token."""
    admin: User = seeded_entities["admin"]
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": admin.email, "password": "AdminPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"].lower() == "bearer"
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_auth_login_invalid_password(
    api_client: AsyncClient,
    seeded_entities: dict[str, Any],
) -> None:
    """Verify login with incorrect password returns 401 Unauthorized."""
    admin: User = seeded_entities["admin"]
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": admin.email, "password": "WrongPassword999!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "Incorrect email or password" in data["detail"]


@pytest.mark.asyncio
async def test_auth_login_nonexistent_user(
    api_client: AsyncClient,
) -> None:
    """Verify login with unregistered email returns 401 Unauthorized."""
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@halocas.safety", "password": "AnyPassword123!"},
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_auth_login_inactive_user(
    api_client: AsyncClient,
    seeded_entities: dict[str, Any],
) -> None:
    """Verify login for deactivated account returns 403 Forbidden."""
    inactive: User = seeded_entities["inactive"]
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": inactive.email, "password": "InactivePass123!"},
    )
    assert response.status_code == 403
    assert "deactivated" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_auth_protected_route_token_validation(
    api_client: AsyncClient,
    seeded_entities: dict[str, Any],
) -> None:
    """Verify protected endpoints reject requests with missing, invalid, or expired tokens."""
    admin: User = seeded_entities["admin"]

    # 1. Missing token
    res_no_token = await api_client.get("/api/v1/workers")
    assert res_no_token.status_code == 401

    # 2. Malformed / invalid signature token
    res_invalid_token = await api_client.get(
        "/api/v1/workers",
        headers={"Authorization": "Bearer invalid.jwt.token.signature"},
    )
    assert res_invalid_token.status_code == 401

    # 3. Expired token
    expired_token = create_access_token(
        subject=str(admin.id),
        role=admin.role.value,
        expires_delta=timedelta(seconds=-60),
        extra_claims={"email": admin.email},
    )
    res_expired_token = await api_client.get(
        "/api/v1/workers",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res_expired_token.status_code == 401


# ==============================================================================
# 2. Workers CRUD Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_workers_crud_lifecycle(
    api_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Verify complete worker CRUD: create, list, get by ID, and update."""
    # 1. CREATE WORKER
    create_payload = {
        "name": "Amit Sharma",
        "role": "Loader Driver",
        "department": "Operations",
        "supervisor_email": "operations_lead@halocas.safety",
        "is_authorized": False,
    }
    create_res = await api_client.post(
        "/api/v1/workers",
        json=create_payload,
        headers=auth_headers,
    )
    assert create_res.status_code == 201
    worker_data = create_res.json()
    worker_id: int = worker_data["id"]
    assert worker_data["name"] == "Amit Sharma"
    assert worker_data["role"] == "Loader Driver"
    assert worker_data["is_authorized"] is False

    # 2. LIST WORKERS
    list_res = await api_client.get("/api/v1/workers", headers=auth_headers)
    assert list_res.status_code == 200
    workers = list_res.json()
    assert any(w["id"] == worker_id for w in workers)
    assert "X-Total-Count" in list_res.headers
    assert int(list_res.headers["X-Total-Count"]) >= 1

    # 3. GET WORKER DETAIL
    get_res = await api_client.get(f"/api/v1/workers/{worker_id}", headers=auth_headers)
    assert get_res.status_code == 200
    detail_data = get_res.json()
    assert detail_data["id"] == worker_id
    assert detail_data["name"] == "Amit Sharma"
    assert "total_incidents" in detail_data
    assert "recent_incidents" in detail_data

    # 4. UPDATE WORKER
    update_payload = {
        "role": "Senior Heavy Equipment Operator",
        "is_authorized": True,
    }
    update_res = await api_client.put(
        f"/api/v1/workers/{worker_id}",
        json=update_payload,
        headers=auth_headers,
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["role"] == "Senior Heavy Equipment Operator"
    assert updated_data["is_authorized"] is True


@pytest.mark.asyncio
async def test_workers_validation_errors_and_not_found(
    api_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Verify 422 for schema validation errors and 404 for nonexistent worker IDs."""
    # 1. Validation error: missing required "name"
    bad_res = await api_client.post(
        "/api/v1/workers",
        json={"role": "Mechanic", "department": "Maintenance"},
        headers=auth_headers,
    )
    assert bad_res.status_code == 422

    # 2. Nonexistent worker get
    not_found_get = await api_client.get("/api/v1/workers/999999", headers=auth_headers)
    assert not_found_get.status_code == 404

    # 3. Nonexistent worker update
    not_found_put = await api_client.put(
        "/api/v1/workers/999999",
        json={"role": "Supervisor"},
        headers=auth_headers,
    )
    assert not_found_put.status_code == 404


# ==============================================================================
# 3. Incidents Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_incidents_list_and_filters(
    api_client: AsyncClient,
    auth_headers: dict[str, str],
    seeded_entities: dict[str, Any],
) -> None:
    """Verify safety incidents listing, pagination headers, and severity/machine filtering."""
    machine: Machine = seeded_entities["machine"]

    # 1. List all incidents
    list_res = await api_client.get("/api/v1/incidents", headers=auth_headers)
    assert list_res.status_code == 200
    all_incidents = list_res.json()
    assert len(all_incidents) >= 2
    assert "X-Total-Count" in list_res.headers
    assert int(list_res.headers["X-Total-Count"]) >= 2

    # 2. Filter by severity=CRITICAL
    crit_res = await api_client.get("/api/v1/incidents?severity=CRITICAL", headers=auth_headers)
    assert crit_res.status_code == 200
    crit_incidents = crit_res.json()
    assert len(crit_incidents) >= 1
    assert all(inc["severity"] == "CRITICAL" for inc in crit_incidents)

    # 3. Filter by machine_id
    machine_res = await api_client.get(f"/api/v1/incidents?machine_id={machine.id}", headers=auth_headers)
    assert machine_res.status_code == 200
    machine_incidents = machine_res.json()
    assert len(machine_incidents) >= 2
    assert all(inc["machine_id"] == machine.id for inc in machine_incidents)


@pytest.mark.asyncio
async def test_incidents_detail_and_clip_url(
    api_client: AsyncClient,
    auth_headers: dict[str, str],
    seeded_entities: dict[str, Any],
) -> None:
    """Verify incident detail retrieval and presigned clip URL redirection."""
    crit_incident: Incident = seeded_entities["incident_critical"]
    warn_incident: Incident = seeded_entities["incident_warning"]

    # 1. Incident detail with alert logs
    detail_res = await api_client.get(
        f"/api/v1/incidents/{crit_incident.id}",
        headers=auth_headers,
    )
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["id"] == crit_incident.id
    assert detail_data["severity"] == "CRITICAL"
    assert detail_data["distance_meters"] == pytest.approx(1.8)
    assert len(detail_data["alert_logs"]) >= 1

    # 2. Presigned clip URL redirect (HTTP 307)
    clip_res = await api_client.get(
        f"/api/v1/incidents/{crit_incident.id}/clip",
        headers=auth_headers,
    )
    assert clip_res.status_code == 307
    location_header = clip_res.headers.get("location")
    assert location_header is not None
    assert "https://presigned.r2.cloudflarestorage.com/" in location_header

    # 3. Incident without clip URL returns 404
    no_clip_res = await api_client.get(
        f"/api/v1/incidents/{warn_incident.id}/clip",
        headers=auth_headers,
    )
    assert no_clip_res.status_code == 404

    # 4. Nonexistent incident returns 404
    not_found_res = await api_client.get(
        "/api/v1/incidents/999999",
        headers=auth_headers,
    )
    assert not_found_res.status_code == 404


# ==============================================================================
# 4. Machines Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_machines_crud_and_status_update(
    api_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Verify machine equipment registration, listing, and operational status updates."""
    # 1. CREATE MACHINE
    create_payload = {
        "name": "Komatsu PC2000 Excavator",
        "type": "excavator",
        "zone": "pit_alpha",
        "status": "ACTIVE",
    }
    create_res = await api_client.post(
        "/api/v1/machines",
        json=create_payload,
        headers=auth_headers,
    )
    assert create_res.status_code == 201
    machine_data = create_res.json()
    machine_id: int = machine_data["id"]
    assert machine_data["name"] == "Komatsu PC2000 Excavator"
    assert machine_data["type"] == "excavator"
    assert machine_data["status"] == "ACTIVE"

    # 2. LIST MACHINES
    list_res = await api_client.get("/api/v1/machines", headers=auth_headers)
    assert list_res.status_code == 200
    machines = list_res.json()
    assert any(m["id"] == machine_id for m in machines)
    assert "X-Total-Count" in list_res.headers
    assert int(list_res.headers["X-Total-Count"]) >= 1

    # 3. UPDATE MACHINE STATUS
    update_res = await api_client.put(
        f"/api/v1/machines/{machine_id}/status",
        json={"status": "MAINTENANCE"},
        headers=auth_headers,
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["id"] == machine_id
    assert updated_data["status"] == "MAINTENANCE"

    # 4. UPDATE STATUS ON NONEXISTENT MACHINE
    not_found_res = await api_client.put(
        "/api/v1/machines/999999/status",
        json={"status": "OFFLINE"},
        headers=auth_headers,
    )
    assert not_found_res.status_code == 404

    # 5. VALIDATION ERROR: MISSING REQUIRED FIELDS
    bad_res = await api_client.post(
        "/api/v1/machines",
        json={"name": "Forklift Unit"},
        headers=auth_headers,
    )
    assert bad_res.status_code == 422


# ==============================================================================
# 5. WebSocket Telemetry Tests
# ==============================================================================


def test_websocket_telemetry_connect_and_json_exchange() -> None:
    """Verify WebSocket client handshake, ping-pong heartbeat, and broadcast reception."""
    client = TestClient(app)

    with client.websocket_connect("/api/v1/ws/telemetry") as ws:
        # 1. Receive initial connection handshake payload
        initial_msg = ws.receive_json()
        assert initial_msg["event"] == "connected"
        assert "HALOCAS" in initial_msg["message"]
        assert "timestamp" in initial_msg

        # 2. Client sends ping heartbeat
        ws.send_text("ping")
        pong_msg = ws.receive_json()
        assert pong_msg["event"] == "pong"
        assert "timestamp" in pong_msg

        # 3. Server-initiated broadcast message delivery
        broadcast_payload = {
            "event": "proximity_breach",
            "incident_id": 42,
            "machine": "CAT 793F Haul Truck",
            "distance_meters": 1.5,
            "severity": "CRITICAL",
        }
        asyncio.run(manager.broadcast_json(broadcast_payload))

        received_broadcast = ws.receive_json()
        assert received_broadcast["event"] == "proximity_breach"
        assert received_broadcast["incident_id"] == 42
        assert received_broadcast["severity"] == "CRITICAL"


# ==============================================================================
# 6. Health Check Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_health_check_service(api_client: AsyncClient) -> None:
    """Verify root /health endpoint returns service health, uptime, and version."""
    response = await api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "halocas-backend"
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0
    assert "version" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_system_status_subsystems(api_client: AsyncClient) -> None:
    """Verify /api/v1/status endpoint returns semantic version and subsystem operational health."""
    response = await api_client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "version" in data
    assert "subsystems" in data
    subsystems = data["subsystems"]
    assert "vision_engine" in subsystems
    assert "proximity_detector" in subsystems
    assert "alert_dispatcher" in subsystems
    assert "storage" in subsystems
    assert "telemetry_stream" in subsystems


@pytest.mark.asyncio
async def test_root_information_endpoint(api_client: AsyncClient) -> None:
    """Verify root / endpoint returns platform identity and API documentation routes."""
    response = await api_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert data["docs_url"] == "/docs"
    assert data["health_url"] == "/health"
    assert data["api_v1_url"] == "/api/v1"
