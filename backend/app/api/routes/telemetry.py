"""Real-time WebSocket telemetry event streaming and live MJPEG video feeds."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Annotated

import cv2
import numpy as np
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.api.deps import get_buffer_manager
from app.core.buffer import BufferManager, burn_timestamp_overlay
from app.core.logging import get_logger
from app.core.telemetry import ConnectionManager, manager

logger = get_logger("halocas.api.telemetry")

router = APIRouter(tags=["Telemetry & Streaming"])

__all__ = ["ConnectionManager", "manager", "router"]


@router.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint broadcasting real-time proximity incidents and equipment telemetry."""
    await manager.connect(websocket)
    try:
        # Send initial connection handshake
        await websocket.send_json(
            {
                "event": "connected",
                "timestamp": datetime.now(UTC).isoformat(),
                "message": "Connected to HALOCAS real-time safety telemetry stream",
            }
        )

        while True:
            # Receive client ping or heartbeat commands
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json(
                    {
                        "event": "pong",
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                )
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as exc:
        logger.warning("WebSocket client connection error: %s", exc)
        await manager.disconnect(websocket)


def _generate_synthetic_test_pattern(camera_id: str) -> np.ndarray:
    """Render a 640x480 test pattern frame when no video stream is active."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:] = (20, 24, 32)  # Dark slate background

    # Crosshair grid
    cv2.line(frame, (0, 240), (640, 240), (45, 55, 72), 1)
    cv2.line(frame, (320, 0), (320, 480), (45, 55, 72), 1)

    # Telemetry text
    cv2.putText(
        frame,
        f"CAMERA: {camera_id.upper()}",
        (40, 200),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 240, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        "STANDBY - STREAM ONLINE",
        (40, 250),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (160, 174, 192),
        1,
        cv2.LINE_AA,
    )

    return burn_timestamp_overlay(frame, datetime.now(UTC).timestamp(), camera_id)


async def mjpeg_frame_generator(
    camera_id: str, buffer_manager: BufferManager
) -> AsyncGenerator[bytes, None]:
    """Asynchronously generate multipart MJPEG frames from the camera buffer."""
    try:
        while True:
            buf = buffer_manager.get_buffer(camera_id)
            frame: np.ndarray | None = None

            if buf and not buf.is_empty():
                frames = buf.get_frames(duration_sec=0.1)
                if frames:
                    frame = frames[-1]

            if frame is None:
                frame = _generate_synthetic_test_pattern(camera_id)

            # Encode frame to JPEG format
            success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if success:
                jpg_bytes = buffer.tobytes()
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(jpg_bytes)).encode() + b"\r\n\r\n"
                    + jpg_bytes
                    + b"\r\n"
                )

            # ~10 FPS for preview stream
            await asyncio.sleep(0.1)
    except (asyncio.CancelledError, GeneratorExit):
        return


@router.get(
    "/stream/{camera_id}",
    summary="Live MJPEG video preview stream for a specific camera",
    responses={200: {"content": {"multipart/x-mixed-replace": {}}}},
)
async def get_live_camera_stream(
    camera_id: str,
    buffer_manager: Annotated[BufferManager, Depends(get_buffer_manager)],
) -> StreamingResponse:
    """Stream live camera feed using standard multipart/x-mixed-replace MJPEG format."""
    return StreamingResponse(
        mjpeg_frame_generator(camera_id, buffer_manager),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
