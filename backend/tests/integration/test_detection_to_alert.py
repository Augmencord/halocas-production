"""End-to-end integration tests: synthetic frame -> state machine -> notification -> DB."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.buffer import BufferManager
from app.core.detector import DetectionResult, Detector
from app.core.face_verifier import FaceVerifier
from app.core.pipeline import PipelineOrchestrator
from app.core.state_machine import SafetyEvent, SafetyStateMachine, Severity
from app.models import AlertLog, DeliveryStatus, Incident, IncidentSeverity
from app.services.notification import NotificationService
from app.services.storage import StorageService


@pytest.mark.asyncio
async def test_end_to_end_detection_to_alert_pipeline(
    integration_db_session: AsyncSession,
    seeded_integration_db: dict[str, Any],
    mock_storage_service: StorageService,
    mock_notification_service: NotificationService,
    sample_synthetic_frame: np.ndarray,
    recorded_notifications: list[dict[str, Any]],
) -> None:
    """Verify flow from synthetic video frame to state machine, alert dispatch, and DB persistence."""
    target_machine = seeded_integration_db["machine"]
    target_worker = seeded_integration_db["worker"]

    # 1. Instantiate state machine with zero debounce for immediate deterministic trigger
    state_machine = SafetyStateMachine(
        critical_distance=3.0,
        warning_distance=10.0,
        pixels_per_meter=20.0,
        cooldown_seconds=60,
        debounce_frames=1,
    )

    # 2. Configure mock detector to return breach proximity bounding boxes
    mock_detector = MagicMock(spec=Detector)

    # Machine center ground base: ~ (350, 400)
    machine_box = [300.0, 200.0, 400.0, 400.0]
    # Worker center ground base: ~ (360, 400) -> distance < 1 meter (< 20 pixels)
    worker_box = [340.0, 280.0, 380.0, 400.0]

    mock_detector.detect_and_track.return_value = [
        DetectionResult(
            id=101,
            class_name="person",
            bbox=worker_box,
            confidence=0.95,
        ),
        DetectionResult(
            id=target_machine.id,
            class_name="truck",
            bbox=machine_box,
            confidence=0.92,
        ),
    ]

    # 3. Configure mock face verifier to match the seeded worker
    mock_face_verifier = MagicMock(spec=FaceVerifier)
    mock_face_verifier.verify.return_value = {
        "id": target_worker.id,
        "name": target_worker.name,
        "confidence": 0.94,
        "supervisor_email": target_worker.supervisor_email,
        "is_authorized": False,
    }

    # 4. Instantiate cyclic buffer manager and prime with synthetic frames
    buffer_manager = BufferManager(default_maxlen=30)
    for _ in range(5):
        buffer_manager.append(camera_id="cam-north", frame=sample_synthetic_frame)

    # Emulate video export writing a temporary file
    def _fake_export(*args: Any, **kwargs: Any) -> bool:
        out_path = str(kwargs.get("output_path") or (args[1] if len(args) > 1 else ""))
        if out_path:
            with open(out_path, "wb") as f:
                f.write(b"MOCK_EXPORTED_MP4_CONTENT")
        return True

    # 5. Assemble full Pipeline Orchestrator with live transactional SQLite session
    pipeline = PipelineOrchestrator(
        detector=mock_detector,
        state_machine=state_machine,
        face_verifier=mock_face_verifier,
        buffer_manager=buffer_manager,
        storage=mock_storage_service,
        notification=mock_notification_service,
        db=integration_db_session,
    )

    # 6. Process frame through pipeline with exported clip mock
    with patch.object(buffer_manager, "export_incident_clip", side_effect=_fake_export):
        events: list[SafetyEvent] = await pipeline.process_frame(
            frame=sample_synthetic_frame,
            camera_id="cam-north",
            timestamp=100.0,
        )

    # 7. Assert pipeline execution outcome
    assert len(events) >= 1
    crit_event = next((e for e in events if e.severity == Severity.CRITICAL), None)
    assert crit_event is not None
    assert crit_event.worker_id == 101
    assert crit_event.distance_meters < 3.0

    # 8. Verify Database Record Creation (incidents table)
    stmt = select(Incident).where(Incident.worker_id == target_worker.id)
    query_res = await integration_db_session.execute(stmt)
    persisted_incident = query_res.scalars().first()

    assert persisted_incident is not None
    assert persisted_incident.severity == IncidentSeverity.CRITICAL
    assert persisted_incident.distance_meters < 3.0
    assert persisted_incident.supervisor_notified is True
    assert persisted_incident.supervisor_email == target_worker.supervisor_email
    assert "https://storage.halocas.safety/" in (persisted_incident.clip_url or "")

    # 9. Verify Notification Dispatch via Mock Service
    assert len(recorded_notifications) == 1
    dispatched_alert = recorded_notifications[0]
    assert dispatched_alert["recipient_email"] == target_worker.supervisor_email
    assert dispatched_alert["incident_id"] == persisted_incident.id
    assert dispatched_alert["worker_name"] == target_worker.name
    assert dispatched_alert["clip_url"] == persisted_incident.clip_url

    # 10. Verify Alert Log Record Creation (alert_logs table)
    log_stmt = select(AlertLog).where(AlertLog.incident_id == persisted_incident.id)
    log_res = await integration_db_session.execute(log_stmt)
    persisted_log = log_res.scalars().first()

    assert persisted_log is not None
    assert persisted_log.delivery_status == DeliveryStatus.SENT
    assert persisted_log.recipient_email == target_worker.supervisor_email
    assert persisted_log.retry_count == 0


@pytest.mark.asyncio
async def test_safe_frame_produces_no_incidents_or_alerts(
    integration_db_session: AsyncSession,
    mock_storage_service: StorageService,
    mock_notification_service: NotificationService,
    sample_synthetic_frame: np.ndarray,
    recorded_notifications: list[dict[str, Any]],
) -> None:
    """Verify safe spatial separation produces zero database incidents and zero alert dispatches."""
    state_machine = SafetyStateMachine(
        critical_distance=3.0,
        warning_distance=10.0,
        pixels_per_meter=20.0,
        cooldown_seconds=60,
        debounce_frames=1,
    )

    mock_detector = MagicMock(spec=Detector)
    # Machine at far right, worker at far left (> 25 meters away)
    mock_detector.detect_and_track.return_value = [
        DetectionResult(id=201, class_name="person", bbox=[10.0, 10.0, 50.0, 100.0], confidence=0.9),
        DetectionResult(id=301, class_name="truck", bbox=[550.0, 380.0, 630.0, 470.0], confidence=0.9),
    ]
    mock_face_verifier = MagicMock(spec=FaceVerifier)
    buffer_manager = BufferManager(default_maxlen=10)

    pipeline = PipelineOrchestrator(
        detector=mock_detector,
        state_machine=state_machine,
        face_verifier=mock_face_verifier,
        buffer_manager=buffer_manager,
        storage=mock_storage_service,
        notification=mock_notification_service,
        db=integration_db_session,
    )

    events = await pipeline.process_frame(
        frame=sample_synthetic_frame,
        camera_id="cam-safe",
        timestamp=200.0,
    )

    assert all(e.severity == Severity.SAFE for e in events)
    assert len(recorded_notifications) == 0

    # Ensure no incidents written to database
    stmt = select(Incident).where(Incident.zone == "Camera CAM-SAFE")
    query_res = await integration_db_session.execute(stmt)
    assert query_res.scalars().first() is None
