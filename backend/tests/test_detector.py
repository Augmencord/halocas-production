"""Unit tests for the YOLOv8 + ByteTrack Detector engine."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.core.detector import (
    Detector,
    InferenceError,
    InvalidFrameError,
    ModelLoadError,
)


@pytest.fixture
def mock_yolo_instance() -> MagicMock:
    """Provide a mock instance of ultralytics.YOLO with default tracking stubs."""
    instance = MagicMock()
    # Stub predict for warm-up
    instance.predict.return_value = []
    # Stub track for inference
    instance.track.return_value = []
    return instance


@pytest.fixture
def sample_frame() -> np.ndarray:
    """Generate a standard test frame (100x100 RGB, uint8)."""
    return np.zeros((100, 100, 3), dtype=np.uint8)


def create_mock_track_results(
    boxes_data: list[dict[str, object]],
) -> list[MagicMock]:
    """Helper to generate mock Ultralytics tracking results.

    Args:
        boxes_data: List of dicts containing 'xyxy', 'conf', 'cls', and 'id'.

    Returns:
        list[MagicMock]: Mock Results list containing mock boxes.
    """
    mock_res = MagicMock()
    mock_boxes = MagicMock()
    mock_boxes.__len__.return_value = len(boxes_data)
    mock_boxes.xyxy = [b["xyxy"] for b in boxes_data]
    mock_boxes.conf = [b["conf"] for b in boxes_data]
    mock_boxes.cls = [b["cls"] for b in boxes_data]
    mock_boxes.id = [b.get("id") for b in boxes_data]
    mock_res.boxes = mock_boxes
    return [mock_res]


def test_detector_initialization(mock_yolo_instance: MagicMock) -> None:
    """Verify initialization loads model, sets device, and triggers warm-up."""
    with patch("app.core.detector.YOLO", return_value=mock_yolo_instance) as mock_yolo_cls:
        detector = Detector(model_path="custom_yolo.pt", device="cpu", frame_skip=1)

        mock_yolo_cls.assert_called_once_with("custom_yolo.pt")
        mock_yolo_instance.to.assert_called_once_with("cpu")
        mock_yolo_instance.predict.assert_called_once()
        assert detector.frame_skip == 1
        assert detector.conf_threshold == 0.4


def test_detector_initialization_failure() -> None:
    """Verify ModelLoadError is raised when model file loading fails."""
    with patch("app.core.detector.YOLO", side_effect=RuntimeError("Weights file corrupted")):
        with pytest.raises(ModelLoadError, match="Weights file corrupted"):
            Detector(model_path="corrupt.pt")


def test_detector_parameter_validation(mock_yolo_instance: MagicMock) -> None:
    """Verify invalid frame_skip or conf_threshold raises ValueError."""
    with patch("app.core.detector.YOLO", return_value=mock_yolo_instance):
        with pytest.raises(ValueError, match="frame_skip must be an integer >= 1"):
            Detector(frame_skip=0)

        with pytest.raises(ValueError, match="conf_threshold must be between 0.0 and 1.0"):
            Detector(conf_threshold=-0.1)

        with pytest.raises(ValueError, match="conf_threshold must be between 0.0 and 1.0"):
            Detector(conf_threshold=1.5)


def test_detect_and_track_valid_frame(
    mock_yolo_instance: MagicMock, sample_frame: np.ndarray
) -> None:
    """Verify valid detection and structured DetectionResult parsing."""
    boxes_data = [
        {
            "xyxy": [10.0, 20.0, 50.0, 100.0],
            "conf": 0.88,
            "cls": 0,  # person
            "id": 101,
        },
        {
            "xyxy": [200.0, 150.0, 450.0, 380.0],
            "conf": 0.94,
            "cls": 7,  # truck
            "id": 202,
        },
    ]
    mock_yolo_instance.track.return_value = create_mock_track_results(boxes_data)

    with patch("app.core.detector.YOLO", return_value=mock_yolo_instance):
        detector = Detector()
        results = detector.detect_and_track(sample_frame)

        assert len(results) == 2

        person_det = results[0]
        assert person_det.id == 101
        assert person_det.class_name == "person"
        assert person_det.confidence == 0.88
        assert person_det.bbox == [10.0, 20.0, 50.0, 100.0]
        assert person_det.centroid == (30.0, 60.0)

        truck_det = results[1]
        assert truck_det.id == 202
        assert truck_det.class_name == "truck"
        assert truck_det.confidence == 0.94
        assert truck_det.bbox == [200.0, 150.0, 450.0, 380.0]
        assert truck_det.centroid == (325.0, 265.0)

        mock_yolo_instance.track.assert_called_once_with(
            source=sample_frame,
            classes=[0, 7],
            tracker="bytetrack.yaml",
            persist=True,
            verbose=False,
            device="cpu",
        )


def test_detect_and_track_invalid_frames(mock_yolo_instance: MagicMock) -> None:
    """Verify InvalidFrameError is raised for None, empty, or wrong-dtype frames."""
    with patch("app.core.detector.YOLO", return_value=mock_yolo_instance):
        detector = Detector()

        # None frame
        with pytest.raises(InvalidFrameError, match="Input frame cannot be None"):
            detector.detect_and_track(None)  # type: ignore[arg-type]

        # Non-ndarray
        with pytest.raises(InvalidFrameError, match="must be a numpy.ndarray"):
            detector.detect_and_track([1, 2, 3])  # type: ignore[arg-type]

        # Empty ndarray
        with pytest.raises(InvalidFrameError, match="cannot be empty"):
            detector.detect_and_track(np.array([], dtype=np.uint8))

        # Wrong dtype (float32 instead of uint8)
        float_frame = np.zeros((50, 50, 3), dtype=np.float32)
        with pytest.raises(InvalidFrameError, match="must have dtype uint8"):
            detector.detect_and_track(float_frame)


def test_confidence_filtering(
    mock_yolo_instance: MagicMock, sample_frame: np.ndarray
) -> None:
    """Verify detections below confidence threshold are discarded."""
    boxes_data = [
        {"xyxy": [10.0, 10.0, 20.0, 20.0], "conf": 0.85, "cls": 0, "id": 1},
        {"xyxy": [30.0, 30.0, 40.0, 40.0], "conf": 0.40, "cls": 0, "id": 2},
        {"xyxy": [50.0, 50.0, 60.0, 60.0], "conf": 0.39, "cls": 7, "id": 3},
        {"xyxy": [70.0, 70.0, 80.0, 80.0], "conf": 0.15, "cls": 7, "id": 4},
    ]
    mock_yolo_instance.track.return_value = create_mock_track_results(boxes_data)

    with patch("app.core.detector.YOLO", return_value=mock_yolo_instance):
        detector = Detector(conf_threshold=0.40)
        results = detector.detect_and_track(sample_frame)

        # Only confidences >= 0.40 should remain
        assert len(results) == 2
        assert [r.id for r in results] == [1, 2]


def test_frame_skipping_behavior(
    mock_yolo_instance: MagicMock, sample_frame: np.ndarray
) -> None:
    """Verify frame skipping processes every Nth frame and caches intermediate results."""
    boxes_data = [
        {"xyxy": [5.0, 5.0, 15.0, 15.0], "conf": 0.90, "cls": 0, "id": 1},
    ]
    mock_yolo_instance.track.return_value = create_mock_track_results(boxes_data)

    with patch("app.core.detector.YOLO", return_value=mock_yolo_instance):
        detector = Detector(frame_skip=3)

        # Frame 1: Should run tracking
        res1 = detector.detect_and_track(sample_frame)
        assert len(res1) == 1
        assert mock_yolo_instance.track.call_count == 1

        # Frame 2: Should be skipped (cached return)
        res2 = detector.detect_and_track(sample_frame)
        assert len(res2) == 1
        assert mock_yolo_instance.track.call_count == 1  # Not called again

        # Frame 3: Should be skipped (cached return)
        res3 = detector.detect_and_track(sample_frame)
        assert len(res3) == 1
        assert mock_yolo_instance.track.call_count == 1  # Not called again

        # Frame 4: Next cycle (4 % 3 == 1) -> Should run tracking again!
        res4 = detector.detect_and_track(sample_frame)
        assert len(res4) == 1
        assert mock_yolo_instance.track.call_count == 2


def test_inference_error_handling(
    mock_yolo_instance: MagicMock, sample_frame: np.ndarray
) -> None:
    """Verify InferenceError is raised when model.track raises an exception."""
    mock_yolo_instance.track.side_effect = RuntimeError("Tracking backend failure")

    with patch("app.core.detector.YOLO", return_value=mock_yolo_instance):
        detector = Detector()
        with pytest.raises(InferenceError, match="Tracking inference failed"):
            detector.detect_and_track(sample_frame)


def test_detector_reset(mock_yolo_instance: MagicMock, sample_frame: np.ndarray) -> None:
    """Verify detector reset clears frame counts and cached tracking results."""
    boxes_data = [
        {"xyxy": [0.0, 0.0, 10.0, 10.0], "conf": 0.95, "cls": 0, "id": 1},
    ]
    mock_yolo_instance.track.return_value = create_mock_track_results(boxes_data)

    with patch("app.core.detector.YOLO", return_value=mock_yolo_instance):
        detector = Detector(frame_skip=2)
        detector.detect_and_track(sample_frame)
        assert detector._frame_count == 1
        assert len(detector._last_results) == 1

        detector.reset()
        assert detector._frame_count == 0
        assert len(detector._last_results) == 0
