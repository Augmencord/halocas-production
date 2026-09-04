"""Real-time computer vision detector and tracker for HALOCAS.

Utilizes YOLOv8 and ByteTrack to identify and continuously track mine personnel
(class 0: person) and heavy mining machinery (class 7: truck) within active mining zones.
Provides configurable confidence thresholding, frame-skipping optimizations,
and high-resolution latency benchmarking.
"""

import time

import numpy as np
from pydantic import BaseModel, Field
from ultralytics import YOLO

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class DetectorError(Exception):
    """Base exception for computer vision detector errors."""


class ModelLoadError(DetectorError):
    """Raised when the YOLO tracking model fails to initialize or load weights."""


class InvalidFrameError(DetectorError, ValueError):
    """Raised when an input frame is invalid, empty, or has an unsupported dtype."""


class InferenceError(DetectorError, RuntimeError):
    """Raised when model inference or tracking pipeline execution fails."""


class DetectionResult(BaseModel):
    """Structured detection result for identified mine personnel or equipment."""

    id: int | None = Field(
        default=None,
        description="Unique ByteTrack tracker identifier persistently assigned to the entity",
    )
    class_name: str = Field(
        ...,
        description="Identified entity class designation ('person' or 'truck')",
    )
    bbox: list[float] = Field(
        ...,
        description="Spatial bounding box [x1, y1, x2, y2] in pixel coordinates",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Neural detection confidence score in range [0.0, 1.0]",
    )

    @property
    def centroid(self) -> tuple[float, float]:
        """Compute the bottom-center ground contact point of the bounding box."""
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


class Detector:
    """High-throughput vision detector with ByteTrack tracking and frame-skipping."""

    CLASS_NAMES: dict[int, str] = {
        0: "person",
        7: "truck",
    }

    def __init__(
        self,
        model_path: str | None = None,
        conf_threshold: float = 0.4,
        frame_skip: int = 1,
        device: str = "cpu",
    ) -> None:
        """Initialize the YOLOv8 detector and run warm-up inference.

        Args:
            model_path: Path or identifier for YOLOv8 weights. Defaults to config setting.
            conf_threshold: Minimum confidence score required to retain detection (>= 0.4).
            frame_skip: Process every Nth frame; skipped frames return cached detections.
            device: Target hardware accelerator ('cpu', 'cuda', 'mps').

        Raises:
            ValueError: If frame_skip < 1 or conf_threshold is not in [0.0, 1.0].
            ModelLoadError: If YOLO weights fail to load.
        """
        settings = get_settings()
        self.model_path = model_path or settings.YOLO_MODEL_PATH

        if conf_threshold < 0.0 or conf_threshold > 1.0:
            raise ValueError(f"conf_threshold must be between 0.0 and 1.0, got {conf_threshold}")
        self.conf_threshold = conf_threshold

        if frame_skip < 1:
            raise ValueError(f"frame_skip must be an integer >= 1, got {frame_skip}")
        self.frame_skip = frame_skip
        self.device = device

        self._frame_count: int = 0
        self._last_results: list[DetectionResult] = []

        try:
            logger.info("Loading YOLO model from %s on device=%s", self.model_path, self.device)
            self.model: YOLO = YOLO(self.model_path)
            if hasattr(self.model, "to"):
                self.model.to(self.device)
            logger.info("YOLO model loaded successfully from %s", self.model_path)
        except Exception as exc:
            logger.error(
                "Failed to initialize YOLO model from %s: %s",
                self.model_path,
                exc,
                exc_info=True,
            )
            raise ModelLoadError(
                f"Failed to load YOLO model from {self.model_path}: {exc}"
            ) from exc

        # Execute warm-up inference on a blank frame
        self._warmup()

    def _warmup(self) -> None:
        """Execute inference on a blank frame to prime network weights and CUDA kernels."""
        try:
            logger.info("Executing detector warm-up on a blank frame")
            blank_frame = np.zeros((640, 640, 3), dtype=np.uint8)
            start_time = time.perf_counter()
            self.model.predict(
                source=blank_frame,
                classes=[0, 7],
                verbose=False,
                device=self.device,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.info("Detector warm-up completed in %.2f ms", elapsed_ms)
        except Exception as exc:
            logger.warning("Detector warm-up encountered an exception: %s", exc)

    def detect_and_track(self, frame: np.ndarray) -> list[DetectionResult]:
        """Detect and track mine personnel and equipment in the input video frame.

        Args:
            frame: Video frame as a uint8 NumPy ndarray (H, W, C) or (H, W).

        Returns:
            List[DetectionResult]: List of validated detections with assigned track IDs.

        Raises:
            InvalidFrameError: If frame is None, non-ndarray, empty, or has wrong dtype.
            InferenceError: If model tracking execution encounters an unexpected failure.
        """
        # 1. Input Validation
        if frame is None:
            logger.error("Frame validation failed: frame is None")
            raise InvalidFrameError("Input frame cannot be None")

        if not isinstance(frame, np.ndarray):
            logger.error("Frame validation failed: expected np.ndarray, got %s", type(frame))
            raise InvalidFrameError(f"Input frame must be a numpy.ndarray, got {type(frame)}")

        if frame.size == 0 or frame.ndim not in (2, 3):
            shape_repr = getattr(frame, "shape", None)
            logger.error("Frame validation failed: empty or invalid shape (%s)", shape_repr)
            raise InvalidFrameError(f"Input frame cannot be empty or invalid shape: {shape_repr}")

        if frame.dtype != np.uint8:
            logger.error("Frame validation failed: expected uint8 dtype, got %s", frame.dtype)
            raise InvalidFrameError(f"Input frame must have dtype uint8, got {frame.dtype}")

        self._frame_count += 1

        # 2. Frame Skipping
        if self.frame_skip > 1 and (self._frame_count % self.frame_skip != 1):
            logger.debug(
                "Skipping inference for frame %d; returning %d cached detections",
                self._frame_count,
                len(self._last_results),
            )
            return list(self._last_results)

        # 3. Model Tracking Execution
        start_time = time.perf_counter()
        try:
            results = self.model.track(
                source=frame,
                classes=[0, 7],
                tracker="bytetrack.yaml",
                persist=True,
                verbose=False,
                device=self.device,
            )
        except Exception as exc:
            logger.error(
                "Model tracking failed on frame %d: %s",
                self._frame_count,
                exc,
                exc_info=True,
            )
            raise InferenceError(
                f"Tracking inference failed on frame {self._frame_count}: {exc}"
            ) from exc

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # 4. Parse Detections and Filter by Confidence
        detections: list[DetectionResult] = []
        if results and len(results) > 0:
            first_result = results[0]
            boxes = getattr(first_result, "boxes", None)
            if boxes is not None and len(boxes) > 0:
                xyxy = boxes.xyxy
                conf = boxes.conf
                cls = boxes.cls
                track_ids = getattr(boxes, "id", None)

                for i in range(len(boxes)):
                    c_raw = conf[i]
                    c_val = float(c_raw) if hasattr(c_raw, "__float__") else float(c_raw.item())
                    if c_val < self.conf_threshold:
                        continue

                    raw_box = xyxy[i]
                    coords_list: list[float] = [
                        float(c)
                        for c in (raw_box.tolist() if hasattr(raw_box, "tolist") else raw_box)
                    ]

                    raw_cls = cls[i]
                    cls_id = int(raw_cls) if hasattr(raw_cls, "__int__") else int(raw_cls.item())
                    class_name = self.CLASS_NAMES.get(cls_id, f"class_{cls_id}")

                    track_id: int | None = None
                    if track_ids is not None and track_ids[i] is not None:
                        t_item = track_ids[i]
                        track_id = (
                            int(t_item) if hasattr(t_item, "__int__") else int(t_item.item())
                        )

                    detections.append(
                        DetectionResult(
                            id=track_id,
                            class_name=class_name,
                            bbox=coords_list,
                            confidence=round(c_val, 4),
                        )
                    )

        # 5. Cache and Log Performance
        self._last_results = detections

        logger.info(
            "Inference for frame %d completed in %.2f ms (%d detections)",
            self._frame_count,
            elapsed_ms,
            len(detections),
            extra={
                "frame_count": self._frame_count,
                "inference_ms": round(elapsed_ms, 2),
                "detections_count": len(detections),
            },
        )

        return detections

    def reset(self) -> None:
        """Reset frame counter and clear cached tracking state."""
        self._frame_count = 0
        self._last_results.clear()
