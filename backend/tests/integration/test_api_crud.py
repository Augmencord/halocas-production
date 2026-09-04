"""End-to-end integration tests: Worker and Incident CRUD workflows through REST API endpoints."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from unittest.mock import MagicMock

import cv2
import numpy as np
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_face_verifier, get_storage_service
from app.main import app
from app.models import Incident, IncidentSeverity, Machine, Worker


@pytest.mark.asyncio
async def test_worker_full_crud_lifecycle(
    integration_api_client: AsyncClient,
) -> None:
    """Verify complete worker lifecycle: creation, retrieval, updates, and paginated listing."""
    # 1. CREATE WORKER
    create_payload = {
        "name": "Carlos Mendez",
        "role": "Excavator Operator",
        "department": "Pit Surface Haulage",
        "supervisor_email": "carlos_supervisor@halocas.safety",
        "is_authorized": False,
    }

    create_res = await integration_api_client.post("/api/v1/workers", json=create_payload)
    assert create_res.status_code == 201
    created_worker = create_res.json()
    worker_id = created_worker["id"]

    assert created_worker["name"] == "Carlos Mendez"
    assert created_worker["role"] == "Excavator Operator"
    assert created_worker["department"] == "Pit Surface Haulage"
    assert created_worker["is_authorized"] is False
    assert created_worker["has_face_embedding"] is False

    # 2. GET WORKER BY ID
    get_res = await integration_api_client.get(f"/api/v1/workers/{worker_id}")
    assert get_res.status_code == 200
    worker_detail = get_res.json()

    assert worker_detail["id"] == worker_id
    assert worker_detail["name"] == "Carlos Mendez"
    assert worker_detail["total_incidents"] == 0
    assert len(worker_detail["recent_incidents"]) == 0

    # 3. UPDATE WORKER
    update_payload = {
        "name": "Carlos Mendez",
        "role": "Master Excavator Specialist",
        "department": "Heavy Fleet Operations",
        "is_authorized": True,
    }

    update_res = await integration_api_client.put(f"/api/v1/workers/{worker_id}", json=update_payload)
    assert update_res.status_code == 200
    updated_worker = update_res.json()

    assert updated_worker["role"] == "Master Excavator Specialist"
    assert updated_worker["department"] == "Heavy Fleet Operations"
    assert updated_worker["is_authorized"] is True

    # 4. LIST WORKERS WITH PAGINATION
    list_res = await integration_api_client.get("/api/v1/workers?offset=0&limit=10")
    assert list_res.status_code == 200
    workers_list = list_res.json()

    assert "X-Total-Count" in list_res.headers
    total_count = int(list_res.headers["X-Total-Count"])
    assert total_count >= 1

    matched = next((w for w in workers_list if w["id"] == worker_id), None)
    assert matched is not None
    assert matched["name"] == "Carlos Mendez"
    assert matched["is_authorized"] is True


@pytest.mark.asyncio
async def test_worker_face_enrollment_api_endpoint(
    integration_api_client: AsyncClient,
    integration_db_session: AsyncSession,
    sample_synthetic_frame: np.ndarray,
) -> None:
    """Verify multipart face photo upload, embedding generation, and biometric enrollment."""
    # 1. Create worker to be enrolled
    worker = Worker(
        name="Elena Vasquez",
        role="Blasting Technician",
        department="Drill & Blast",
        supervisor_email="blasting_supervisor@halocas.safety",
        is_authorized=False,
    )
    integration_db_session.add(worker)
    await integration_db_session.commit()
    await integration_db_session.refresh(worker)

    # 2. Encode synthetic frame as JPEG byte stream
    _, buffer = cv2.imencode(".jpg", sample_synthetic_frame)
    image_bytes = buffer.tobytes()

    # 3. Mock FaceVerifier.extract_embedding and StorageService.upload_clip
    synthetic_embedding = np.full(512, 0.035, dtype=np.float32)

    mock_verifier_inst = MagicMock()
    mock_verifier_inst.extract_embedding.return_value = synthetic_embedding

    mock_storage_inst = MagicMock()
    mock_storage_inst.upload_clip.return_value = (
        f"https://storage.halocas.safety/faces/worker_{worker.id}.jpg"
    )

    app.dependency_overrides[get_face_verifier] = lambda: mock_verifier_inst
    app.dependency_overrides[get_storage_service] = lambda: mock_storage_inst

    try:
        files = {"photo": ("face_photo.jpg", io.BytesIO(image_bytes), "image/jpeg")}
        enroll_res = await integration_api_client.post(
            f"/api/v1/workers/{worker.id}/enroll-face",
            files=files,
        )

        assert enroll_res.status_code == 200
        enroll_data = enroll_res.json()
        assert enroll_data["worker_id"] == worker.id
        assert enroll_data["embedding_dimensions"] == 512
        assert enroll_data["face_photo_url"] == (
            f"https://storage.halocas.safety/faces/worker_{worker.id}.jpg"
        )
    finally:
        app.dependency_overrides.pop(get_face_verifier, None)
        app.dependency_overrides.pop(get_storage_service, None)

    # 4. Verify worker record has face embedding set
    detail_res = await integration_api_client.get(f"/api/v1/workers/{worker.id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["has_face_embedding"] is True


@pytest.mark.asyncio
async def test_incidents_filtering_and_statistics_endpoints(
    integration_api_client: AsyncClient,
    integration_db_session: AsyncSession,
) -> None:
    """Verify safety incidents filtering, pagination headers, and aggregate statistics."""
    # 1. Seed machines and test incidents
    truck = Machine(name="CAT 793F #505", type="Haul Truck", zone="Pit Alpha", status="active")
    loader = Machine(name="CAT 994K #606", type="Loader", zone="Crusher Plant", status="active")
    integration_db_session.add_all([truck, loader])
    await integration_db_session.commit()
    await integration_db_session.refresh(truck)
    await integration_db_session.refresh(loader)

    incident_crit = Incident(
        timestamp=datetime.now(UTC),
        machine_id=truck.id,
        worker_name="Worker #11",
        distance_meters=1.8,
        severity=IncidentSeverity.CRITICAL,
        closing_velocity=2.4,
        supervisor_notified=True,
        supervisor_email="safety_head@halocas.safety",
        zone="Pit Alpha",
        clip_url="https://storage.halocas.safety/clips/inc_crit.mp4",
    )
    incident_warn = Incident(
        timestamp=datetime.now(UTC),
        machine_id=loader.id,
        worker_name="Worker #12",
        distance_meters=5.5,
        severity=IncidentSeverity.WARNING,
        closing_velocity=0.8,
        supervisor_notified=False,
        zone="Crusher Plant",
        clip_url="https://storage.halocas.safety/clips/inc_warn.mp4",
    )
    integration_db_session.add_all([incident_crit, incident_warn])
    await integration_db_session.commit()

    # 2. List all incidents
    all_res = await integration_api_client.get("/api/v1/incidents")
    assert all_res.status_code == 200
    all_data = all_res.json()
    assert len(all_data) >= 2
    assert int(all_res.headers["X-Total-Count"]) >= 2

    # 3. Filter by severity=CRITICAL
    crit_res = await integration_api_client.get("/api/v1/incidents?severity=CRITICAL")
    assert crit_res.status_code == 200
    crit_data = crit_res.json()
    assert all(inc["severity"] == "CRITICAL" for inc in crit_data)

    # 4. Filter by machine_id
    machine_res = await integration_api_client.get(f"/api/v1/incidents?machine_id={truck.id}")
    assert machine_res.status_code == 200
    machine_data = machine_res.json()
    assert all(inc["machine_id"] == truck.id for inc in machine_data)

    # 5. Fetch incident statistics
    stats_res = await integration_api_client.get("/api/v1/incidents/stats")
    assert stats_res.status_code == 200
    stats_data = stats_res.json()
    assert "total_incidents" in stats_data
    assert "critical_count" in stats_data
    assert "warning_count" in stats_data
    assert stats_data["total_incidents"] >= 2
    assert stats_data["critical_count"] >= 1


@pytest.mark.asyncio
async def test_crud_error_states_and_not_found(
    integration_api_client: AsyncClient,
) -> None:
    """Verify edge cases: 404 for nonexistent entities and 422 for malformed requests."""
    # 1. Nonexistent worker
    res = await integration_api_client.get("/api/v1/workers/999999")
    assert res.status_code == 404
    assert "not found" in res.json()["message"]

    # 2. Nonexistent incident
    res_inc = await integration_api_client.get("/api/v1/incidents/999999")
    assert res_inc.status_code == 404
    assert "not found" in res_inc.json()["message"]

    # 3. Malformed worker payload (missing name)
    bad_res = await integration_api_client.post("/api/v1/workers", json={"role": "Mechanic"})
    assert bad_res.status_code == 422
