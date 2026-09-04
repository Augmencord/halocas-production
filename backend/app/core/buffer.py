"""HALOCAS Rolling Frame Buffer and Multi-Camera Incident Clip Exporter.

This module provides a production-grade, thread-safe circular frame buffer
(RollingFrameBuffer) and a multi-camera buffer manager (BufferManager) designed
to maintain rolling in-memory windows of video streams. Upon detection of safety
breaches or critical proximity incidents, buffers export timestamp-overlaid MP4
video clips using primary (mp4v) and fallback (avc1) codecs asynchronously
without blocking real-time vision pipelines.
"""

from __future__ import annotations

import asyncio
import collections
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger("halocas.core.buffer")


class BufferError(Exception):
    """Base exception for rolling frame buffer operational failures."""


class ClipExportError(BufferError):
    """Raised when an incident video clip fails to export."""


class CameraNotFoundError(BufferError):
    """Raised when an operation targets an uninitialized camera stream."""


@dataclass(frozen=True, slots=True)
class FrameEntry:
    """Immutable container encapsulating a raw video frame and its capture timestamp.

    Attributes:
        frame: BGR numpy ndarray representing the image frame.
        timestamp: Epoch timestamp in seconds when the frame was acquired.
    """

    frame: np.ndarray
    timestamp: float


def burn_timestamp_overlay(
    frame: np.ndarray,
    timestamp: float,
    camera_id: str | None = None,
) -> np.ndarray:
    """Burn high-visibility ISO timestamp and camera metadata onto a video frame.

    Applies a semi-transparent black banner and high-contrast text overlay at the
    top of the frame to ensure legibility across extreme underground mining lighting
    conditions (dark haulage tunnels, high-glare floodlights).

    Args:
        frame: Source BGR image array.
        timestamp: Epoch timestamp in seconds.
        camera_id: Optional camera identifier (e.g., 'FRONT', 'REAR').

    Returns:
        np.ndarray: Modified image frame with burned-in telemetry overlay.
    """
    if frame is None or frame.size == 0:
        return frame

    annotated = frame.copy()
    height, width = annotated.shape[:2]

    utc_dt = datetime.fromtimestamp(timestamp, tz=UTC)
    iso_str = utc_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " UTC"
    cam_str = f"[{camera_id.upper()}] " if camera_id else ""
    overlay_text = f"HALOCAS SAFETY FEED | {cam_str}{iso_str}"

    # Visual configuration
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(0.45, min(width / 1280.0 * 0.7, 1.0))
    thickness = max(1, int(font_scale * 2))

    (text_w, text_h), baseline = cv2.getTextSize(
        overlay_text, font, font_scale, thickness
    )

    banner_h = text_h + baseline + 16
    banner_w = width

    # Semi-transparent dark banner overlay
    banner_roi = annotated[0:banner_h, 0:banner_w]
    dark_mask = np.zeros_like(banner_roi, dtype=np.uint8)
    # Blend 65% dark banner with 35% original frame
    cv2.addWeighted(dark_mask, 0.65, banner_roi, 0.35, 0, banner_roi)
    annotated[0:banner_h, 0:banner_w] = banner_roi

    # Render high-contrast text: yellow with subtle black drop-shadow
    text_x = 12
    text_y = text_h + 8

    # Shadow
    cv2.putText(
        annotated,
        overlay_text,
        (text_x + 1, text_y + 1),
        font,
        font_scale,
        (0, 0, 0),
        thickness + 1,
        cv2.LINE_AA,
    )
    # Primary yellow text
    cv2.putText(
        annotated,
        overlay_text,
        (text_x, text_y),
        font,
        font_scale,
        (0, 255, 255),
        thickness,
        cv2.LINE_AA,
    )

    return annotated


class RollingFrameBuffer:
    """Thread-safe circular ring buffer storing the latest N video frames.

    Designed for sub-millisecond append latency inside real-time computer vision
    loops and non-blocking retrieval for incident video clip generation.
    """

    def __init__(self, maxlen: int | None = None) -> None:
        """Initialize the RollingFrameBuffer.

        Args:
            maxlen: Maximum frame capacity. If None, derived from application
                settings (CLIP_DURATION_SECONDS * FPS, default 150 frames = 5s @ 30fps).
        """
        settings = get_settings()
        default_capacity = settings.CLIP_DURATION_SECONDS * settings.FPS
        if maxlen is not None and maxlen > 0:
            self.maxlen = maxlen
        elif default_capacity > 0:
            self.maxlen = default_capacity
        else:
            self.maxlen = 150

        self._buffer: collections.deque[FrameEntry] = collections.deque(
            maxlen=self.maxlen
        )
        self._lock = threading.RLock()
        self._total_appended: int = 0
        self._dropped_invalid: int = 0

        logger.info(
            "RollingFrameBuffer initialized with maxlen=%d (%.1fs at %dfps)",
            self.maxlen,
            self.maxlen / max(settings.FPS, 1),
            settings.FPS,
        )

    @property
    def total_appended(self) -> int:
        """Total valid frames appended across buffer lifetime."""
        with self._lock:
            return self._total_appended

    @property
    def dropped_invalid(self) -> int:
        """Total invalid or corrupt frames rejected by append validation."""
        with self._lock:
            return self._dropped_invalid

    def append(self, frame: np.ndarray, timestamp: float | None = None) -> bool:
        """Append a frame to the circular ring buffer in a thread-safe manner.

        Args:
            frame: Video frame array (expected BGR uint8 ndarray).
            timestamp: Epoch timestamp in seconds. Defaults to time.time() if None.

        Returns:
            bool: True if frame passed validation and was stored, False otherwise.
        """
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            with self._lock:
                self._dropped_invalid += 1
            logger.warning("Rejected invalid frame: None or empty ndarray")
            return False

        if len(frame.shape) not in (2, 3):
            with self._lock:
                self._dropped_invalid += 1
            logger.warning(
                "Rejected frame with abnormal dimensions: shape=%s",
                str(frame.shape),
            )
            return False

        ts = timestamp if timestamp is not None else time.time()
        entry = FrameEntry(frame=frame, timestamp=ts)

        with self._lock:
            self._buffer.append(entry)
            self._total_appended += 1

        return True

    def get_entries(
        self, duration_sec: float | None = None, fps: int | None = None
    ) -> list[FrameEntry]:
        """Retrieve a thread-safe snapshot copy of buffered frame entries.

        Args:
            duration_sec: Target duration of frames to return.
            fps: Frame rate used to calculate frame count (defaults to config.FPS).

        Returns:
            list[FrameEntry]: Chronologically ordered frame entries.
        """
        with self._lock:
            if not self._buffer:
                return []

            if duration_sec is not None and duration_sec > 0:
                rate = fps if fps is not None and fps > 0 else get_settings().FPS
                num_frames = min(int(duration_sec * rate), len(self._buffer))
                return list(self._buffer)[-num_frames:]

            return list(self._buffer)

    def get_frames(
        self, duration_sec: float | None = None, fps: int | None = None
    ) -> list[np.ndarray]:
        """Retrieve a list of raw image arrays without timestamp metadata.

        Args:
            duration_sec: Optional duration in seconds to retrieve.
            fps: Frame rate for slice calculation.

        Returns:
            list[np.ndarray]: Chronological sequence of image frames.
        """
        entries = self.get_entries(duration_sec=duration_sec, fps=fps)
        return [entry.frame for entry in entries]

    def clear(self) -> None:
        """Clear all buffered frames and reset counters."""
        with self._lock:
            self._buffer.clear()
            logger.debug("RollingFrameBuffer cleared")

    def __len__(self) -> int:
        """Return the current number of frames residing in the buffer."""
        with self._lock:
            return len(self._buffer)

    def is_empty(self) -> bool:
        """Return True if the buffer contains zero frames."""
        with self._lock:
            return len(self._buffer) == 0

    def export_incident_clip(
        self,
        output_path: str,
        duration_sec: int | float | None = None,
        fps: int | None = None,
        overlay_timestamp: bool = True,
        camera_id: str | None = None,
    ) -> bool:
        """Export buffered frames to an MP4 video clip with primary/fallback codecs.

        Uses 'mp4v' as the primary codec and seamlessly falls back to 'avc1'
        if the primary encoder is unavailable. Optionally burns a high-visibility
        ISO-8601 timestamp overlay on each frame.

        Args:
            output_path: Destination filesystem path for the .mp4 file.
            duration_sec: Length of clip to export in seconds. Defaults to config.
            fps: Video frame rate. Defaults to config.FPS.
            overlay_timestamp: Whether to burn ISO timestamp overlay on frames.
            camera_id: Optional camera name to embed in the overlay banner.

        Returns:
            bool: True if the video clip was successfully written and closed.
        """
        settings = get_settings()
        target_fps = int(fps if fps is not None and fps > 0 else settings.FPS)
        target_duration = (
            float(duration_sec)
            if duration_sec is not None and duration_sec > 0
            else float(settings.CLIP_DURATION_SECONDS)
        )

        entries = self.get_entries(duration_sec=target_duration, fps=target_fps)
        if not entries:
            logger.error(
                "Export incident clip failed: buffer contains no frames for camera=%s (output=%s)",
                str(camera_id),
                output_path,
            )
            return False

        # Ensure target directory exists
        try:
            out_file = Path(output_path).resolve()
            out_file.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.error(
                "Failed to create output directory for clip export %s: %s",
                output_path,
                str(exc),
            )
            return False

        sample_frame = entries[0].frame
        height, width = sample_frame.shape[:2]
        frame_size = (width, height)

        # Primary codec: mp4v; Fallback codec: avc1
        codecs_to_try = [
            ("mp4v", cv2.VideoWriter_fourcc(*"mp4v")),  # type: ignore[attr-defined]
            ("avc1", cv2.VideoWriter_fourcc(*"avc1")),  # type: ignore[attr-defined]
        ]

        writer: cv2.VideoWriter | None = None
        selected_codec = ""

        for codec_name, fourcc in codecs_to_try:
            try:
                candidate_writer = cv2.VideoWriter(
                    str(out_file), fourcc, float(target_fps), frame_size
                )
                if candidate_writer.isOpened():
                    writer = candidate_writer
                    selected_codec = codec_name
                    logger.debug(
                        "Initialized VideoWriter successfully: codec=%s, path=%s, fps=%d, dims=%s",
                        codec_name,
                        str(out_file),
                        target_fps,
                        str(frame_size),
                    )
                    break
                candidate_writer.release()
                logger.warning(
                    "VideoWriter failed to open with codec %s for path %s",
                    codec_name,
                    str(out_file),
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Exception initializing VideoWriter codec %s: %s",
                    codec_name,
                    str(exc),
                )

        if writer is None or not writer.isOpened():
            logger.error(
                "VideoWriter failed to open with all candidate codecs (mp4v, avc1) for path %s",
                str(out_file),
            )
            return False

        frames_written = 0
        try:
            for entry in entries:
                frame_to_write = entry.frame
                # Ensure frame size matches writer expectations
                if frame_to_write.shape[:2] != (height, width):
                    frame_to_write = cv2.resize(frame_to_write, frame_size)

                # Burn overlay if requested
                if overlay_timestamp:
                    frame_to_write = burn_timestamp_overlay(
                        frame=frame_to_write,
                        timestamp=entry.timestamp,
                        camera_id=camera_id,
                    )

                writer.write(frame_to_write)
                frames_written += 1

            logger.info(
                "Incident clip exported successfully to %s (%d frames, codec=%s, cam=%s)",
                str(out_file),
                frames_written,
                selected_codec,
                str(camera_id),
            )
            return True

        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Error occurred during frame encoding/write to %s after %d frames: %s",
                str(out_file),
                frames_written,
                str(exc),
            )
            return False

        finally:
            writer.release()


class BufferManager:
    """Manages rolling frame buffers for multiple camera streams.

    Supports dynamic camera registration, centralized video ingestion, synchronized
    multi-camera incident clip extraction, and asynchronous thread-pool offloading.
    """

    def __init__(self, default_maxlen: int | None = None) -> None:
        """Initialize the BufferManager.

        Args:
            default_maxlen: Default frame capacity per camera buffer.
        """
        self.default_maxlen = default_maxlen
        self._buffers: dict[str, RollingFrameBuffer] = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="halocas-buffer-export"
        )
        logger.info(
            "BufferManager initialized with default_maxlen=%s",
            str(default_maxlen),
        )

    def get_or_create_buffer(
        self, camera_id: str, maxlen: int | None = None
    ) -> RollingFrameBuffer:
        """Retrieve existing buffer for camera_id or create a new one.

        Args:
            camera_id: Unique camera feed identifier (e.g. 'front', 'rear').
            maxlen: Optional custom capacity for this camera buffer.

        Returns:
            RollingFrameBuffer: The active buffer instance for this camera.
        """
        cid = camera_id.strip().lower()
        with self._lock:
            if cid not in self._buffers:
                capacity = maxlen or self.default_maxlen
                self._buffers[cid] = RollingFrameBuffer(maxlen=capacity)
                logger.info(
                    "Created new camera buffer for camera=%s with capacity=%s",
                    cid,
                    str(capacity),
                )
            return self._buffers[cid]

    def get_buffer(self, camera_id: str) -> RollingFrameBuffer | None:
        """Retrieve buffer for camera_id, or None if uninitialized.

        Args:
            camera_id: Unique camera identifier.

        Returns:
            RollingFrameBuffer | None: The camera buffer or None.
        """
        cid = camera_id.strip().lower()
        with self._lock:
            return self._buffers.get(cid)

    def append(
        self,
        camera_id: str,
        frame: np.ndarray,
        timestamp: float | None = None,
    ) -> bool:
        """Append a frame to the specified camera stream buffer.

        Args:
            camera_id: Unique camera identifier.
            frame: Video frame array.
            timestamp: Optional epoch timestamp.

        Returns:
            bool: True if stored successfully, False if frame invalid.
        """
        buffer = self.get_or_create_buffer(camera_id)
        return buffer.append(frame=frame, timestamp=timestamp)

    def get_all_camera_ids(self) -> list[str]:
        """Return a list of all active registered camera identifiers."""
        with self._lock:
            return list(self._buffers.keys())

    def clear(self, camera_id: str | None = None) -> None:
        """Clear buffer for a specific camera or all cameras.

        Args:
            camera_id: Optional camera to clear. If None, clears all buffers.
        """
        with self._lock:
            if camera_id is not None:
                buf = self._buffers.get(camera_id.strip().lower())
                if buf:
                    buf.clear()
            else:
                for buf in self._buffers.values():
                    buf.clear()

    def export_incident_clip(
        self,
        camera_id: str,
        output_path: str,
        duration_sec: int | float | None = None,
        fps: int | None = None,
        overlay_timestamp: bool = True,
    ) -> bool:
        """Export an incident clip from a specific camera stream.

        Args:
            camera_id: Identifier of target camera.
            output_path: Destination path for output .mp4 clip.
            duration_sec: Temporal window in seconds.
            fps: Frame rate for export.
            overlay_timestamp: Whether to burn timestamp and camera banner.

        Returns:
            bool: True if export succeeded, False otherwise.
        """
        buf = self.get_buffer(camera_id)
        if buf is None:
            logger.error(
                "Export incident clip failed: camera %s not registered (path=%s)",
                camera_id,
                output_path,
            )
            return False

        return buf.export_incident_clip(
            output_path=output_path,
            duration_sec=duration_sec,
            fps=fps,
            overlay_timestamp=overlay_timestamp,
            camera_id=camera_id,
        )

    def export_multi_camera_clip(
        self,
        output_dir: str,
        duration_sec: int | float | None = None,
        fps: int | None = None,
        filename_prefix: str = "incident",
        overlay_timestamp: bool = True,
    ) -> dict[str, str]:
        """Export synchronized incident clips across all registered camera streams.

        Args:
            output_dir: Destination directory where clips will be stored.
            duration_sec: Temporal length of clips.
            fps: Frame rate for video encoding.
            filename_prefix: Prefix for generated video files.
            overlay_timestamp: Whether to burn timestamp/camera overlays.

        Returns:
            dict[str, str]: Mapping of camera_id -> absolute output clip path
                for all successfully exported clips.
        """
        with self._lock:
            active_cameras = list(self._buffers.items())

        if not active_cameras:
            logger.warning("export_multi_camera_clip called with no active cameras")
            return {}

        timestamp_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        out_directory = Path(output_dir).resolve()
        out_directory.mkdir(parents=True, exist_ok=True)

        exported_clips: dict[str, str] = {}

        for cid, buffer in active_cameras:
            clip_name = f"{filename_prefix}_{cid}_{timestamp_str}.mp4"
            clip_path = str(out_directory / clip_name)

            success = buffer.export_incident_clip(
                output_path=clip_path,
                duration_sec=duration_sec,
                fps=fps,
                overlay_timestamp=overlay_timestamp,
                camera_id=cid,
            )

            if success:
                exported_clips[cid] = clip_path
            else:
                logger.warning(
                    "Multi-camera export failed for camera %s (path=%s)",
                    cid,
                    clip_path,
                )

        return exported_clips

    async def async_export_incident_clip(
        self,
        camera_id: str,
        output_path: str,
        duration_sec: int | float | None = None,
        fps: int | None = None,
        overlay_timestamp: bool = True,
    ) -> bool:
        """Asynchronously export an incident clip in a background thread pool worker.

        Prevents blocking the async event loop during video encoding and I/O.

        Args:
            camera_id: Target camera identifier.
            output_path: Destination path for .mp4 clip.
            duration_sec: Clip length in seconds.
            fps: Video frames per second.
            overlay_timestamp: Whether to burn metadata banner.

        Returns:
            bool: True on successful clip creation, False otherwise.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            self.export_incident_clip,
            camera_id,
            output_path,
            duration_sec,
            fps,
            overlay_timestamp,
        )

    async def async_export_multi_camera_clip(
        self,
        output_dir: str,
        duration_sec: int | float | None = None,
        fps: int | None = None,
        filename_prefix: str = "incident",
        overlay_timestamp: bool = True,
    ) -> dict[str, str]:
        """Asynchronously export multi-camera clips in a background thread pool.

        Args:
            output_dir: Output directory path.
            duration_sec: Clip duration in seconds.
            fps: Frame rate.
            filename_prefix: Clip naming prefix.
            overlay_timestamp: Overlay telemetry toggle.

        Returns:
            dict[str, str]: Mapping of camera_id to exported file path.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            self.export_multi_camera_clip,
            output_dir,
            duration_sec,
            fps,
            filename_prefix,
            overlay_timestamp,
        )

    def close(self) -> None:
        """Shut down background thread pool executor cleanly."""
        self._executor.shutdown(wait=False)
        logger.info("BufferManager executor shut down")
