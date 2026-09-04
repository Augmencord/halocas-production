"""Unit tests for the DeepFace FaceVerifier biometric engine."""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from app.core.face_verifier import FaceEnrollmentError, FaceVerifier


@pytest.fixture
def dummy_embedding() -> np.ndarray:
    """Generate a normalized 512-d unit vector."""
    vec = np.ones(512, dtype=np.float32)
    return vec / np.linalg.norm(vec)


@pytest.fixture
def synthetic_face_crop() -> np.ndarray:
    """Generate a dummy synthetic RGB/BGR face crop."""
    return np.full((120, 120, 3), fill_value=128, dtype=np.uint8)


def test_cosine_similarity_computation(dummy_embedding: np.ndarray) -> None:
    """Verify mathematical correctness of cosine similarity calculations."""
    verifier = FaceVerifier(warmup=False)

    # 1. Identical vectors
    sim_identical = verifier.compute_cosine_similarity(dummy_embedding, dummy_embedding)
    assert np.isclose(sim_identical, 1.0, atol=1e-4)

    # 2. Orthogonal vectors
    v1 = np.zeros(512, dtype=np.float32)
    v1[0] = 1.0
    v2 = np.zeros(512, dtype=np.float32)
    v2[1] = 1.0
    sim_orthogonal = verifier.compute_cosine_similarity(v1, v2)
    assert np.isclose(sim_orthogonal, 0.0, atol=1e-4)

    # 3. Opposite vectors
    sim_opposite = verifier.compute_cosine_similarity(v1, -v1)
    assert np.isclose(sim_opposite, -1.0, atol=1e-4)

    # 4. Edge cases (None, empty, zero norms)
    assert verifier.compute_cosine_similarity(None, v1) == 0.0
    assert verifier.compute_cosine_similarity(v1, None) == 0.0
    assert verifier.compute_cosine_similarity(np.zeros(512), v1) == 0.0
    assert verifier.compute_cosine_similarity(np.array([]), v1) == 0.0


def test_extract_embedding_success(synthetic_face_crop: np.ndarray, dummy_embedding: np.ndarray) -> None:
    """Verify embedding extraction returns 512-d float32 array when face is detected."""
    verifier = FaceVerifier(warmup=False)

    mock_rep_return = [{"embedding": dummy_embedding.tolist()}]
    with patch("app.core.face_verifier.DeepFace.represent", return_value=mock_rep_return) as mock_rep:
        embedding = verifier.extract_embedding(synthetic_face_crop)

        assert embedding is not None
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (512,)
        assert embedding.dtype == np.float32
        assert np.allclose(embedding, dummy_embedding)
        mock_rep.assert_called_once()


def test_extract_embedding_invalid_inputs() -> None:
    """Verify extract_embedding safely returns None on empty or invalid inputs."""
    verifier = FaceVerifier(warmup=False)

    assert verifier.extract_embedding(None) is None  # type: ignore[arg-type]
    assert verifier.extract_embedding(np.array([], dtype=np.uint8)) is None
    assert verifier.extract_embedding("not an image") is None  # type: ignore[arg-type]


def test_extract_embedding_no_face_detected(synthetic_face_crop: np.ndarray) -> None:
    """Verify ValueError from DeepFace (face not detected) is handled gracefully."""
    verifier = FaceVerifier(warmup=False)

    with patch("app.core.face_verifier.DeepFace.represent", side_effect=ValueError("Face could not be detected")):
        result = verifier.extract_embedding(synthetic_face_crop)
        assert result is None


def test_extract_embedding_unexpected_exception(synthetic_face_crop: np.ndarray) -> None:
    """Verify unexpected runtime errors return None without crashing."""
    verifier = FaceVerifier(warmup=False)

    with patch("app.core.face_verifier.DeepFace.represent", side_effect=RuntimeError("GPU OOM")):
        result = verifier.extract_embedding(synthetic_face_crop)
        assert result is None


def test_verify_matching_worker(dummy_embedding: np.ndarray) -> None:
    """Verify full verification pipeline correctly matches database worker above threshold."""
    verifier = FaceVerifier(similarity_threshold=0.40, warmup=False)
    frame = np.full((600, 600, 3), fill_value=128, dtype=np.uint8)
    bbox = [100.0, 100.0, 200.0, 400.0]

    # Database candidates
    orthogonal_emb = np.zeros(512, dtype=np.float32)
    orthogonal_emb[5] = 1.0

    database_workers = [
        {"id": 1, "name": "Wrong Person", "role": "General Worker", "embedding": orthogonal_emb},
        {"id": 2, "name": "Marcus Vance", "role": "Authorized Mechanic", "face_embedding": dummy_embedding},
    ]

    mock_rep_return = [{"embedding": dummy_embedding.tolist()}]
    with patch("app.core.face_verifier.DeepFace.represent", return_value=mock_rep_return):
        match = verifier.verify(frame, bbox, database_workers)

        assert match is not None
        assert match["id"] == 2
        assert match["name"] == "Marcus Vance"
        assert match["role"] == "Authorized Mechanic"
        assert match["confidence"] >= 0.99
        assert match["match_confidence"] >= 0.99


def test_verify_non_matching_worker(dummy_embedding: np.ndarray) -> None:
    """Verify verification returns None when similarity is below threshold."""
    verifier = FaceVerifier(similarity_threshold=0.85, warmup=False)
    frame = np.full((600, 600, 3), fill_value=128, dtype=np.uint8)
    bbox = [100.0, 100.0, 200.0, 400.0]

    # Database worker has orthogonal vector -> similarity = 0.0
    orthogonal_emb = np.zeros(512, dtype=np.float32)
    orthogonal_emb[10] = 1.0
    database_workers = [
        {"id": 1, "name": "Unrelated Worker", "role": "Driller", "embedding": orthogonal_emb},
    ]

    mock_rep_return = [{"embedding": dummy_embedding.tolist()}]
    with patch("app.core.face_verifier.DeepFace.represent", return_value=mock_rep_return):
        match = verifier.verify(frame, bbox, database_workers)
        assert match is None


def test_verify_no_face_in_crop() -> None:
    """Verify verify returns None when no face is found in upper crop."""
    verifier = FaceVerifier(warmup=False)
    frame = np.full((600, 600, 3), fill_value=128, dtype=np.uint8)
    bbox = [50.0, 50.0, 150.0, 350.0]
    database_workers = [{"id": 1, "name": "Worker", "embedding": np.ones(512)}]

    with patch("app.core.face_verifier.DeepFace.represent", side_effect=ValueError("No face detected")):
        match = verifier.verify(frame, bbox, database_workers)
        assert match is None


def test_enroll_face_success(tmp_path: Path, dummy_embedding: np.ndarray) -> None:
    """Verify enroll_face reads a valid photo and outputs a 512-d embedding."""
    verifier = FaceVerifier(warmup=False)

    # Create dummy image file
    img_file = tmp_path / "worker_portrait.jpg"
    img_file.write_bytes(b"dummy_image_data")

    mock_img = np.full((200, 200, 3), fill_value=200, dtype=np.uint8)
    mock_rep_return = [{"embedding": dummy_embedding.tolist()}]

    with (
        patch("app.core.face_verifier.cv2.imread", return_value=mock_img),
        patch("app.core.face_verifier.DeepFace.represent", return_value=mock_rep_return) as mock_rep,
    ):
        embedding = verifier.enroll_face(str(img_file))

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (512,)
        assert np.allclose(embedding, dummy_embedding)
        mock_rep.assert_called_once()


def test_enroll_face_failures(tmp_path: Path) -> None:
    """Verify FaceEnrollmentError on missing files, corrupt images, and detection failures."""
    verifier = FaceVerifier(warmup=False)

    # 1. Non-existent file
    with pytest.raises(FaceEnrollmentError, match="does not exist"):
        verifier.enroll_face("/path/to/missing_file.jpg")

    # 2. Corrupted image file
    img_file = tmp_path / "corrupt.jpg"
    img_file.write_bytes(b"not_a_valid_image")

    with patch("app.core.face_verifier.cv2.imread", return_value=None):
        with pytest.raises(FaceEnrollmentError, match="Could not decode image"):
            verifier.enroll_face(str(img_file))

    # 3. No face detected in portrait
    mock_img = np.zeros((100, 100, 3), dtype=np.uint8)
    with (
        patch("app.core.face_verifier.cv2.imread", return_value=mock_img),
        patch("app.core.face_verifier.DeepFace.represent", side_effect=ValueError("No face found")),
    ):
        with pytest.raises(FaceEnrollmentError, match="No face detected"):
            verifier.enroll_face(str(img_file))


def test_face_verifier_warmup() -> None:
    """Verify warmup triggers DeepFace model building."""
    with patch("app.core.face_verifier.DeepFace.build_model") as mock_build:
        FaceVerifier(model_name="Facenet512", warmup=True)
        mock_build.assert_called_once_with(model_name="Facenet512")
