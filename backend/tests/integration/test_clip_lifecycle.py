"""End-to-end integration tests: ring buffer -> video export -> Cloudflare R2 upload -> incident record."""

from __future__ import annotations

import os
import tempfile

import cv2
import numpy as np
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.buffer import BufferManager
from app.models import Incident, IncidentSeverity, Machine
from app.services.storage import StorageService


@pytest.mark.asyncio
async def test_complete_clip_lifecycle_buffer_export_upload_record(
    integration_db_session: AsyncSession,
    sample_synthetic_frame: np.ndarray,
    mock_storage_service: StorageService,
    uploaded_clips: dict[str, str],
) -> None:
    """Verify entire video lifecycle from cyclic memory buffer to temporary export, R2 upload, and DB update."""
    # 1. Initialize BufferManager for high-definition multi-camera streams
    camera_id = "cam-haulage-01"
    buffer_mgr = BufferManager(default_maxlen=60)

    # Prime buffer with 30 synthetic video frames containing moving patterns
    for frame_idx in range(30):
        frame = sample_synthetic_frame.copy()
        # Draw moving indicator
        cv2.circle(frame, (50 + frame_idx * 15, 240), 20, (0, 0, 255), -1)
        buffer_mgr.append(camera_id=camera_id, frame=frame)

    cam_buf = buffer_mgr.get_buffer(camera_id)
    assert cam_buf is not None
    assert len(cam_buf) == 30

    # 2. Export 2-second incident clip to temporary file
    temp_dir = tempfile.mkdtemp(prefix="halocas_clip_test_")
    output_clip_path = os.path.join(temp_dir, "incident_clip_001.mp4")

    try:
        export_success = buffer_mgr.export_incident_clip(
            camera_id=camera_id,
            output_path=output_clip_path,
            duration_sec=2.0,
        )
        assert export_success is True
        assert os.path.exists(output_clip_path)
        assert os.path.getsize(output_clip_path) > 0

        # Validate video file readability via OpenCV
        cap = cv2.VideoCapture(output_clip_path)
        assert cap.isOpened() is True
        exported_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        assert exported_frame_count > 0
        cap.release()

        # 3. Create initial incident record in database
        machine = Machine(
            name="CAT 793F #404",
            type="Haul Truck",
            zone="Pit Charlie",
            status="active",
        )
        integration_db_session.add(machine)
        await integration_db_session.commit()
        await integration_db_session.refresh(machine)

        incident = Incident(
            machine_id=machine.id,
            worker_name="Worker #99",
            distance_meters=2.2,
            severity=IncidentSeverity.CRITICAL,
            closing_velocity=1.9,
            clip_url=None,
            clip_duration_sec=2.0,
            supervisor_notified=True,
            supervisor_email="safety@halocas.safety",
            zone="Pit Charlie",
        )
        integration_db_session.add(incident)
        await integration_db_session.commit()
        await integration_db_session.refresh(incident)
        assert incident.clip_url is None

        # 4. Upload incident clip to Cloudflare R2 object storage via StorageService
        object_key = mock_storage_service.build_object_key(
            incident_id=incident.id,
            camera_id=camera_id,
            timestamp=incident.timestamp,
        )
        r2_url = mock_storage_service.upload_clip(
            local_path=output_clip_path,
            object_key=object_key,
        )

        assert "https://storage.halocas.safety/" in r2_url
        assert f"incident_{incident.id}.mp4" in r2_url
        assert len(uploaded_clips) == 1

        # 5. Persist canonical R2 URL to Incident database record
        incident.clip_url = r2_url
        await integration_db_session.commit()
        await integration_db_session.refresh(incident)

        # 6. Verify Incident record is properly updated and retrievable
        stmt = select(Incident).where(Incident.id == incident.id)
        query_res = await integration_db_session.execute(stmt)
        retrieved_incident = query_res.scalar_one()

        assert retrieved_incident.clip_url == r2_url
        assert retrieved_incident.clip_duration_sec == 2.0

        # 7. Generate presigned URL for secure dashboard video player streaming
        presigned_stream_url = mock_storage_service.generate_presigned_url(object_key=object_key, expiry_seconds=1800)

        assert "https://presigned.storage.halocas.safety/" in presigned_stream_url
        assert "expires=1800" in presigned_stream_url

    finally:
        if os.path.exists(output_clip_path):
            os.remove(output_clip_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)


@pytest.mark.asyncio
async def test_multi_camera_concurrent_clip_isolation(
    sample_synthetic_frame: np.ndarray,
    mock_storage_service: StorageService,
    uploaded_clips: dict[str, str],
) -> None:
    """Verify multiple camera streams maintain separate buffers and generate distinct R2 clips."""
    buffer_mgr = BufferManager(default_maxlen=40)

    cam_a = "cam_east_crusher"
    cam_b = "cam_west_dump"

    # Frame A has red dot, Frame B has blue dot
    frame_a = sample_synthetic_frame.copy()
    cv2.circle(frame_a, (100, 100), 30, (0, 0, 255), -1)

    frame_b = sample_synthetic_frame.copy()
    cv2.circle(frame_b, (400, 400), 30, (255, 0, 0), -1)

    for _ in range(15):
        buffer_mgr.append(camera_id=cam_a, frame=frame_a)
        buffer_mgr.append(camera_id=cam_b, frame=frame_b)

    temp_dir = tempfile.mkdtemp(prefix="halocas_multicam_")
    clip_a_path = os.path.join(temp_dir, "clip_a.mp4")
    clip_b_path = os.path.join(temp_dir, "clip_b.mp4")

    try:
        assert buffer_mgr.export_incident_clip(cam_a, clip_a_path, duration_sec=1.0) is True
        assert buffer_mgr.export_incident_clip(cam_b, clip_b_path, duration_sec=1.0) is True

        key_a = mock_storage_service.build_object_key(incident_id=101, camera_id=cam_a, timestamp=None)
        key_b = mock_storage_service.build_object_key(incident_id=102, camera_id=cam_b, timestamp=None)

        url_a = mock_storage_service.upload_clip(clip_a_path, key_a)
        url_b = mock_storage_service.upload_clip(clip_b_path, key_b)

        assert url_a != url_b
        assert cam_a in url_a
        assert cam_b in url_b
        assert len(uploaded_clips) == 2
    finally:
        for p in (clip_a_path, clip_b_path):
            if os.path.exists(p):
                os.remove(p)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)
