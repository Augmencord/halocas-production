"""Tests for the RollingFrameBuffer and BufferManager subsystems.

Validates thread-safe ring buffer functionality, multi-camera buffer routing,
timestamp overlay burning, synchronous and asynchronous incident video clip exports,
codec fallback dynamics, and concurrent write resilience.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.core.buffer import (
    BufferManager,
    FrameEntry,
    RollingFrameBuffer,
    burn_timestamp_overlay,
)


@pytest.fixture
def sample_frame() -> np.ndarray:
    """Create a standard synthetic 480x640 BGR image frame."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Add colored patterns so it is non-empty
    frame[100:200, 100:300] = [0, 255, 0]  # Green box
    frame[300:400, 400:600] = [0, 0, 255]  # Red box
    return frame


def test_buffer_initialization_and_properties() -> None:
    """Verify default capacity calculation and capacity override."""
    buf_default = RollingFrameBuffer()
    assert buf_default.maxlen == 150
    assert len(buf_default) == 0
    assert buf_default.is_empty()
    assert buf_default.total_appended == 0
    assert buf_default.dropped_invalid == 0

    buf_custom = RollingFrameBuffer(maxlen=45)
    assert buf_custom.maxlen == 45


def test_buffer_append_and_overflow(sample_frame: np.ndarray) -> None:
    """Verify standard appending, overflow eviction, and snapshot ordering."""
    buf = RollingFrameBuffer(maxlen=3)

    # Append 3 frames
    t0 = time.time()
    for i in range(3):
        success = buf.append(sample_frame, timestamp=t0 + i)
        assert success is True

    assert len(buf) == 3
    assert buf.total_appended == 3
    assert not buf.is_empty()

    # Append 4th frame -> should drop the first frame
    success = buf.append(sample_frame, timestamp=t0 + 10.0)
    assert success is True
    assert len(buf) == 3
    assert buf.total_appended == 4

    entries = buf.get_entries()
    assert len(entries) == 3
    assert entries[0].timestamp == t0 + 1
    assert entries[1].timestamp == t0 + 2
    assert entries[2].timestamp == t0 + 10.0

    # Test get_frames
    frames = buf.get_frames()
    assert len(frames) == 3
    assert all(isinstance(f, np.ndarray) for f in frames)

    # Test sliced duration
    # If duration_sec=0.05s and fps=30 -> ~1 frame
    sliced_entries = buf.get_entries(duration_sec=0.05, fps=30)
    assert len(sliced_entries) == 1
    assert sliced_entries[0].timestamp == t0 + 10.0

    # Clear buffer
    buf.clear()
    assert len(buf) == 0
    assert buf.is_empty()


def test_buffer_invalid_frame_handling() -> None:
    """Verify robust rejection of None, empty, or malformed ndarrays."""
    buf = RollingFrameBuffer(maxlen=5)

    # None frame
    assert buf.append(None) is False  # type: ignore[arg-type]
    # Empty ndarray
    assert buf.append(np.array([], dtype=np.uint8)) is False
    # Non-ndarray
    assert buf.append("not a frame") is False  # type: ignore[arg-type]
    # 1D array
    assert buf.append(np.zeros((100,), dtype=np.uint8)) is False
    # 4D array
    assert buf.append(np.zeros((2, 100, 100, 3), dtype=np.uint8)) is False

    assert len(buf) == 0
    assert buf.total_appended == 0
    assert buf.dropped_invalid == 5


def test_timestamp_overlay_generation(sample_frame: np.ndarray) -> None:
    """Verify that timestamp overlay is non-destructive and alters pixel values in the banner."""
    original = sample_frame.copy()
    ts = 1756992000.123  # Known epoch timestamp
    annotated = burn_timestamp_overlay(original, timestamp=ts, camera_id="FRONT")

    # Original frame must NOT be modified in place
    assert np.array_equal(original, sample_frame)
    # Annotated frame must have altered pixels in the top banner region
    assert not np.array_equal(annotated, original)
    # Banner area top rows must have non-zero or blended pixels
    assert annotated.shape == original.shape

    # Handle edge case: empty or None frame
    empty = np.array([])
    assert burn_timestamp_overlay(empty, timestamp=ts) is empty


def test_buffer_thread_safety_concurrent_writes(sample_frame: np.ndarray) -> None:
    """Verify thread-safety when multiple worker threads append frames concurrently."""
    capacity = 100
    buf = RollingFrameBuffer(maxlen=capacity)
    num_threads = 8
    frames_per_thread = 50

    def worker(worker_id: int) -> None:
        for idx in range(frames_per_thread):
            t = time.time() + (worker_id * 100) + idx
            buf.append(sample_frame, timestamp=t)

    with ThreadPoolExecutor(max_workers=num_threads) as pool:
        futures = [pool.submit(worker, i) for i in range(num_threads)]
        for f in futures:
            f.result()

    assert len(buf) == capacity
    assert buf.total_appended == num_threads * frames_per_thread
    assert buf.dropped_invalid == 0

    entries = buf.get_entries()
    assert len(entries) == capacity
    for entry in entries:
        assert isinstance(entry, FrameEntry)
        assert entry.frame.shape == sample_frame.shape


def test_export_incident_clip_empty_buffer(tmp_path: Path) -> None:
    """Verify export returns False gracefully when buffer is empty."""
    buf = RollingFrameBuffer(maxlen=10)
    out_file = str(tmp_path / "empty.mp4")
    success = buf.export_incident_clip(output_path=out_file)
    assert success is False
    assert not os.path.exists(out_file)


def test_export_incident_clip_with_mocked_videowriter(
    tmp_path: Path, sample_frame: np.ndarray
) -> None:
    """Verify clip export with mocked VideoWriter covering write calls and cleanup."""
    buf = RollingFrameBuffer(maxlen=10)
    for _ in range(5):
        buf.append(sample_frame)

    out_file = str(tmp_path / "mocked_clip.mp4")

    mock_writer = MagicMock()
    mock_writer.isOpened.return_value = True

    with patch("cv2.VideoWriter", return_value=mock_writer):
        success = buf.export_incident_clip(
            output_path=out_file, duration_sec=2, fps=30, overlay_timestamp=True
        )
        assert success is True
        assert mock_writer.write.call_count == 5
        mock_writer.release.assert_called_once()


def test_export_incident_clip_codec_fallback(
    tmp_path: Path, sample_frame: np.ndarray
) -> None:
    """Verify that if primary mp4v codec fails to open, it falls back to avc1."""
    buf = RollingFrameBuffer(maxlen=5)
    for _ in range(3):
        buf.append(sample_frame)

    out_file = str(tmp_path / "fallback_clip.mp4")

    # First instance fails isOpened(), second succeeds
    fail_writer = MagicMock()
    fail_writer.isOpened.return_value = False

    success_writer = MagicMock()
    success_writer.isOpened.return_value = True

    with patch("cv2.VideoWriter", side_effect=[fail_writer, success_writer]):
        success = buf.export_incident_clip(output_path=out_file)
        assert success is True
        fail_writer.release.assert_called_once()
        assert success_writer.write.call_count == 3
        success_writer.release.assert_called_once()


def test_export_incident_clip_both_codecs_fail(
    tmp_path: Path, sample_frame: np.ndarray
) -> None:
    """Verify handling when all candidate codecs fail to open."""
    buf = RollingFrameBuffer(maxlen=5)
    buf.append(sample_frame)

    out_file = str(tmp_path / "fail_clip.mp4")

    fail_writer = MagicMock()
    fail_writer.isOpened.return_value = False

    with patch("cv2.VideoWriter", return_value=fail_writer):
        success = buf.export_incident_clip(output_path=out_file)
        assert success is False


def test_export_incident_clip_write_exception(
    tmp_path: Path, sample_frame: np.ndarray
) -> None:
    """Verify graceful handling and resource cleanup when writer.write raises an error."""
    buf = RollingFrameBuffer(maxlen=5)
    buf.append(sample_frame)

    out_file = str(tmp_path / "error_clip.mp4")

    mock_writer = MagicMock()
    mock_writer.isOpened.return_value = True
    mock_writer.write.side_effect = RuntimeError("Disk full / encoder crash")

    with patch("cv2.VideoWriter", return_value=mock_writer):
        success = buf.export_incident_clip(output_path=out_file)
        assert success is False
        mock_writer.release.assert_called_once()


def test_buffer_manager_multi_camera_lifecycle(sample_frame: np.ndarray) -> None:
    """Verify multi-camera buffer registration, retrieval, and independent clearing."""
    manager = BufferManager(default_maxlen=30)

    assert manager.get_all_camera_ids() == []
    assert manager.get_buffer("front") is None

    # Appending automatically creates buffer
    manager.append("front", sample_frame)
    manager.append("rear", sample_frame)
    manager.append("cabin", sample_frame)

    assert set(manager.get_all_camera_ids()) == {"front", "rear", "cabin"}

    front_buf = manager.get_buffer("front")
    assert front_buf is not None
    assert len(front_buf) == 1

    # Clear individual camera
    manager.clear("front")
    assert len(front_buf) == 0
    rear_buf = manager.get_buffer("rear")
    assert rear_buf is not None and len(rear_buf) == 1

    # Clear all cameras
    manager.clear()
    assert len(rear_buf) == 0

    manager.close()


def test_buffer_manager_export_incident_clip(
    tmp_path: Path, sample_frame: np.ndarray
) -> None:
    """Verify BufferManager single-camera export delegate."""
    manager = BufferManager(default_maxlen=10)
    out_file = str(tmp_path / "single_cam.mp4")

    # Target non-existent camera
    assert manager.export_incident_clip("unknown", out_file) is False

    # Target active camera with mocked writer
    manager.append("front", sample_frame)
    mock_writer = MagicMock()
    mock_writer.isOpened.return_value = True

    with patch("cv2.VideoWriter", return_value=mock_writer):
        success = manager.export_incident_clip("front", out_file)
        assert success is True
        assert mock_writer.write.call_count == 1
        mock_writer.release.assert_called_once()

    manager.close()


def test_buffer_manager_export_multi_camera_clip(
    tmp_path: Path, sample_frame: np.ndarray
) -> None:
    """Verify synchronized multi-camera clip export."""
    manager = BufferManager(default_maxlen=10)
    out_dir = str(tmp_path / "incident_clips")

    # Empty manager
    assert manager.export_multi_camera_clip(output_dir=out_dir) == {}

    # Multi-camera population
    for _ in range(3):
        manager.append("cam_front", sample_frame)
        manager.append("cam_rear", sample_frame)

    mock_writer = MagicMock()
    mock_writer.isOpened.return_value = True

    with patch("cv2.VideoWriter", return_value=mock_writer):
        results = manager.export_multi_camera_clip(
            output_dir=out_dir,
            duration_sec=1.0,
            fps=30,
            filename_prefix="test_incident",
        )
        assert "cam_front" in results
        assert "cam_rear" in results
        assert "test_incident_cam_front" in results["cam_front"]
        assert "test_incident_cam_rear" in results["cam_rear"]
        assert mock_writer.write.call_count == 6  # 3 frames * 2 cameras

    manager.close()


@pytest.mark.asyncio
async def test_buffer_manager_async_exports(
    tmp_path: Path, sample_frame: np.ndarray
) -> None:
    """Verify asynchronous execution wrappers offload video encoding to thread pool."""
    manager = BufferManager(default_maxlen=10)
    manager.append("front", sample_frame)
    manager.append("rear", sample_frame)

    mock_writer = MagicMock()
    mock_writer.isOpened.return_value = True

    with patch("cv2.VideoWriter", return_value=mock_writer):
        # Test async single clip export
        out_single = str(tmp_path / "async_single.mp4")
        single_res = await manager.async_export_incident_clip(
            camera_id="front",
            output_path=out_single,
        )
        assert single_res is True

        # Test async multi-camera export
        multi_dir = str(tmp_path / "async_multi")
        multi_res = await manager.async_export_multi_camera_clip(
            output_dir=multi_dir,
        )
        assert "front" in multi_res
        assert "rear" in multi_res

    manager.close()
