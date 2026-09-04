"""Central Pipeline Orchestrator for HALOCAS.

Ties together computer vision detection and ByteTrack tracking (Detector),
proximity physics and trajectory evaluation (SafetyStateMachine), biometric
facial recognition (FaceVerifier), rolling circular buffer clip generation
(BufferManager), Cloudflare R2 object storage (StorageService), Resend supervisor
alert dispatching (NotificationService), PostgreSQL database persistence, and
real-time WebSocket telemetry streaming.
"""

from __future__ import annotations

import os
import tempfile
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import cv2
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.buffer import BufferManager
from app.core.detector import DetectionResult, Detector
from app.core.face_verifier import FaceVerifier
from app.core.logging import get_logger
from app.core.state_machine import SafetyEvent, SafetyStateMachine, Severity
from app.core.telemetry import manager as ws_manager
from app.models.incident import Incident, IncidentSeverity
from app.models.worker import Worker

if TYPE_CHECKING:
    from app.services.notification import NotificationService
    from app.services.storage import StorageService

logger = get_logger("halocas.core.pipeline")


class PipelineError(Exception):
    """Base exception for pipeline orchestration failures."""


class PipelineInputError(PipelineError, ValueError):
    """Raised when an invalid or corrupt input frame/video is supplied to the pipeline."""


class PipelineOrchestrator:
    """Central orchestrator managing the full real-time collision avoidance lifecycle."""

    def __init__(
        self,
        detector: Detector,
        state_machine: SafetyStateMachine,
        face_verifier: FaceVerifier,
        buffer_manager: BufferManager,
        storage: StorageService,
        notification: NotificationService,
        db: AsyncSession | async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        """Initialize the pipeline orchestrator with all necessary subsystems.

        Args:
            detector: Vision model running YOLOv8 tracking for personnel and equipment.
            state_machine: Monocular proximity physics and debounce filter engine.
            face_verifier: DeepFace biometric identifier matching candidate workers.
            buffer_manager: Rolling ring buffer maintaining pre/post incident video clips.
            storage: Cloudflare R2 S3-compatible cloud storage service.
            notification: Resend email alert dispatching service.
            db: Optional active AsyncSession or sessionmaker factory.
        """
        self.detector = detector
        self.state_machine = state_machine
        self.face_verifier = face_verifier
        self.buffer_manager = buffer_manager
        self.storage = storage
        self.notification = notification
        self.db = db

        # Observability counters
        self.total_frames_processed: int = 0
        self.total_incidents_logged: int = 0
        self.total_notifications_sent: int = 0

        logger.info(
            "PipelineOrchestrator initialized with detector=%s, state_machine=%s, "
            "face_verifier=%s, buffer_manager=%s, storage=%s, notification=%s",
            detector.__class__.__name__,
            state_machine.__class__.__name__,
            face_verifier.__class__.__name__,
            buffer_manager.__class__.__name__,
            storage.__class__.__name__,
            notification.__class__.__name__,
        )

    @asynccontextmanager
    async def _get_db_session(self) -> AsyncIterator[AsyncSession]:
        """Provide a contextual transactional async database session."""
        if isinstance(self.db, AsyncSession):
            yield self.db
        elif isinstance(self.db, async_sessionmaker):
            async with self.db() as session:
                yield session
        else:
            from app.db.session import async_session_factory

            async with async_session_factory() as session:
                yield session

    def _validate_frame(self, frame: np.ndarray | None) -> None:
        """Verify that the supplied frame is a valid non-empty NumPy image array."""
        if frame is None:
            raise PipelineInputError("Frame cannot be None")
        if not isinstance(frame, np.ndarray):
            raise PipelineInputError(f"Expected numpy.ndarray frame, got {type(frame).__name__}")
        if frame.size == 0 or len(frame.shape) < 2:
            raise PipelineInputError(f"Frame is empty or invalid shape: {getattr(frame, 'shape', None)}")

    async def _query_worker_candidates(self, session: AsyncSession) -> list[dict[str, Any]]:
        """Retrieve registered workers who possess enrolled face embeddings."""
        try:
            stmt = select(Worker).where(Worker.face_embedding.is_not(None))
            result = await session.execute(stmt)
            workers = result.scalars().all()
            return [
                {
                    "id": w.id,
                    "name": w.name,
                    "face_embedding": w.face_embedding,
                    "supervisor_email": w.supervisor_email,
                    "is_authorized": w.is_authorized,
                }
                for w in workers
                if w.face_embedding is not None
            ]
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to query worker candidates from database: %s", exc, exc_info=True)
            return []

    async def _handle_critical_event(
        self,
        event: SafetyEvent,
        frame: np.ndarray,
        camera_id: str,
        workers: list[dict[str, Any]],
        session: AsyncSession,
    ) -> Incident | None:
        """Handle execution sequence for a critical proximity breach.

        Executes biometric face match, temporary video clip export, Cloudflare R2
        upload, database incident persistence, and supervisor email notification.
        """
        t_crit_start = time.perf_counter()
        event_dt = datetime.fromtimestamp(event.timestamp, tz=UTC)

        # 1. Face Verification / Worker Matching
        t_face_start = time.perf_counter()
        worker_db_id: int | None = None
        worker_name: str = f"Worker #{event.worker_id}"
        supervisor_email: str | None = None
        face_match_confidence: float | None = None

        target_worker_det: dict[str, Any] | None = next(
            (w for w in workers if w.get("id") == event.worker_id), None
        )

        if target_worker_det and target_worker_det.get("bbox"):
            candidates = await self._query_worker_candidates(session)
            if candidates:
                try:
                    match = self.face_verifier.verify(
                        frame=frame,
                        bbox=target_worker_det["bbox"],
                        database_workers=candidates,
                    )
                    if match is not None:
                        worker_db_id = match.get("id")
                        worker_name = match.get("name", worker_name)
                        supervisor_email = match.get("supervisor_email")
                        face_match_confidence = match.get("confidence")
                        logger.info(
                            "Biometric verification matched worker '%s' (ID %s, conf=%.3f)",
                            worker_name,
                            str(worker_db_id),
                            face_match_confidence or 0.0,
                        )
                    else:
                        logger.debug(
                            "Face verification yielded no match above threshold for worker tracker %d",
                            event.worker_id,
                        )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Biometric verification encountered exception: %s", exc)

        face_verify_ms = (time.perf_counter() - t_face_start) * 1000

        # 2. Initial Database Incident Record
        incident = Incident(
            timestamp=event_dt,
            machine_id=event.machine_id,
            worker_id=worker_db_id,
            worker_name=worker_name,
            distance_meters=round(event.distance_meters, 2),
            severity=IncidentSeverity.CRITICAL,
            closing_velocity=round(event.closing_velocity, 2),
            clip_url=None,
            clip_duration_sec=5.0,
            supervisor_notified=False,
            supervisor_email=supervisor_email,
            face_match_confidence=face_match_confidence,
            zone=f"Camera {camera_id.upper()}",
        )
        session.add(incident)
        await session.flush()
        incident_id = incident.id

        # 3. Export Incident Video Clip from Buffer
        t_export_start = time.perf_counter()
        temp_clip_path: str | None = None
        clip_url: str | None = None

        try:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
                temp_clip_path = tmp_file.name

            export_ok = self.buffer_manager.export_incident_clip(
                camera_id=camera_id,
                output_path=temp_clip_path,
                duration_sec=5.0,
            )

            clip_export_ms = (time.perf_counter() - t_export_start) * 1000

            # 4. Upload Clip to Cloudflare R2
            t_storage_start = time.perf_counter()
            if export_ok and os.path.exists(temp_clip_path) and os.path.getsize(temp_clip_path) > 0:
                object_key = self.storage.build_object_key(
                    incident_id=incident_id,
                    camera_id=camera_id,
                    timestamp=event_dt,
                )
                clip_url = self.storage.upload_clip(
                    local_path=temp_clip_path,
                    object_key=object_key,
                )
                incident.clip_url = clip_url
                logger.info(
                    "Uploaded incident clip for ID %d to R2: %s",
                    incident_id,
                    clip_url,
                )
            else:
                logger.warning(
                    "Clip export did not produce valid video file for incident %d",
                    incident_id,
                )
            storage_upload_ms = (time.perf_counter() - t_storage_start) * 1000
        except Exception as exc:  # noqa: BLE001
            logger.error("Clip export or cloud storage upload failed for incident %d: %s", incident_id, exc)
            clip_export_ms = 0.0
            storage_upload_ms = 0.0
        finally:
            if temp_clip_path and os.path.exists(temp_clip_path):
                try:
                    os.remove(temp_clip_path)
                except OSError as err:
                    logger.debug("Could not remove temp clip file %s: %s", temp_clip_path, err)

        # 5. Dispatch Supervisor Notification
        t_notif_start = time.perf_counter()
        if supervisor_email:
            try:
                sent = await self.notification.send_proximity_alert(
                    supervisor_email=supervisor_email,
                    worker_name=worker_name,
                    distance=event.distance_meters,
                    clip_url=clip_url,
                    incident_id=incident_id,
                    db_session=session,
                )
                if sent:
                    incident.supervisor_notified = True
                    incident.notification_sent_at = datetime.now(UTC)
                    self.total_notifications_sent += 1
                    logger.info(
                        "Dispatched proximity alert to supervisor %s for incident %d",
                        supervisor_email,
                        incident_id,
                    )
                else:
                    logger.warning(
                        "Notification service failed delivery to %s for incident %d",
                        supervisor_email,
                        incident_id,
                    )
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed sending supervisor notification for incident %d: %s", incident_id, exc)

        notification_ms = (time.perf_counter() - t_notif_start) * 1000

        await session.commit()
        await session.refresh(incident)
        self.total_incidents_logged += 1

        total_crit_ms = (time.perf_counter() - t_crit_start) * 1000
        logger.info(
            "Critical event handled for incident=%d (worker=%s, machine=%d, dist=%.2fm, "
            "face_ms=%.1f, export_ms=%.1f, upload_ms=%.1f, notif_ms=%.1f, total_ms=%.1f)",
            incident_id,
            worker_name,
            event.machine_id,
            event.distance_meters,
            face_verify_ms,
            clip_export_ms,
            storage_upload_ms,
            notification_ms,
            total_crit_ms,
        )
        return incident

    async def process_frame(
        self,
        frame: np.ndarray,
        camera_id: str = "main",
        timestamp: float | None = None,
    ) -> list[SafetyEvent]:
        """Process a single video frame through the complete HALOCAS safety pipeline.

        Args:
            frame: Video image frame as NumPy BGR array.
            camera_id: Identifier of the source camera.
            timestamp: Optional capture timestamp in seconds. Defaults to UTC now.

        Returns:
            list[SafetyEvent]: Evaluated safety proximity events for the current frame.
        """
        t_frame_start = time.perf_counter()
        self._validate_frame(frame)

        ts = timestamp if timestamp is not None else datetime.now(UTC).timestamp()

        # 1. Append frame to circular buffer
        self.buffer_manager.append(camera_id=camera_id, frame=frame, timestamp=ts)

        # 2. Run object detection and tracking
        t_det_start = time.perf_counter()
        detections: list[DetectionResult] = self.detector.detect_and_track(frame)
        detect_ms = (time.perf_counter() - t_det_start) * 1000

        # 3. Separate detections into machines and workers
        machines: list[dict[str, Any]] = []
        workers: list[dict[str, Any]] = []

        for d in detections:
            entity_id = d.id if d.id is not None else 0
            if d.class_name in ("truck", "machine"):
                machines.append(
                    {
                        "id": entity_id,
                        "bbox": d.bbox,
                        "confidence": d.confidence,
                        "class_name": d.class_name,
                    }
                )
            elif d.class_name in ("person", "worker"):
                workers.append(
                    {
                        "id": entity_id,
                        "bbox": d.bbox,
                        "confidence": d.confidence,
                        "class_name": d.class_name,
                    }
                )

        # 4. Evaluate spatial state machine transitions
        t_sm_start = time.perf_counter()
        events: list[SafetyEvent] = self.state_machine.update(
            timestamp=ts,
            machines=machines,
            workers=workers,
            frame=frame,
            face_verifier=self.face_verifier,
        )
        sm_ms = (time.perf_counter() - t_sm_start) * 1000

        # 5. Handle CRITICAL events requiring biometric audit, clip export, and alert dispatch
        async with self._get_db_session() as session:
            for event in events:
                if event.severity == Severity.CRITICAL and not event.alert_suppressed:
                    try:
                        await self._handle_critical_event(
                            event=event,
                            frame=frame,
                            camera_id=camera_id,
                            workers=workers,
                            session=session,
                        )
                    except Exception as exc:  # noqa: BLE001
                        logger.error(
                            "Unhandled exception during critical event handling for camera %s: %s",
                            camera_id,
                            exc,
                            exc_info=True,
                        )

        # 6. Broadcast real-time telemetry over WebSocket
        try:
            telemetry_data = {
                "event": "telemetry_frame",
                "camera_id": camera_id,
                "timestamp": ts,
                "machines_detected": len(machines),
                "workers_detected": len(workers),
                "events_count": len(events),
                "safety_events": [e.model_dump() for e in events],
            }
            await ws_manager.broadcast_json(telemetry_data)
        except Exception as exc:  # noqa: BLE001
            logger.debug("WebSocket broadcast encountered exception: %s", exc)

        self.total_frames_processed += 1
        total_ms = (time.perf_counter() - t_frame_start) * 1000

        logger.debug(
            "Frame processed on cam=%s: det=%d (machines=%d, workers=%d), events=%d, "
            "detect_ms=%.1f, sm_ms=%.1f, total_ms=%.1f",
            camera_id,
            len(detections),
            len(machines),
            len(workers),
            len(events),
            detect_ms,
            sm_ms,
            total_ms,
        )

        return events

    async def process_video(
        self,
        video_path: str,
        camera_id: str = "main",
        max_frames: int | None = None,
    ) -> dict[str, Any]:
        """Process a stored video file frame-by-frame through the safety pipeline.

        Args:
            video_path: Absolute or relative filesystem path to input video file.
            camera_id: Camera stream identifier.
            max_frames: Optional upper limit of frames to process.

        Returns:
            dict[str, Any]: Run statistics and summary metrics.
        """
        p = Path(video_path)
        if not p.is_file():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(str(p))
        if not cap.isOpened():
            raise PipelineError(f"Failed to open video file at {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0.0 or np.isnan(fps):
            fps = 30.0

        total_file_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        logger.info(
            "Processing video '%s' (camera=%s, fps=%.2f, total_frames=%d)",
            video_path,
            camera_id,
            fps,
            total_file_frames,
        )

        frames_read = 0
        total_events_generated = 0
        critical_events_count = 0
        warning_events_count = 0
        t_video_start = time.perf_counter()

        try:
            while True:
                if max_frames is not None and frames_read >= max_frames:
                    break

                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                timestamp = frames_read / fps
                events = await self.process_frame(
                    frame=frame,
                    camera_id=camera_id,
                    timestamp=timestamp,
                )

                frames_read += 1
                total_events_generated += len(events)
                for ev in events:
                    if ev.severity == Severity.CRITICAL:
                        critical_events_count += 1
                    elif ev.severity == Severity.WARNING:
                        warning_events_count += 1

        finally:
            cap.release()

        elapsed_sec = time.perf_counter() - t_video_start
        fps_achieved = frames_read / elapsed_sec if elapsed_sec > 0 else 0.0

        summary = {
            "video_path": video_path,
            "camera_id": camera_id,
            "frames_processed": frames_read,
            "total_file_frames": total_file_frames,
            "events_generated": total_events_generated,
            "critical_events": critical_events_count,
            "warning_events": warning_events_count,
            "elapsed_seconds": round(elapsed_sec, 2),
            "processing_fps": round(fps_achieved, 2),
        }

        logger.info(
            "Completed video '%s': processed %d frames in %.2fs (%.1f FPS), "
            "critical=%d, warning=%d",
            video_path,
            frames_read,
            elapsed_sec,
            fps_achieved,
            critical_events_count,
            warning_events_count,
        )
        return summary

    async def process_video_batch(
        self,
        video_paths: list[str],
        camera_id: str = "main",
    ) -> list[dict[str, Any]]:
        """Process a batch of video files sequentially with isolated error handling.

        Args:
            video_paths: List of filepaths to process.
            camera_id: Camera stream identifier.

        Returns:
            list[dict[str, Any]]: Outcome report per video file.
        """
        results: list[dict[str, Any]] = []
        logger.info("Starting batch video processing for %d files", len(video_paths))

        for path in video_paths:
            try:
                summary = await self.process_video(video_path=path, camera_id=camera_id)
                results.append(summary)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed processing video in batch '%s': %s", path, exc)
                results.append(
                    {
                        "video_path": path,
                        "camera_id": camera_id,
                        "error": str(exc),
                        "frames_processed": 0,
                    }
                )

        logger.info("Batch video processing completed for %d files", len(video_paths))
        return results
