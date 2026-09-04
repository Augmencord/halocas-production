#!/usr/bin/env python3
"""Biometric Face Extraction and Embedding Pipeline for HALOCAS Demo Videos.

Processes downloaded industrial/construction demonstration videos, samples
frames every 30 frames (1 per second), detects facial candidates using DeepFace
with RetinaFace backend, extracts 512-dimensional Facenet512 biometric embeddings,
deduplicates across frames, and compiles a comprehensive JSON manifest.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from deepface import DeepFace

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("extract_faces")


@dataclass
class FaceRecord:
    """Individual extracted biometric face record for JSON manifest."""

    face_id: str
    source_video: str
    frame_number: int
    timestamp_seconds: float
    embedding_path: str
    crop_path: str
    confidence: float


def compute_cosine_similarity(
    vec1: np.ndarray | None,
    vec2: np.ndarray | None,
) -> float:
    """Compute cosine similarity between two feature vectors in [-1.0, 1.0].

    Args:
        vec1: First feature embedding vector.
        vec2: Second feature embedding vector.

    Returns:
        float: Cosine similarity score, or 0.0 if either vector is degenerate.
    """
    if vec1 is None or vec2 is None:
        return 0.0

    v1 = np.asarray(vec1, dtype=np.float32).flatten()
    v2 = np.asarray(vec2, dtype=np.float32).flatten()

    if v1.size == 0 or v2.size == 0:
        return 0.0

    norm1 = float(np.linalg.norm(v1))
    norm2 = float(np.linalg.norm(v2))

    if norm1 == 0.0 or norm2 == 0.0 or np.isnan(norm1) or np.isnan(norm2):
        return 0.0

    similarity = float(np.dot(v1, v2) / (norm1 * norm2))
    return float(np.clip(similarity, -1.0, 1.0))


def extract_face_candidates_from_frame(
    frame: np.ndarray,
    detector_backend: str = "retinaface",
    min_confidence: float = 0.70,
) -> list[dict[str, Any]]:
    """Detect and locate human faces in an individual video frame.

    Args:
        frame: Full frame image matrix (BGR numpy array).
        detector_backend: DeepFace detection backend.
        min_confidence: Minimum detector confidence score.

    Returns:
        List of dictionaries containing bounding box crops and metadata.
    """
    if frame is None or frame.size == 0:
        return []

    frame_h, frame_w = frame.shape[:2]
    candidates: list[dict[str, Any]] = []

    try:
        # DeepFace extract_faces returns list of detected face objects
        detections = DeepFace.extract_faces(
            img_path=frame,
            detector_backend=detector_backend,
            enforce_detection=False,
            align=True,
        )

        for det in detections:
            conf = float(det.get("confidence", 0.0))
            facial_area = det.get("facial_area", {})
            fx = int(facial_area.get("x", 0))
            fy = int(facial_area.get("y", 0))
            fw = int(facial_area.get("w", 0))
            fh = int(facial_area.get("h", 0))

            # Filter out whole-frame fallbacks (when enforce_detection=False finds no face)
            if fx == 0 and fy == 0 and fw >= frame_w - 2 and fh >= frame_h - 2:
                continue

            # Filter out tiny noise artifacts or low confidence
            if fw < 28 or fh < 28 or conf < min_confidence:
                continue

            # Add 15% contextual padding around face crop
            pad_x = int(fw * 0.15)
            pad_y = int(fh * 0.15)
            x1 = max(0, fx - pad_x)
            y1 = max(0, fy - pad_y)
            x2 = min(frame_w, fx + fw + pad_x)
            y2 = min(frame_h, fy + fh + pad_y)

            if x2 <= x1 or y2 <= y1:
                continue

            crop = frame[y1:y2, x1:x2].copy()
            candidates.append({
                "crop": crop,
                "confidence": conf,
                "bbox": [x1, y1, x2, y2],
            })

    except Exception as exc:
        logger.debug("Non-fatal notice during frame face extraction: %s", exc)

    return candidates


def generate_face_embedding(
    face_crop: np.ndarray,
    model_name: str = "Facenet512",
) -> np.ndarray | None:
    """Generate 512-dimensional biometric feature embedding vector for face crop.

    Args:
        face_crop: Cropped facial BGR image matrix.
        model_name: DeepFace feature extraction model architecture.

    Returns:
        NumPy float32 1D array of length 512, or None on failure.
    """
    if face_crop is None or face_crop.size == 0:
        return None

    try:
        representations = DeepFace.represent(
            img_path=face_crop,
            model_name=model_name,
            detector_backend="skip",
            enforce_detection=False,
            align=False,
        )

        if not representations or len(representations) == 0:
            return None

        raw_emb = representations[0].get("embedding")
        if raw_emb is None:
            return None

        embedding = np.array(raw_emb, dtype=np.float32)
        return embedding

    except Exception as exc:
        logger.debug("Error computing DeepFace embedding for face crop: %s", exc)
        return None


def process_video_for_faces(
    video_path: Path,
    faces_dir: Path,
    embeddings_dir: Path,
    enrolled_embeddings: list[np.ndarray],
    manifest_records: list[FaceRecord],
    frame_stride: int = 30,
    similarity_threshold: float = 0.65,
    detector_backend: str = "retinaface",
    model_name: str = "Facenet512",
) -> int:
    """Sample frames from a video, extract unique faces, and save assets.

    Args:
        video_path: Input video file path.
        faces_dir: Destination directory for face crop images.
        embeddings_dir: Destination directory for .npy embeddings.
        enrolled_embeddings: Running pool of unique embeddings for deduplication.
        manifest_records: Running list of FaceRecord instances.
        frame_stride: Sample rate stride (e.g. 30 = 1 per second at 30 fps).
        similarity_threshold: Cosine similarity cutoff to consider faces identical.
        detector_backend: Detector architecture.
        model_name: Embedding model architecture.

    Returns:
        Count of new unique faces enrolled from this video.
    """
    logger.info("================================================================")
    logger.info("Processing video: %s (sampling every %d frames)", video_path.name, frame_stride)
    logger.info("================================================================")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.error("Failed to open video stream: %s", video_path)
        return 0

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0 or np.isnan(fps):
        fps = 30.0

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    logger.info("Video specs: %d total frames, %.1f fps, estimated duration: %.1fs", total_frames, fps, total_frames / fps)

    frame_idx = 0
    sampled_count = 0
    new_faces_enrolled = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1

            # Sample every 30 frames (1 per second)
            if frame_idx % frame_stride != 0:
                continue

            sampled_count += 1
            timestamp_sec = round(frame_idx / fps, 2)

            candidates = extract_face_candidates_from_frame(
                frame=frame,
                detector_backend=detector_backend,
                min_confidence=0.70,
            )

            for cand in candidates:
                crop = cand["crop"]
                conf = cand["confidence"]

                embedding = generate_face_embedding(crop, model_name=model_name)
                if embedding is None:
                    continue

                # Evaluate cosine similarity against all enrolled faces for uniqueness
                is_unique = True
                for prev_emb in enrolled_embeddings:
                    sim = compute_cosine_similarity(embedding, prev_emb)
                    if sim >= similarity_threshold:
                        is_unique = False
                        break

                if not is_unique:
                    logger.debug(
                        "Frame %d: detected face matched existing identity (sim >= %.2f)",
                        frame_idx,
                        similarity_threshold,
                    )
                    continue

                # New unique face identified
                face_num = len(manifest_records) + 1
                face_id = f"face_{face_num:04d}"

                crop_filename = f"{face_id}.jpg"
                emb_filename = f"{face_id}.npy"

                crop_dest = faces_dir / crop_filename
                emb_dest = embeddings_dir / emb_filename

                cv2.imwrite(str(crop_dest), crop)
                np.save(str(emb_dest), embedding)

                enrolled_embeddings.append(embedding)

                record = FaceRecord(
                    face_id=face_id,
                    source_video=video_path.name,
                    frame_number=frame_idx,
                    timestamp_seconds=timestamp_sec,
                    embedding_path=f"backend/demo_data/faces/embeddings/{emb_filename}",
                    crop_path=f"backend/demo_data/faces/{crop_filename}",
                    confidence=round(conf, 4),
                )
                manifest_records.append(record)
                new_faces_enrolled += 1

                logger.info(
                    "Enrolled new unique biometric identity [%s] at frame %d (t=%.1fs, conf=%.3f) -> %s",
                    face_id,
                    frame_idx,
                    timestamp_sec,
                    conf,
                    crop_filename,
                )

    finally:
        cap.release()

    logger.info(
        "Finished %s: sampled %d frames, enrolled %d new unique faces",
        video_path.name,
        sampled_count,
        new_faces_enrolled,
    )
    return new_faces_enrolled


def extract_all_faces(
    videos_dir: Path,
    output_dir: Path,
    frame_stride: int = 30,
    similarity_threshold: float = 0.65,
    detector_backend: str = "retinaface",
    model_name: str = "Facenet512",
) -> list[FaceRecord]:
    """Orchestrate biometric face extraction across all downloaded demo videos.

    Args:
        videos_dir: Directory containing input demo videos.
        output_dir: Directory for extracted face crops and manifest.
        frame_stride: Frame sampling interval.
        similarity_threshold: Deduplication cosine similarity cutoff.
        detector_backend: DeepFace detection backend.
        model_name: DeepFace feature model.

    Returns:
        List of enrolled FaceRecord instances.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    embeddings_dir = output_dir / "embeddings"
    embeddings_dir.mkdir(parents=True, exist_ok=True)

    video_files = sorted(videos_dir.glob("*.mp4"))
    if not video_files:
        logger.warning("No MP4 files found in %s", videos_dir)
        return []

    logger.info("Found %d video files in %s to process for faces", len(video_files), videos_dir)

    enrolled_embeddings: list[np.ndarray] = []
    manifest_records: list[FaceRecord] = []

    for video_file in video_files:
        process_video_for_faces(
            video_path=video_file,
            faces_dir=output_dir,
            embeddings_dir=embeddings_dir,
            enrolled_embeddings=enrolled_embeddings,
            manifest_records=manifest_records,
            frame_stride=frame_stride,
            similarity_threshold=similarity_threshold,
            detector_backend=detector_backend,
            model_name=model_name,
        )

    # Write manifest.json
    manifest_path = output_dir / "manifest.json"
    manifest_data = [asdict(record) for record in manifest_records]

    with open(manifest_path, "w", encoding="utf-8") as f_manifest:
        json.dump(manifest_data, f_manifest, indent=2)

    logger.info("================================================================")
    logger.info("BIOMETRIC FACE EXTRACTION COMPLETE")
    logger.info("Total unique faces enrolled: %d", len(manifest_records))
    logger.info("Manifest saved to: %s", manifest_path.resolve())
    logger.info("================================================================")

    return manifest_records


def main() -> int:
    """CLI entrypoint for extract_faces."""
    # Ensure UTF-8 output encoding on Windows consoles
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Extract unique facial crops and Facenet512 embeddings from demo videos."
    )
    parser.add_argument(
        "--videos-dir",
        type=str,
        default="backend/demo_data/videos",
        help="Path to folder containing downloaded demo MP4 videos.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="backend/demo_data/faces",
        help="Path to folder where face crops, embeddings, and manifest will be saved.",
    )
    parser.add_argument(
        "--stride",
        type=int,
        default=30,
        help="Frame sampling stride (default: 30 = 1 per second at 30 fps).",
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.65,
        help="Cosine similarity threshold for face deduplication (default: 0.65).",
    )
    parser.add_argument(
        "--detector",
        type=str,
        default="retinaface",
        help="DeepFace detector backend (default: retinaface).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="Facenet512",
        help="DeepFace representation model (default: Facenet512).",
    )

    args = parser.parse_args()

    videos_path = Path(args.videos_dir)
    output_path = Path(args.output_dir)

    manifest = extract_all_faces(
        videos_dir=videos_path,
        output_dir=output_path,
        frame_stride=args.stride,
        similarity_threshold=args.similarity_threshold,
        detector_backend=args.detector,
        model_name=args.model,
    )

    print("\n" + "=" * 80)
    print("BIOMETRIC FACE EXTRACTION MANIFEST SUMMARY")
    print("=" * 80)
    print(f"{'Face ID':<12} | {'Source Video':<36} | {'Frame':<6} | {'Time (s)':<8} | {'Conf'}")
    print("-" * 80)
    for item in manifest:
        print(f"{item.face_id:<12} | {item.source_video:<36} | {item.frame_number:<6} | {item.timestamp_seconds:<8.1f} | {item.confidence:.3f}")

    print("=" * 80)
    print(f"Manifest written to {output_path / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
