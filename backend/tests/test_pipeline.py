"""Integration tests for the central PipelineOrchestrator."""

from __future__ import annotations

import os
import tempfile
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import cv2
import numpy as np
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.buffer import BufferManager
from app.core.detector import DetectionResult, Detector
from app.core.face_verifier import FaceVerifier
from app.core.pipeline import PipelineInputError, PipelineOrchestrator
from app.core.state_machine import SafetyEvent, SafetyStateMachine, Severity
from app.models.base import Base
from app.models.incident import Incident, IncidentSeverity
from app.models.worker import Worker
from app.services.notification import NotificationService
from app.services.storage import StorageService, StorageUploadError


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
def mock_detector() -> MagicMock:
    """Mock Detector producing deterministic DetectionResult objects."""
    det = MagicMock(spec=Detector)
    det.detect_and_track.return_value = [
        DetectionResult(
            id=10,
            class_name="person",
            bbox=[100.0, 100.0, 150.0, 200.0],
            confidence=0.91,
        ),
        DetectionResult(
            id=20,
            class_name="truck",
            bbox=[300.0, 300.0, 500.0, 500.0],
            confidence=0.95,
        ),
    ]
    return det


@pytest.fixture
def mock_state_machine() -> MagicMock:
    """Mock SafetyStateMachine returning configurable SafetyEvent instances."""
    sm = MagicMock(spec=SafetyStateMachine)
    sm.update.return_value = [
        SafetyEvent(
            timestamp=100.0,
            machine_id=20,
            worker_id=10,
            distance_meters=12.5,
            severity=Severity.SAFE,
            closing_velocity=0.0,
            machine_speed=0.0,
            alert_suppressed=False,
        )
    ]
    return sm


@pytest.fixture
def mock_face_verifier() -> MagicMock:
    """Mock FaceVerifier."""
    fv = MagicMock(spec=FaceVerifier)
    fv.verify.return_value = {
        "id": 1,
        "name": "Elena Rostova",
        "confidence": 0.88,
        "supervisor_email": "supervisor@halocas.safety",
        "is_authorized": True,
    }
    return fv


@pytest.fixture
def mock_buffer_manager() -> MagicMock:
    """Mock BufferManager with clip export emulation."""
    bm = MagicMock(spec=BufferManager)
    bm.append.return_value = True

    def fake_export(*args: object, **kwargs: object) -> bool:
        # Create a small valid file so os.path.getsize(output_path) > 0
        output_path = str(kwargs.get("output_path") or (args[1] if len(args) > 1 else ""))
        if output_path:
            with open(output_path, "wb") as f:
                f.write(b"MOCK_MP4_DATA_HEADER_1234567890")
        return True

    bm.export_incident_clip.side_effect = fake_export
    return bm


@pytest.fixture
def mock_storage() -> MagicMock:
    """Mock StorageService."""
    st = MagicMock(spec=StorageService)
    st.build_object_key.return_value = "incidents/2026/09/04/1_front.mp4"
    st.upload_clip.return_value = "https://r2.halocas.safety/incidents/2026/09/04/1_front.mp4"
    return st


@pytest.fixture
def mock_notification() -> MagicMock:
    """Mock NotificationService."""
    notif = MagicMock(spec=NotificationService)
    notif.send_proximity_alert = AsyncMock(return_value=True)
    return notif


@pytest.fixture
def sample_frame() -> np.ndarray:
    """640x480 synthetic RGB image frame."""
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.mark.asyncio
async def test_pipeline_init(
    mock_detector: MagicMock,
    mock_state_machine: MagicMock,
    mock_face_verifier: MagicMock,
    mock_buffer_manager: MagicMock,
    mock_storage: MagicMock,
    mock_notification: MagicMock,
    test_session: AsyncSession,
) -> None:
    """Verify initialization and internal counter resets."""
    pipeline = PipelineOrchestrator(
        detector=mock_detector,
        state_machine=mock_state_machine,
        face_verifier=mock_face_verifier,
        buffer_manager=mock_buffer_manager,
        storage=mock_storage,
        notification=mock_notification,
        db=test_session,
    )
    assert pipeline.total_frames_processed == 0
    assert pipeline.total_incidents_logged == 0
    assert pipeline.total_notifications_sent == 0


@pytest.mark.asyncio
async def test_process_frame_safe_state(
    mock_detector: MagicMock,
    mock_state_machine: MagicMock,
    mock_face_verifier: MagicMock,
    mock_buffer_manager: MagicMock,
    mock_storage: MagicMock,
    mock_notification: MagicMock,
    test_session: AsyncSession,
    sample_frame: np.ndarray,
) -> None:
    """Verify non-critical frame stores to buffer and emits events without incident logging."""
    pipeline = PipelineOrchestrator(
        detector=mock_detector,
        state_machine=mock_state_machine,
        face_verifier=mock_face_verifier,
        buffer_manager=mock_buffer_manager,
        storage=mock_storage,
        notification=mock_notification,
        db=test_session,
    )

    events = await pipeline.process_frame(
        frame=sample_frame,
        camera_id="cam_front",
        timestamp=100.0,
    )

    assert len(events) == 1
    assert events[0].severity == Severity.SAFE
    assert pipeline.total_frames_processed == 1
    assert pipeline.total_incidents_logged == 0
    mock_buffer_manager.append.assert_called_once()
    mock_storage.upload_clip.assert_not_called()
    mock_notification.send_proximity_alert.assert_not_called()


@pytest.mark.asyncio
async def test_process_frame_critical_event_flow(
    mock_detector: MagicMock,
    mock_state_machine: MagicMock,
    mock_face_verifier: MagicMock,
    mock_buffer_manager: MagicMock,
    mock_storage: MagicMock,
    mock_notification: MagicMock,
    test_session: AsyncSession,
    sample_frame: np.ndarray,
) -> None:
    """Verify full end-to-end orchestration for a critical collision risk."""
    # 1. Seed database with enrolled worker
    worker = Worker(
        name="Elena Rostova",
        role="Shift Supervisor",
        department="Operations",
        supervisor_email="supervisor@halocas.safety",
        face_embedding=[0.1] * 512,
        is_authorized=False,
    )
    test_session.add(worker)
    await test_session.commit()
    await test_session.refresh(worker)

    # 2. Configure state machine for critical severity
    mock_state_machine.update.return_value = [
        SafetyEvent(
            timestamp=datetime.now(UTC).timestamp(),
            machine_id=20,
            worker_id=10,
            distance_meters=1.85,
            severity=Severity.CRITICAL,
            closing_velocity=1.2,
            machine_speed=2.5,
            alert_suppressed=False,
        )
    ]

    pipeline = PipelineOrchestrator(
        detector=mock_detector,
        state_machine=mock_state_machine,
        face_verifier=mock_face_verifier,
        buffer_manager=mock_buffer_manager,
        storage=mock_storage,
        notification=mock_notification,
        db=test_session,
    )

    events = await pipeline.process_frame(
        frame=sample_frame,
        camera_id="cam_front",
    )

    assert len(events) == 1
    assert events[0].severity == Severity.CRITICAL
    assert pipeline.total_incidents_logged == 1
    assert pipeline.total_notifications_sent == 1

    # Verify incident stored in database
    stmt = select(Incident).order_by(Incident.id.desc())
    res = await test_session.execute(stmt)
    logged_incident = res.scalars().first()

    assert logged_incident is not None
    assert logged_incident.severity == IncidentSeverity.CRITICAL
    assert logged_incident.worker_id == worker.id
    assert logged_incident.worker_name == "Elena Rostova"
    assert logged_incident.distance_meters == 1.85
    assert logged_incident.clip_url == "https://r2.halocas.safety/incidents/2026/09/04/1_front.mp4"
    assert logged_incident.supervisor_notified is True
    assert logged_incident.supervisor_email == "supervisor@halocas.safety"


@pytest.mark.asyncio
async def test_process_frame_unidentified_worker(
    mock_detector: MagicMock,
    mock_state_machine: MagicMock,
    mock_face_verifier: MagicMock,
    mock_buffer_manager: MagicMock,
    mock_storage: MagicMock,
    mock_notification: MagicMock,
    test_session: AsyncSession,
    sample_frame: np.ndarray,
) -> None:
    """Verify fallback handling when face verifier cannot identify personnel."""
    # No face match found
    mock_face_verifier.verify.return_value = None

    mock_state_machine.update.return_value = [
        SafetyEvent(
            timestamp=datetime.now(UTC).timestamp(),
            machine_id=20,
            worker_id=99,
            distance_meters=2.1,
            severity=Severity.CRITICAL,
            closing_velocity=0.8,
            machine_speed=1.5,
            alert_suppressed=False,
        )
    ]

    pipeline = PipelineOrchestrator(
        detector=mock_detector,
        state_machine=mock_state_machine,
        face_verifier=mock_face_verifier,
        buffer_manager=mock_buffer_manager,
        storage=mock_storage,
        notification=mock_notification,
        db=test_session,
    )

    events = await pipeline.process_frame(
        frame=sample_frame,
        camera_id="cam_rear",
    )

    assert len(events) == 1
    assert pipeline.total_incidents_logged == 1
    # Without supervisor email, notification is not dispatched
    assert pipeline.total_notifications_sent == 0
    mock_notification.send_proximity_alert.assert_not_called()

    stmt = select(Incident).order_by(Incident.id.desc())
    res = await test_session.execute(stmt)
    logged_incident = res.scalars().first()
    assert logged_incident is not None
    assert logged_incident.worker_id is None
    assert "99" in str(logged_incident.worker_name)


@pytest.mark.asyncio
async def test_process_frame_storage_failure_resilience(
    mock_detector: MagicMock,
    mock_state_machine: MagicMock,
    mock_face_verifier: MagicMock,
    mock_buffer_manager: MagicMock,
    mock_storage: MagicMock,
    mock_notification: MagicMock,
    test_session: AsyncSession,
    sample_frame: np.ndarray,
) -> None:
    """Verify incident logging proceeds even if cloud storage upload raises error."""
    mock_storage.upload_clip.side_effect = StorageUploadError("R2 network connection timeout")

    mock_state_machine.update.return_value = [
        SafetyEvent(
            timestamp=datetime.now(UTC).timestamp(),
            machine_id=5,
            worker_id=3,
            distance_meters=1.5,
            severity=Severity.CRITICAL,
            closing_velocity=0.5,
            alert_suppressed=False,
        )
    ]

    pipeline = PipelineOrchestrator(
        detector=mock_detector,
        state_machine=mock_state_machine,
        face_verifier=mock_face_verifier,
        buffer_manager=mock_buffer_manager,
        storage=mock_storage,
        notification=mock_notification,
        db=test_session,
    )

    # Should not raise exception
    events = await pipeline.process_frame(frame=sample_frame, camera_id="cam_east")
    assert len(events) == 1
    assert pipeline.total_incidents_logged == 1

    stmt = select(Incident).order_by(Incident.id.desc())
    res = await test_session.execute(stmt)
    logged = res.scalars().first()
    assert logged is not None
    assert logged.clip_url is None


@pytest.mark.asyncio
async def test_process_frame_notification_failure_resilience(
    mock_detector: MagicMock,
    mock_state_machine: MagicMock,
    mock_face_verifier: MagicMock,
    mock_buffer_manager: MagicMock,
    mock_storage: MagicMock,
    mock_notification: MagicMock,
    test_session: AsyncSession,
    sample_frame: np.ndarray,
) -> None:
    """Verify failure during notification dispatch is handled gracefully."""
    mock_notification.send_proximity_alert.side_effect = RuntimeError("SMTP dispatch failed")

    mock_state_machine.update.return_value = [
        SafetyEvent(
            timestamp=datetime.now(UTC).timestamp(),
            machine_id=7,
            worker_id=8,
            distance_meters=1.2,
            severity=Severity.CRITICAL,
            alert_suppressed=False,
        )
    ]

    pipeline = PipelineOrchestrator(
        detector=mock_detector,
        state_machine=mock_state_machine,
        face_verifier=mock_face_verifier,
        buffer_manager=mock_buffer_manager,
        storage=mock_storage,
        notification=mock_notification,
        db=test_session,
    )

    events = await pipeline.process_frame(frame=sample_frame, camera_id="cam_west")
    assert len(events) == 1
    assert pipeline.total_incidents_logged == 1
    assert pipeline.total_notifications_sent == 0


@pytest.mark.asyncio
async def test_process_frame_invalid_inputs(
    mock_detector: MagicMock,
    mock_state_machine: MagicMock,
    mock_face_verifier: MagicMock,
    mock_buffer_manager: MagicMock,
    mock_storage: MagicMock,
    mock_notification: MagicMock,
    test_session: AsyncSession,
) -> None:
    """Verify validation raises PipelineInputError on degenerate inputs."""
    pipeline = PipelineOrchestrator(
        detector=mock_detector,
        state_machine=mock_state_machine,
        face_verifier=mock_face_verifier,
        buffer_manager=mock_buffer_manager,
        storage=mock_storage,
        notification=mock_notification,
        db=test_session,
    )

    with pytest.raises(PipelineInputError, match="cannot be None"):
        await pipeline.process_frame(frame=None)  # type: ignore[arg-type]

    with pytest.raises(PipelineInputError, match="Expected numpy.ndarray"):
        await pipeline.process_frame(frame="invalid_string")  # type: ignore[arg-type]

    with pytest.raises(PipelineInputError, match="empty or invalid shape"):
        await pipeline.process_frame(frame=np.zeros((0,)))


@pytest.mark.asyncio
async def test_process_video_success(
    mock_detector: MagicMock,
    mock_state_machine: MagicMock,
    mock_face_verifier: MagicMock,
    mock_buffer_manager: MagicMock,
    mock_storage: MagicMock,
    mock_notification: MagicMock,
    test_session: AsyncSession,
) -> None:
    """Verify video file processing loop across frames."""
    pipeline = PipelineOrchestrator(
        detector=mock_detector,
        state_machine=mock_state_machine,
        face_verifier=mock_face_verifier,
        buffer_manager=mock_buffer_manager,
        storage=mock_storage,
        notification=mock_notification,
        db=test_session,
    )

    # Generate a temporary synthetic 5-frame video
    temp_video_path = os.path.join(tempfile.gettempdir(), "test_pipeline_run.mp4")
    fourcc = cv2.VideoWriter.fourcc(*"mp4v")
    out = cv2.VideoWriter(temp_video_path, fourcc, 10.0, (320, 240))
    for _ in range(5):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        out.write(frame)
    out.release()

    try:
        summary = await pipeline.process_video(
            video_path=temp_video_path,
            camera_id="cam_main",
            max_frames=5,
        )
        assert summary["frames_processed"] == 5
        assert summary["camera_id"] == "cam_main"
        assert summary["processing_fps"] >= 0.0
        assert "events_generated" in summary
    finally:
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)


@pytest.mark.asyncio
async def test_process_video_file_not_found(
    mock_detector: MagicMock,
    mock_state_machine: MagicMock,
    mock_face_verifier: MagicMock,
    mock_buffer_manager: MagicMock,
    mock_storage: MagicMock,
    mock_notification: MagicMock,
    test_session: AsyncSession,
) -> None:
    """Verify FileNotFoundError when input video does not exist."""
    pipeline = PipelineOrchestrator(
        detector=mock_detector,
        state_machine=mock_state_machine,
        face_verifier=mock_face_verifier,
        buffer_manager=mock_buffer_manager,
        storage=mock_storage,
        notification=mock_notification,
        db=test_session,
    )

    with pytest.raises(FileNotFoundError):
        await pipeline.process_video(video_path="nonexistent_video_path_xyz.mp4")


@pytest.mark.asyncio
async def test_process_video_batch(
    mock_detector: MagicMock,
    mock_state_machine: MagicMock,
    mock_face_verifier: MagicMock,
    mock_buffer_manager: MagicMock,
    mock_storage: MagicMock,
    mock_notification: MagicMock,
    test_session: AsyncSession,
) -> None:
    """Verify batch video processing collects per-video summaries and isolates failures."""
    pipeline = PipelineOrchestrator(
        detector=mock_detector,
        state_machine=mock_state_machine,
        face_verifier=mock_face_verifier,
        buffer_manager=mock_buffer_manager,
        storage=mock_storage,
        notification=mock_notification,
        db=test_session,
    )

    # 1 valid video, 1 missing video
    temp_video_path = os.path.join(tempfile.gettempdir(), "test_batch_1.mp4")
    fourcc = cv2.VideoWriter.fourcc(*"mp4v")
    out = cv2.VideoWriter(temp_video_path, fourcc, 10.0, (160, 120))
    for _ in range(3):
        out.write(np.zeros((120, 160, 3), dtype=np.uint8))
    out.release()

    video_batch = [temp_video_path, "missing_video.mp4"]

    try:
        results = await pipeline.process_video_batch(video_paths=video_batch, camera_id="cam_batch")
        assert len(results) == 2
        assert results[0]["frames_processed"] == 3
        assert "error" in results[1]
    finally:
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
