"""End-to-end integration tests: known embedding -> face match -> correct supervisor dispatch."""

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
from app.core.state_machine import SafetyStateMachine
from app.models import Incident, Machine, Worker
from app.services.notification import NotificationService
from app.services.storage import StorageService


@pytest.mark.asyncio
async def test_known_face_embedding_matches_and_notifies_designated_supervisor(
    integration_db_session: AsyncSession,
    mock_storage_service: StorageService,
    mock_notification_service: NotificationService,
    sample_synthetic_frame: np.ndarray,
    recorded_notifications: list[dict[str, Any]],
) -> None:
    """Verify facial embedding match resolves specific worker identity and designated supervisor email."""
    # 1. Create two distinct workers with unique supervisor assignments
    worker_haulage = Worker(
        name="Amit Sharma",
        role="Loader Operator",
        department="Haulage Fleet",
        supervisor_email="haulage_supervisor@halocas.safety",
        face_embedding=[0.25] * 512,
        is_authorized=False,
    )
    worker_drilling = Worker(
        name="Rajesh Kumar",
        role="Drill Operator",
        department="Drill & Blast",
        supervisor_email="drill_supervisor@halocas.safety",
        face_embedding=[0.75] * 512,
        is_authorized=False,
    )
    test_machine = Machine(
        name="Komatsu PC2000 Excavator #202",
        type="Excavator",
        zone="Pit Beta",
        status="active",
    )
    integration_db_session.add_all([worker_haulage, worker_drilling, test_machine])
    await integration_db_session.commit()
    await integration_db_session.refresh(worker_haulage)
    await integration_db_session.refresh(worker_drilling)
    await integration_db_session.refresh(test_machine)

    # 2. Configure detector with dangerous proximity between worker and machine
    mock_detector = MagicMock(spec=Detector)
    mock_detector.detect_and_track.return_value = [
        DetectionResult(
            id=404,
            class_name="person",
            bbox=[150.0, 200.0, 200.0, 320.0],
            confidence=0.96,
        ),
        DetectionResult(
            id=test_machine.id,
            class_name="truck",
            bbox=[170.0, 180.0, 290.0, 340.0],
            confidence=0.94,
        ),
    ]

    # 3. Simulate real biometric matcher returning Amit Sharma
    mock_face_verifier = MagicMock(spec=FaceVerifier)

    def _mock_verify(
        frame: np.ndarray,
        bbox: list[float],
        database_workers: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        _ = (frame, bbox, kwargs)
        for candidate in database_workers:
            if candidate["name"] == "Amit Sharma":
                return {
                    "id": candidate["id"],
                    "name": candidate["name"],
                    "confidence": 0.912,
                    "supervisor_email": candidate["supervisor_email"],
                    "is_authorized": candidate["is_authorized"],
                }
        return None

    mock_face_verifier.verify = MagicMock(side_effect=_mock_verify)

    # 4. Configure pipeline
    state_machine = SafetyStateMachine(
        critical_distance=3.0,
        warning_distance=10.0,
        pixels_per_meter=20.0,
        debounce_frames=1,
    )
    buffer_manager = BufferManager(default_maxlen=10)

    def _fake_export(*args: Any, **kwargs: Any) -> bool:
        out_path = str(kwargs.get("output_path") or (args[1] if len(args) > 1 else ""))
        if out_path:
            with open(out_path, "wb") as f:
                f.write(b"MOCK_CLIP_DATA")
        return True

    pipeline = PipelineOrchestrator(
        detector=mock_detector,
        state_machine=state_machine,
        face_verifier=mock_face_verifier,
        buffer_manager=buffer_manager,
        storage=mock_storage_service,
        notification=mock_notification_service,
        db=integration_db_session,
    )

    # 5. Execute frame processing
    with patch.object(buffer_manager, "export_incident_clip", side_effect=_fake_export):
        events = await pipeline.process_frame(
            frame=sample_synthetic_frame,
            camera_id="cam-beta",
            timestamp=100.0,
        )

    # 6. Verify identification and targeted notification
    assert len(events) >= 1
    assert len(recorded_notifications) == 1
    sent_alert = recorded_notifications[0]

    # Recipient MUST be haulage supervisor, NOT drilling supervisor
    assert sent_alert["recipient_email"] == "haulage_supervisor@halocas.safety"
    assert sent_alert["worker_name"] == "Amit Sharma"

    # 7. Check database record linkage
    stmt = select(Incident).where(Incident.worker_id == worker_haulage.id)
    res = await integration_db_session.execute(stmt)
    incident = res.scalars().first()

    assert incident is not None
    assert incident.worker_id == worker_haulage.id
    assert incident.worker_name == "Amit Sharma"
    assert incident.supervisor_email == "haulage_supervisor@halocas.safety"
    assert incident.face_match_confidence == pytest.approx(0.912, rel=1e-3)


@pytest.mark.asyncio
async def test_unidentified_worker_falls_back_to_generic_alert(
    integration_db_session: AsyncSession,
    mock_storage_service: StorageService,
    mock_notification_service: NotificationService,
    sample_synthetic_frame: np.ndarray,
    recorded_notifications: list[dict[str, Any]],
) -> None:
    """Verify unidentified worker generates incident with generic tracker name and fallback supervisor routing."""
    test_machine = Machine(
        name="CAT Loader #303",
        type="Wheel Loader",
        zone="Crusher Plant",
        status="active",
    )
    integration_db_session.add(test_machine)
    await integration_db_session.commit()
    await integration_db_session.refresh(test_machine)

    mock_detector = MagicMock(spec=Detector)
    mock_detector.detect_and_track.return_value = [
        DetectionResult(
            id=888,
            class_name="person",
            bbox=[100.0, 100.0, 150.0, 200.0],
            confidence=0.88,
        ),
        DetectionResult(
            id=test_machine.id,
            class_name="truck",
            bbox=[100.0, 120.0, 180.0, 220.0],
            confidence=0.91,
        ),
    ]

    # Face verifier fails to match (e.g. obscured face / hardhat / dust)
    mock_face_verifier = MagicMock(spec=FaceVerifier)
    mock_face_verifier.verify.return_value = None

    state_machine = SafetyStateMachine(
        critical_distance=3.0,
        warning_distance=10.0,
        pixels_per_meter=20.0,
        debounce_frames=1,
    )
    buffer_manager = BufferManager(default_maxlen=10)

    def _fake_export(*args: Any, **kwargs: Any) -> bool:
        out_path = str(kwargs.get("output_path") or (args[1] if len(args) > 1 else ""))
        if out_path:
            with open(out_path, "wb") as f:
                f.write(b"MOCK_CLIP_DATA")
        return True

    pipeline = PipelineOrchestrator(
        detector=mock_detector,
        state_machine=state_machine,
        face_verifier=mock_face_verifier,
        buffer_manager=buffer_manager,
        storage=mock_storage_service,
        notification=mock_notification_service,
        db=integration_db_session,
    )

    with patch.object(buffer_manager, "export_incident_clip", side_effect=_fake_export):
        events = await pipeline.process_frame(
            frame=sample_synthetic_frame,
            camera_id="cam-crusher",
            timestamp=200.0,
        )

    assert len(events) >= 1
    assert len(recorded_notifications) == 0

    # Verify DB incident record
    stmt = select(Incident).where(Incident.worker_name == "Worker #888")
    res = await integration_db_session.execute(stmt)
    incident = res.scalars().first()

    assert incident is not None
    assert incident.worker_id is None
    assert incident.face_match_confidence is None
