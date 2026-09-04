"""Production DeepFace biometric facial verification engine for HALOCAS.

Replaces prototype color histogram approaches with 512-dimensional Facenet512
deep feature embeddings and RetinaFace detection backends. Supports real-time worker
biometric identification, head-region spatial cropping, industrial noise tolerance
(helmets, dust, occlusion), and new worker facial enrollment.
"""

import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class _LazyDeepFace:
    """Lazy loader proxy for DeepFace to prevent eager TensorFlow initialization on module import."""

    _module: Any = None

    def _get_module(self) -> Any:
        if self._module is None:
            import deepface.DeepFace as df_mod

            self._module = df_mod
        return self._module

    def build_model(self, *args: Any, **kwargs: Any) -> Any:
        return self._get_module().build_model(*args, **kwargs)

    def represent(self, *args: Any, **kwargs: Any) -> Any:
        return self._get_module().represent(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get_module(), name)


DeepFace = _LazyDeepFace()


class FaceVerificationError(Exception):
    """Base exception for face verification and biometric matching failures."""


class FaceEnrollmentError(FaceVerificationError, ValueError):
    """Raised when facial enrollment fails due to missing faces or invalid files."""


class FaceVerifier:
    """Biometric facial verification and enrollment engine utilizing DeepFace."""

    def __init__(
        self,
        model_name: str | None = None,
        detector_backend: str = "retinaface",
        similarity_threshold: float = 0.40,
        warmup: bool = False,
    ) -> None:
        """Initialize the DeepFace facial verifier.

        Args:
            model_name: Face recognition model identifier (defaults to config DEEPFACE_MODEL).
            detector_backend: Detection backend architecture ('retinaface', 'opencv', etc.).
            similarity_threshold: Minimum cosine similarity score required for positive verification.
            warmup: If True, primes the recognition model on initialization.
        """
        settings = get_settings()
        self.model_name: str = model_name or settings.DEEPFACE_MODEL
        self.detector_backend: str = detector_backend
        self.similarity_threshold: float = similarity_threshold

        logger.info(
            "Initializing FaceVerifier with model=%s, detector=%s, threshold=%.2f",
            self.model_name,
            self.detector_backend,
            self.similarity_threshold,
        )

        if warmup:
            self._warmup()

    def _warmup(self) -> None:
        """Pre-cache neural weights and prime computational graphs."""
        if os.getenv("SKIP_FACE_WARMUP", "0") == "1":
            logger.info("FaceVerifier warmup deferred (container memory optimization active)")
            return
        try:
            logger.info("Executing FaceVerifier model pre-caching for %s", self.model_name)
            DeepFace.build_model(model_name=self.model_name)
            logger.info("FaceVerifier model pre-cached successfully")
        except Exception as exc:
            logger.warning("FaceVerifier warmup was skipped or encountered non-fatal notice: %s", exc)

    def extract_embedding(self, face_crop: np.ndarray) -> np.ndarray | None:
        """Extract a 512-dimensional float32 feature vector from a cropped facial image.

        Args:
            face_crop: BGR image matrix representing candidate facial area.

        Returns:
            Optional[np.ndarray]: 512-d float32 embedding, or None if no face is detected.
        """
        if face_crop is None or not isinstance(face_crop, np.ndarray) or face_crop.size == 0:
            logger.debug("Face extraction skipped: invalid or empty frame crop")
            return None

        try:
            # DeepFace expects BGR or RGB numpy array.
            # In industrial mining environments, lack of face detection is common (helmets/dust).
            results = DeepFace.represent(
                img_path=face_crop,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=True,
                align=True,
            )

            if not results or len(results) == 0:
                return None

            first_result = results[0]
            raw_embedding = first_result.get("embedding")
            if raw_embedding is None:
                return None

            embedding = np.array(raw_embedding, dtype=np.float32)
            return embedding

        except ValueError as val_err:
            # Expected in mining environments when face is turned away, occluded, or helmeted
            logger.debug("No face detected in crop (expected under occlusion/helmets): %s", val_err)
            return None
        except Exception as exc:
            logger.error("Unexpected error during DeepFace embedding extraction: %s", exc, exc_info=True)
            return None

    @staticmethod
    def compute_cosine_similarity(
        emb1: np.ndarray | Sequence[float] | None,
        emb2: np.ndarray | Sequence[float] | None,
    ) -> float:
        """Compute cosine similarity between two feature vectors in [-1.0, 1.0].

        Args:
            emb1: First feature embedding vector.
            emb2: Second feature embedding vector.

        Returns:
            float: Cosine similarity score, or 0.0 if either vector is null/degenerate.
        """
        if emb1 is None or emb2 is None:
            return 0.0

        vec1 = np.asarray(emb1, dtype=np.float32).flatten()
        vec2 = np.asarray(emb2, dtype=np.float32).flatten()

        if vec1.size == 0 or vec2.size == 0:
            return 0.0

        norm1 = float(np.linalg.norm(vec1))
        norm2 = float(np.linalg.norm(vec2))

        if norm1 == 0.0 or norm2 == 0.0 or np.isnan(norm1) or np.isnan(norm2):
            return 0.0

        dot_product = float(np.dot(vec1, vec2))
        similarity = dot_product / (norm1 * norm2)

        # Numerical clamping to strictly [-1.0, 1.0]
        return float(np.clip(similarity, -1.0, 1.0))

    def verify(
        self,
        frame: np.ndarray,
        bbox: list[float] | tuple[float, float, float, float],
        database_workers: list[dict[str, Any]],
        threshold: float | None = None,
    ) -> dict[str, Any] | None:
        """Verify the identity of a detected person against authorized database personnel.

        Crops the upper 35% of the person's bounding box (head region), applies 20% spatial
        padding, extracts 512-d embeddings, and evaluates cosine similarity against all candidates.

        Args:
            frame: Full video frame (NumPy ndarray BGR).
            bbox: Person spatial bounding box [x1, y1, x2, y2].
            database_workers: List of worker records with stored embeddings.
            threshold: Custom similarity cutoff, or default configured threshold.

        Returns:
            Optional[Dict[str, Any]]: Best matching worker record including confidence score,
                                      or None if no candidate satisfies threshold.
        """
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return None

        if not bbox or len(bbox) < 4:
            return None

        eval_threshold = self.similarity_threshold if threshold is None else threshold

        try:
            x1_f, y1_f, x2_f, y2_f = bbox[:4]
            x1, y1, x2, y2 = int(x1_f), int(y1_f), int(x2_f), int(y2_f)

            frame_h, frame_w = frame.shape[:2]
            if x2 <= x1 or y2 <= y1 or x1 >= frame_w or y1 >= frame_h:
                return None

            # 1. Isolate upper 35% of bounding box (head region)
            box_w = x2 - x1
            box_h = y2 - y1
            head_h = box_h * 0.35
            head_y2 = y1 + head_h

            # 2. Add 20% padding around head region for context
            pad_x = int(box_w * 0.20)
            pad_y = int(head_h * 0.20)

            crop_x1 = max(0, x1 - pad_x)
            crop_y1 = max(0, y1 - pad_y)
            crop_x2 = min(frame_w, x2 + pad_x)
            crop_y2 = min(frame_h, int(head_y2 + pad_y))

            if crop_x2 <= crop_x1 or crop_y2 <= crop_y1:
                return None

            head_crop = frame[crop_y1:crop_y2, crop_x1:crop_x2]

            # 3. Extract 512-d facial embedding
            query_embedding = self.extract_embedding(head_crop)
            if query_embedding is None:
                return None

            # 4. Compare against candidate database workers
            best_match: dict[str, Any] | None = None
            highest_sim: float = -1.0

            for worker in database_workers:
                candidate_emb = worker.get("face_embedding")
                if candidate_emb is None:
                    candidate_emb = worker.get("embedding")

                if candidate_emb is None:
                    continue

                sim = self.compute_cosine_similarity(query_embedding, candidate_emb)
                if sim > highest_sim:
                    highest_sim = sim
                    best_match = worker

            # 5. Threshold enforcement
            if highest_sim >= eval_threshold and best_match is not None:
                result = dict(best_match)
                result["confidence"] = round(highest_sim, 4)
                result["match_confidence"] = round(highest_sim, 4)

                logger.info(
                    "Worker biometric match identified: %s (role=%s, confidence=%.4f)",
                    result.get("name"),
                    result.get("role"),
                    highest_sim,
                    extra={
                        "worker_id": result.get("id"),
                        "worker_name": result.get("name"),
                        "similarity": round(highest_sim, 4),
                        "threshold": eval_threshold,
                    },
                )
                return result

        except Exception as exc:
            logger.error("Error during facial verification pipeline: %s", exc, exc_info=True)

        return None

    def enroll_face(self, image_path: str) -> np.ndarray:
        """Extract a reference 512-d embedding from a high-resolution worker portrait.

        Args:
            image_path: Filesystem path to worker identification photo.

        Returns:
            np.ndarray: 512-dimensional float32 feature embedding vector.

        Raises:
            FaceEnrollmentError: If the image file is missing, unreadable, or contains no detectable face.
        """
        path_obj = Path(image_path)
        if not path_obj.is_file() or not os.access(image_path, os.R_OK):
            raise FaceEnrollmentError(f"Enrollment image path does not exist or is unreadable: {image_path}")

        img = cv2.imread(image_path)
        if img is None or img.size == 0:
            raise FaceEnrollmentError(f"Could not decode image at path: {image_path}")

        try:
            logger.info("Enrolling worker face from image: %s", image_path)
            results = DeepFace.represent(
                img_path=img,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=True,
                align=True,
            )

            if not results or len(results) == 0:
                raise FaceEnrollmentError(f"No faces detected in enrollment photo: {image_path}")

            first_rep = results[0]
            raw_emb = first_rep.get("embedding")
            if raw_emb is None:
                raise FaceEnrollmentError(f"Failed to generate embedding from photo: {image_path}")

            embedding = np.array(raw_emb, dtype=np.float32)
            logger.info("Successfully enrolled worker face with %d dimensions", embedding.size)
            return embedding

        except FaceEnrollmentError:
            raise
        except ValueError as val_err:
            raise FaceEnrollmentError(f"No face detected during enrollment: {val_err}") from val_err
        except Exception as exc:
            raise FaceEnrollmentError(f"Facial enrollment failed for {image_path}: {exc}") from exc
