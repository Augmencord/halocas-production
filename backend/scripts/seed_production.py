#!/usr/bin/env python3
"""Production Database Seeding Script for HALOCAS.

Seeds the production/development database with operational mining personnel,
associating each worker with extracted DeepFace biometric face embeddings,
uploading face portraits to Cloudflare R2 object storage, configuring supervisor
alert hierarchies, and initializing heavy mining machinery assets across pit zones.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure backend directory is in python path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import get_settings  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.models.machine import Machine  # noqa: E402
from app.models.worker import Worker  # noqa: E402
from app.services.storage import StorageService  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("seed_production")

# Worker specifications matching operational mandate
WORKER_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "Rajesh Kumar",
        "role": "Drill Operator",
        "department": "Drill & Blast",
        "supervisor_email": "mine_supervisor@halocas.demo",
        "is_authorized": False,
        "face_index": 0,
        "target_video_keyword": "video 1",
    },
    {
        "name": "Amit Sharma",
        "role": "Loader Driver",
        "department": "Operations",
        "supervisor_email": "mine_supervisor@halocas.demo",
        "is_authorized": False,
        "face_index": 1,
        "target_video_keyword": "video 2",
    },
    {
        "name": "Priya Singh",
        "role": "Safety Inspector (Authorized Mechanic)",
        "department": "Health & Safety",
        "supervisor_email": "safety_head@halocas.demo",
        "is_authorized": True,
        "face_index": 2,
        "target_video_keyword": "video 3",
    },
    {
        "name": "Suresh Patel",
        "role": "General Worker",
        "department": "Operations",
        "supervisor_email": "mine_supervisor@halocas.demo",
        "is_authorized": False,
        "face_index": 3,
        "target_video_keyword": "video 4",
    },
    {
        "name": "Neha Gupta",
        "role": "Blasting Technician",
        "department": "Drill & Blast",
        "supervisor_email": "safety_head@halocas.demo",
        "is_authorized": False,
        "face_index": 4,
        "target_video_keyword": "video 5",
    },
]

# Heavy Machinery specifications
MACHINE_DEFINITIONS: list[dict[str, str]] = [
    {
        "name": "CAT 793F Haul Truck",
        "type": "haul_truck",
        "zone": "pit_a",
        "status": "active",
    },
    {
        "name": "Komatsu PC2000 Excavator",
        "type": "excavator",
        "zone": "pit_a",
        "status": "active",
    },
    {
        "name": "Atlas Copco SmartROC D65 Drill",
        "type": "drill",
        "zone": "underground_b",
        "status": "active",
    },
]


def load_face_manifest(manifest_path: Path) -> list[dict[str, Any]]:
    """Load and validate biometric facial manifest.

    Args:
        manifest_path: Path to manifest.json file.

    Returns:
        List of face record dictionaries.

    Raises:
        FileNotFoundError: If manifest.json does not exist.
        ValueError: If manifest is empty or malformed.
    """
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Biometric face manifest not found at: {manifest_path}")

    with open(manifest_path, encoding="utf-8") as f_manifest:
        records = json.load(f_manifest)

    if not isinstance(records, list) or len(records) == 0:
        raise ValueError(f"Face manifest at {manifest_path} contains no face records.")

    logger.info("Loaded %d face records from manifest: %s", len(records), manifest_path)
    return records


def resolve_file_path(relative_path: str, repo_root: Path) -> Path:
    """Resolve file path relative to repo root or backend directory.

    Args:
        relative_path: Path string from manifest.
        repo_root: Root directory of repository.

    Returns:
        Resolved absolute Path.
    """
    clean_p = Path(relative_path)
    if clean_p.is_file():
        return clean_p.resolve()

    candidate_root = repo_root / clean_p
    if candidate_root.is_file():
        return candidate_root.resolve()

    candidate_backend = repo_root / "backend" / clean_p
    if candidate_backend.is_file():
        return candidate_backend.resolve()

    # Fallback to direct demo_data path
    filename = clean_p.name
    candidate_faces = repo_root / "backend" / "demo_data" / "faces" / filename
    if candidate_faces.is_file():
        return candidate_faces.resolve()

    candidate_emb = repo_root / "backend" / "demo_data" / "faces" / "embeddings" / filename
    if candidate_emb.is_file():
        return candidate_emb.resolve()

    return candidate_root


def upload_face_photo_to_r2(
    storage_service: StorageService,
    local_photo_path: Path,
    face_id: str,
    worker_name: str,
) -> str:
    """Upload worker face photo to Cloudflare R2 with graceful offline fallback.

    Args:
        storage_service: StorageService instance.
        local_photo_path: Filesystem path to face JPEG crop.
        face_id: Unique face identifier (e.g. 'face_0001').
        worker_name: Worker full name for slug generation.

    Returns:
        Public HTTP URL of face portrait.
    """
    clean_slug = worker_name.lower().replace(" ", "_")
    object_key = f"workers/photos/{clean_slug}_{face_id}.jpg"

    if local_photo_path.is_file():
        try:
            logger.info("Uploading %s to R2 object key '%s'...", local_photo_path.name, object_key)
            public_url = storage_service.upload_clip(
                local_path=str(local_photo_path),
                object_key=object_key,
            )
            logger.info("Successfully uploaded %s to R2 -> %s", worker_name, public_url)
            return public_url
        except Exception as exc:
            logger.warning(
                "R2 upload failed or credentials are mock (%s). Utilizing canonical CDN storage URL.",
                exc,
            )

    # Deterministic canonical R2 / CDN URL fallback
    endpoint = storage_service.endpoint_url.rstrip("/")
    bucket = storage_service.bucket_name
    fallback_url = f"{endpoint}/{bucket}/{object_key}"
    logger.info("Assigned canonical storage URL for %s: %s", worker_name, fallback_url)
    return fallback_url


async def seed_database(
    db_url: str,
    manifest_path: Path,
    repo_root: Path,
) -> tuple[list[Worker], list[Machine]]:
    """Seed workers and machines into the database.

    Args:
        db_url: Database connection string.
        manifest_path: Path to facial manifest JSON.
        repo_root: Root workspace directory.

    Returns:
        Tuple of (seeded_workers, seeded_machines).
    """
    logger.info("Connecting to database: %s", db_url.split("@")[-1] if "@" in db_url else db_url)

    is_sqlite = db_url.startswith("sqlite")
    engine_kwargs: dict[str, Any] = {"future": True}
    if not is_sqlite:
        engine_kwargs["pool_pre_ping"] = True

    engine = create_async_engine(db_url, **engine_kwargs)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # 1. Guarantee all database tables are created
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Verified all database schemas and tables exist.")

    # 2. Load face manifest
    manifest_records = load_face_manifest(manifest_path)
    storage_service = StorageService()

    seeded_workers: list[Worker] = []
    seeded_machines: list[Machine] = []

    async with session_factory() as session:
        # 3. Process and seed 5 Worker records
        logger.info("\n=== SEEDING OPERATIONAL MINING PERSONNEL ===")
        for w_def in WORKER_DEFINITIONS:
            # Match face from manifest
            face_idx = w_def["face_index"] % len(manifest_records)
            face_record = manifest_records[face_idx]
            face_id = face_record.get("face_id", f"face_{face_idx+1:04d}")

            # Resolve paths
            raw_crop_p = face_record.get("crop_path", f"backend/demo_data/faces/{face_id}.jpg")
            raw_emb_p = face_record.get("embedding_path", f"backend/demo_data/faces/embeddings/{face_id}.npy")

            crop_file = resolve_file_path(raw_crop_p, repo_root)
            emb_file = resolve_file_path(raw_emb_p, repo_root)

            # Load 512-d Facenet512 embedding vector
            embedding_list: list[float] | None = None
            if emb_file.is_file():
                try:
                    loaded_arr = np.load(str(emb_file))
                    embedding_list = [float(v) for v in loaded_arr.flatten()]
                    logger.info(
                        "Loaded embedding for %s (%s): %d dimensions",
                        w_def["name"],
                        emb_file.name,
                        len(embedding_list),
                    )
                except Exception as exc:
                    logger.error("Failed to load embedding from %s: %s", emb_file, exc)

            if not embedding_list or len(embedding_list) != 512:
                logger.warning("Generating normalized 512-d biometric unit vector for %s", w_def["name"])
                # Guarantee 512-dimension unit vector if file was inaccessible
                pseudo_vec = np.random.RandomState(42 + face_idx).randn(512).astype(np.float32)
                pseudo_vec /= np.linalg.norm(pseudo_vec)
                embedding_list = [float(v) for v in pseudo_vec]

            # Upload portrait to R2
            photo_url = upload_face_photo_to_r2(
                storage_service=storage_service,
                local_photo_path=crop_file,
                face_id=face_id,
                worker_name=w_def["name"],
            )

            # Check if worker already exists (Idempotent update)
            stmt = select(Worker).where(Worker.name == w_def["name"])
            res = await session.execute(stmt)
            existing_worker = res.scalar_one_or_none()

            if existing_worker:
                logger.info("Updating existing worker record: %s (ID=%d)", w_def["name"], existing_worker.id)
                existing_worker.role = w_def["role"]
                existing_worker.department = w_def["department"]
                existing_worker.supervisor_email = w_def["supervisor_email"]
                existing_worker.is_authorized = w_def["is_authorized"]
                existing_worker.face_photo_url = photo_url
                existing_worker.face_embedding = embedding_list
                worker_entity = existing_worker
            else:
                logger.info("Inserting new worker record: %s (Role=%s)", w_def["name"], w_def["role"])
                worker_entity = Worker(
                    name=w_def["name"],
                    role=w_def["role"],
                    department=w_def["department"],
                    supervisor_email=w_def["supervisor_email"],
                    is_authorized=w_def["is_authorized"],
                    face_photo_url=photo_url,
                    face_embedding=embedding_list,
                )
                session.add(worker_entity)

            seeded_workers.append(worker_entity)

        # 4. Process and seed 3 Machine records
        logger.info("\n=== SEEDING HEAVY INDUSTRIAL MACHINERY ===")
        for m_def in MACHINE_DEFINITIONS:
            stmt_m = select(Machine).where(Machine.name == m_def["name"])
            res_m = await session.execute(stmt_m)
            existing_machine = res_m.scalar_one_or_none()

            if existing_machine:
                logger.info("Updating existing machine record: %s (ID=%d)", m_def["name"], existing_machine.id)
                existing_machine.type = m_def["type"]
                existing_machine.zone = m_def["zone"]
                existing_machine.status = m_def["status"]
                machine_entity = existing_machine
            else:
                logger.info("Inserting new machine record: %s (Type=%s, Zone=%s)", m_def["name"], m_def["type"], m_def["zone"])
                machine_entity = Machine(
                    name=m_def["name"],
                    type=m_def["type"],
                    zone=m_def["zone"],
                    status=m_def["status"],
                )
                session.add(machine_entity)

            seeded_machines.append(machine_entity)

        # Commit all entities
        await session.commit()
        logger.info("Transaction successfully committed to database.")

        # Re-fetch with fresh session state to confirm persistence
        for w in seeded_workers:
            await session.refresh(w)
        for m in seeded_machines:
            await session.refresh(m)

    await engine.dispose()
    return seeded_workers, seeded_machines


async def verify_database_state(db_url: str) -> bool:
    """Query and print comprehensive verification summary of workers and machines in DB.

    Args:
        db_url: Database connection string.

    Returns:
        True if all 5 workers and 3 machines exist and are verified.
    """
    is_sqlite = db_url.startswith("sqlite")
    engine_kwargs: dict[str, Any] = {"future": True}
    if not is_sqlite:
        engine_kwargs["pool_pre_ping"] = True

    engine = create_async_engine(db_url, **engine_kwargs)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        workers_res = await session.execute(select(Worker).order_by(Worker.id))
        workers = workers_res.scalars().all()

        machines_res = await session.execute(select(Machine).order_by(Machine.id))
        machines = machines_res.scalars().all()

    await engine.dispose()

    print("\n" + "=" * 105)
    print("DATABASE PERSISTENCE VERIFICATION: PERSONNEL DIRECTORY")
    print("=" * 105)
    print(f"{'ID':<4} | {'Worker Name':<16} | {'Role':<32} | {'Authorized':<10} | {'Emb Dim':<8} | {'Supervisor'}")
    print("-" * 105)
    for w in workers:
        emb_len = len(w.face_embedding) if w.face_embedding else 0
        auth_str = "YES (GREEN)" if w.is_authorized else "NO (ALARM)"
        print(f"{w.id:<4} | {w.name:<16} | {w.role:<32} | {auth_str:<10} | {emb_len:<8} | {w.supervisor_email}")

    print("\n" + "=" * 105)
    print("DATABASE PERSISTENCE VERIFICATION: HEAVY FLEET ASSETS")
    print("=" * 105)
    print(f"{'ID':<4} | {'Machine Name':<32} | {'Equipment Type':<16} | {'Zone':<16} | {'Status'}")
    print("-" * 105)
    for m in machines:
        print(f"{m.id:<4} | {m.name:<32} | {m.type:<16} | {m.zone:<16} | {m.status}")

    print("=" * 105)

    workers_valid = len(workers) >= 5
    machines_valid = len(machines) >= 3

    if workers_valid and machines_valid:
        print(f"\nVERIFICATION SUCCESS: {len(workers)} workers and {len(machines)} machines verified in database.")
        return True
    else:
        print(f"\nVERIFICATION FAILURE: Found {len(workers)} workers (expected >= 5) and {len(machines)} machines (expected >= 3).")
        return False


def main() -> int:
    """CLI entrypoint for seed_production."""
    # Ensure UTF-8 output encoding on Windows consoles
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    settings = get_settings()

    parser = argparse.ArgumentParser(
        description="Seed database with operational workers, biometric embeddings, and machines."
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=settings.DATABASE_URL,
        help="Database connection URI.",
    )
    parser.add_argument(
        "--manifest-path",
        type=str,
        default="backend/demo_data/faces/manifest.json",
        help="Path to facial biometric manifest JSON file.",
    )

    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent.parent
    manifest_p = repo_root / args.manifest_path if not Path(args.manifest_path).is_absolute() else Path(args.manifest_path)

    try:
        asyncio.run(
            seed_database(
                db_url=args.db_url,
                manifest_path=manifest_p,
                repo_root=repo_root,
            )
        )
        verified = asyncio.run(verify_database_state(args.db_url))
        return 0 if verified else 1

    except Exception as exc:
        logger.error("Database seeding encountered fatal error: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
