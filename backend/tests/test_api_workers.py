"""Unit and integration tests for worker personnel and face enrollment endpoints."""

from __future__ import annotations

import io
from collections.abc import AsyncIterator
from typing import Any, cast
from unittest.mock import MagicMock

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db, get_face_verifier, get_storage_service
from app.core.security import create_access_token
from app.main import app
from app.models import Base, User, UserRole, Worker


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
async def seed_worker_and_user(test_session: AsyncSession) -> dict[str, Any]:
    """Seed baseline operator user and worker."""
    user = User(
        email="operator@halocas.safety",
        hashed_password="hash",
        full_name="Operator",
        role=UserRole.OPERATOR,
        is_active=True,
    )
    worker = Worker(
        name="Elena Rostova",
        role="Shift Supervisor",
        department="Underground Haulage",
        supervisor_email="super@mine.example",
        is_authorized=True,
    )
    test_session.add_all([user, worker])
    await test_session.commit()
    await test_session.refresh(user)
    await test_session.refresh(worker)
    return {"user": user, "worker": worker}


@pytest.fixture
async def client(test_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Create test client with DB and service overrides."""
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield test_session

    mock_verifier = MagicMock()
    mock_verifier.extract_embedding.return_value = np.zeros((512,), dtype=np.float32)

    mock_storage = MagicMock()
    mock_storage.upload_clip.return_value = "https://r2.example.com/faces/1.jpg"

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_face_verifier] = lambda: mock_verifier
    app.dependency_overrides[get_storage_service] = lambda: mock_storage

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_workers(client: AsyncClient, seed_worker_and_user: dict[str, Any]) -> None:
    """Verify list workers with X-Total-Count pagination header."""
    user = cast(User, seed_worker_and_user["user"])
    token = create_access_token(subject=user.email, role=user.role.value)

    response = await client.get(
        "/api/v1/workers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.headers.get("X-Total-Count") == "1"
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Elena Rostova"
    assert data[0]["is_authorized"] is True


@pytest.mark.asyncio
async def test_create_worker(client: AsyncClient, seed_worker_and_user: dict[str, Any]) -> None:
    """Verify registration of a new worker profile."""
    user = cast(User, seed_worker_and_user["user"])
    token = create_access_token(subject=user.email, role=user.role.value)

    response = await client.post(
        "/api/v1/workers",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Carlos Gomez",
            "role": "Haul Truck Driver",
            "department": "Surface Logistics",
            "supervisor_email": "supervisor@mine.example",
            "is_authorized": False,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Carlos Gomez"
    assert data["is_authorized"] is False
    assert data["id"] > 0


@pytest.mark.asyncio
async def test_get_worker_detail(client: AsyncClient, seed_worker_and_user: dict[str, Any]) -> None:
    """Verify retrieval of worker detail profile."""
    user = cast(User, seed_worker_and_user["user"])
    worker = cast(Worker, seed_worker_and_user["worker"])
    token = create_access_token(subject=user.email, role=user.role.value)

    response = await client.get(
        f"/api/v1/workers/{worker.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == worker.id
    assert data["total_incidents"] == 0


@pytest.mark.asyncio
async def test_update_worker(client: AsyncClient, seed_worker_and_user: dict[str, Any]) -> None:
    """Verify updating worker details."""
    user = cast(User, seed_worker_and_user["user"])
    worker = cast(Worker, seed_worker_and_user["worker"])
    token = create_access_token(subject=user.email, role=user.role.value)

    response = await client.put(
        f"/api/v1/workers/{worker.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_authorized": False, "role": "Senior Supervisor"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_authorized"] is False
    assert data["role"] == "Senior Supervisor"


@pytest.mark.asyncio
async def test_enroll_face_success(client: AsyncClient, seed_worker_and_user: dict[str, Any]) -> None:
    """Verify uploading face photo extracts embedding and updates worker record."""
    user = cast(User, seed_worker_and_user["user"])
    worker = cast(Worker, seed_worker_and_user["worker"])
    token = create_access_token(subject=user.email, role=user.role.value)

    # Generate synthetic image bytes
    img = Image.new("RGB", (200, 200), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    photo_bytes = buf.getvalue()

    response = await client.post(
        f"/api/v1/workers/{worker.id}/enroll-face",
        headers={"Authorization": f"Bearer {token}"},
        files={"photo": ("face.jpg", photo_bytes, "image/jpeg")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["face_enrolled"] is True
    assert data["embedding_dimensions"] == 512
    assert "r2.example.com" in data["face_photo_url"]
