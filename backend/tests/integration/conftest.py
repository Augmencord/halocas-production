"""Shared pytest fixtures for HALOCAS end-to-end integration test suites."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.deps import get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models import Base, Machine, User, UserRole, Worker
from app.models.alert_log import AlertLog, DeliveryStatus
from app.services.notification import NotificationService
from app.services.storage import StorageService


@pytest.fixture
async def integration_db_engine() -> AsyncIterator[AsyncEngine]:
    """Provide an isolated in-memory SQLite async database engine."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def integration_db_session(
    integration_db_engine: AsyncEngine,
) -> AsyncIterator[AsyncSession]:
    """Yield an isolated transactional database session with schema pre-created."""
    session_factory = async_sessionmaker(
        integration_db_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
def sample_synthetic_frame() -> np.ndarray:
    """Generate a realistic 640x480 RGB uint8 frame with visual contrast."""
    frame = np.full((480, 640, 3), 40, dtype=np.uint8)
    # Draw simulated worker region
    frame[100:300, 200:280] = [200, 180, 50]
    # Draw simulated machinery region
    frame[80:400, 320:580] = [180, 80, 30]
    return frame


@pytest.fixture
def recorded_notifications() -> list[dict[str, Any]]:
    """Store dispatches sent via mock notification service."""
    return []


@pytest.fixture
def mock_notification_service(
    recorded_notifications: list[dict[str, Any]],
) -> NotificationService:
    """Provide a functional NotificationService mock capturing outgoing email dispatches."""
    service = MagicMock(spec=NotificationService)

    async def _mock_send_alert(
        supervisor_email: str,
        worker_name: str,
        distance: float,
        clip_url: str | None = None,
        incident_id: int | None = None,
        db_session: Any = None,
    ) -> bool:
        record = {
            "recipient_email": supervisor_email,
            "incident_id": incident_id,
            "worker_name": worker_name,
            "distance_meters": distance,
            "clip_url": clip_url,
        }
        recorded_notifications.append(record)
        if db_session is not None and incident_id is not None:
            log_entry = AlertLog(
                incident_id=incident_id,
                recipient_email=supervisor_email,
                delivery_status=DeliveryStatus.SENT,
                retry_count=0,
                sent_at=datetime.now(UTC),
            )
            db_session.add(log_entry)
            await db_session.flush()
        return True

    service.send_proximity_alert = AsyncMock(side_effect=_mock_send_alert)
    return service


@pytest.fixture
def uploaded_clips() -> dict[str, str]:
    """Store clips uploaded through mock storage service."""
    return {}


@pytest.fixture
def mock_storage_service(uploaded_clips: dict[str, str]) -> StorageService:
    """Provide a functional StorageService mock returning deterministic Cloudflare R2 URLs."""
    service = MagicMock(spec=StorageService)

    def _mock_build_object_key(incident_id: int, camera_id: str, timestamp: Any = None) -> str:
        _ = timestamp
        return f"clips/cam_{camera_id}/incident_{incident_id}.mp4"

    def _mock_upload_clip(
        local_path: str,
        object_key: str,
    ) -> str:
        url = f"https://storage.halocas.safety/{object_key}"
        uploaded_clips[object_key] = local_path
        return url

    def _mock_generate_presigned_url(object_key: str, expiry_seconds: int = 3600) -> str:
        return f"https://presigned.storage.halocas.safety/{object_key}?expires={expiry_seconds}"

    service.build_object_key = MagicMock(side_effect=_mock_build_object_key)
    service.upload_clip = MagicMock(side_effect=_mock_upload_clip)
    service.generate_presigned_url = MagicMock(side_effect=_mock_generate_presigned_url)
    return service


@pytest.fixture
async def seeded_integration_db(
    integration_db_session: AsyncSession,
) -> dict[str, Any]:
    """Seed integration database with standard machines, workers, and admin credentials."""
    admin_user = User(
        email="admin@halocas.safety",
        hashed_password=get_password_hash("AdminSecretPassword123!"),
        full_name="Integration Admin",
        role=UserRole.ADMIN,
        is_active=True,
        is_superuser=True,
    )
    operator_user = User(
        email="operator@halocas.safety",
        hashed_password=get_password_hash("OperatorSecretPassword123!"),
        full_name="Integration Operator",
        role=UserRole.OPERATOR,
        is_active=True,
        is_superuser=False,
    )
    machine = Machine(
        name="CAT 793F Mining Truck #101",
        type="Haul Truck",
        zone="Pit Alpha",
        status="active",
    )
    worker = Worker(
        name="Rajesh Kumar",
        role="Drill Operator",
        department="Drill & Blast",
        supervisor_email="supervisor@halocas.safety",
        face_embedding=[0.05] * 512,
        is_authorized=False,
    )
    authorized_worker = Worker(
        name="Priya Singh",
        role="Safety Inspector",
        department="Safety Inspection",
        supervisor_email="safety_head@halocas.safety",
        face_embedding=[0.12] * 512,
        is_authorized=True,
    )

    integration_db_session.add_all([admin_user, operator_user, machine, worker, authorized_worker])
    await integration_db_session.commit()
    await integration_db_session.refresh(admin_user)
    await integration_db_session.refresh(operator_user)
    await integration_db_session.refresh(machine)
    await integration_db_session.refresh(worker)
    await integration_db_session.refresh(authorized_worker)

    return {
        "admin": admin_user,
        "operator": operator_user,
        "machine": machine,
        "worker": worker,
        "authorized_worker": authorized_worker,
    }


@pytest.fixture
async def integration_api_client(
    integration_db_session: AsyncSession,
    seeded_integration_db: dict[str, Any],
) -> AsyncIterator[AsyncClient]:
    """Provide authenticated HTTP test client bound to FastAPI application with DB override."""
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield integration_db_session

    app.dependency_overrides[get_db] = override_get_db
    admin_user = seeded_integration_db["admin"]
    token = create_access_token(subject=admin_user.email, role="admin")

    transport = ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=headers) as client:
        yield client
    app.dependency_overrides.clear()
