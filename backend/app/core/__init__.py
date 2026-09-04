"""HALOCAS Core Module."""

from app.core.buffer import (
    BufferError,
    BufferManager,
    CameraNotFoundError,
    ClipExportError,
    FrameEntry,
    RollingFrameBuffer,
    burn_timestamp_overlay,
)
from app.core.detector import (
    DetectionResult,
    Detector,
    DetectorError,
    InferenceError,
    InvalidFrameError,
    ModelLoadError,
)
from app.core.face_verifier import (
    FaceEnrollmentError,
    FaceVerificationError,
    FaceVerifier,
)
from app.core.logging import get_logger, setup_logging
from app.core.pipeline import (
    PipelineError,
    PipelineInputError,
    PipelineOrchestrator,
)
from app.core.state_machine import (
    SafetyEvent,
    SafetyStateMachine,
    Severity,
)

__all__ = [
    "BufferError",
    "BufferManager",
    "CameraNotFoundError",
    "ClipExportError",
    "DetectionResult",
    "Detector",
    "DetectorError",
    "FaceEnrollmentError",
    "FaceVerificationError",
    "FaceVerifier",
    "FrameEntry",
    "InferenceError",
    "InvalidFrameError",
    "ModelLoadError",
    "PipelineError",
    "PipelineInputError",
    "PipelineOrchestrator",
    "RollingFrameBuffer",
    "SafetyEvent",
    "SafetyStateMachine",
    "Severity",
    "burn_timestamp_overlay",
    "get_logger",
    "setup_logging",
]
