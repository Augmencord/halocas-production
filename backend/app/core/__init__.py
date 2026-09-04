"""HALOCAS Core Module."""

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

__all__ = [
    "DetectionResult",
    "Detector",
    "DetectorError",
    "FaceEnrollmentError",
    "FaceVerificationError",
    "FaceVerifier",
    "InferenceError",
    "InvalidFrameError",
    "ModelLoadError",
    "get_logger",
    "setup_logging",
]
