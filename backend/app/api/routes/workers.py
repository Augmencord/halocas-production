"""Personnel management and biometric face enrollment API endpoints."""

from __future__ import annotations

import tempfile
from typing import Annotated

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    get_current_user,
    get_db,
    get_face_verifier,
    get_storage_service,
)
from app.core.face_verifier import FaceVerifier
from app.models.user import User
from app.models.worker import Worker
from app.schemas.common import PaginationParams
from app.schemas.incident import IncidentResponse
from app.schemas.worker import (
    FaceEnrollResponse,
    WorkerCreate,
    WorkerDetailResponse,
    WorkerResponse,
    WorkerUpdate,
)
from app.services.storage import StorageService

router = APIRouter(prefix="/workers", tags=["Workers"])


def _to_worker_response(worker: Worker) -> WorkerResponse:
    """Helper to convert Worker ORM model into WorkerResponse with has_face_embedding flag."""
    return WorkerResponse(
        id=worker.id,
        name=worker.name,
        role=worker.role,
        department=worker.department,
        supervisor_id=worker.supervisor_id,
        supervisor_email=worker.supervisor_email,
        face_photo_url=worker.face_photo_url,
        is_authorized=worker.is_authorized,
        has_face_embedding=bool(worker.face_embedding and len(worker.face_embedding) > 0),
        created_at=worker.created_at,
    )


@router.get(
    "",
    response_model=list[WorkerResponse],
    summary="List all registered mine personnel with pagination",
)
async def list_workers(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    pagination: Annotated[PaginationParams, Depends()] = PaginationParams(),
) -> list[WorkerResponse]:
    """List workers with offset and limit pagination and X-Total-Count header."""
    count_stmt = select(func.count(Worker.id))
    count_res = await db.execute(count_stmt)
    total_count = count_res.scalar_one()

    response.headers["X-Total-Count"] = str(total_count)

    stmt = (
        select(Worker)
        .order_by(Worker.name.asc())
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    result = await db.execute(stmt)
    workers = result.scalars().all()

    return [_to_worker_response(w) for w in workers]


@router.post(
    "",
    response_model=WorkerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new mine worker",
)
async def create_worker(
    payload: WorkerCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> WorkerResponse:
    """Register personnel profile without face embedding."""
    worker = Worker(
        name=payload.name.strip(),
        role=payload.role.strip(),
        department=payload.department.strip(),
        supervisor_id=payload.supervisor_id,
        supervisor_email=str(payload.supervisor_email).strip().lower() if payload.supervisor_email else None,
        is_authorized=payload.is_authorized,
        face_embedding=None,
        face_photo_url=None,
    )
    db.add(worker)
    await db.commit()
    await db.refresh(worker)

    return _to_worker_response(worker)


@router.get(
    "/{worker_id}",
    response_model=WorkerDetailResponse,
    summary="Get single worker profile with incident breach history",
    responses={404: {"description": "Worker not found"}},
)
async def get_worker(
    worker_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> WorkerDetailResponse:
    """Retrieve full worker record with historical proximity breaches."""
    stmt = (
        select(Worker)
        .options(selectinload(Worker.incidents))
        .where(Worker.id == worker_id)
    )
    result = await db.execute(stmt)
    worker = result.scalars().first()

    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with ID {worker_id} not found",
        )

    base = _to_worker_response(worker)
    recent_incidents = [
        IncidentResponse.model_validate(inc)
        for inc in sorted(worker.incidents, key=lambda x: x.timestamp, reverse=True)[:10]
    ]

    return WorkerDetailResponse(
        **base.model_dump(),
        total_incidents=len(worker.incidents),
        recent_incidents=recent_incidents,
    )


@router.put(
    "/{worker_id}",
    response_model=WorkerResponse,
    summary="Update worker details and authorization status",
    responses={404: {"description": "Worker not found"}},
)
async def update_worker(
    worker_id: int,
    payload: WorkerUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> WorkerResponse:
    """Update profile information, supervisor linkage, or hazard authorization."""
    stmt = select(Worker).where(Worker.id == worker_id)
    result = await db.execute(stmt)
    worker = result.scalars().first()

    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with ID {worker_id} not found",
        )

    if payload.name is not None:
        worker.name = payload.name.strip()
    if payload.role is not None:
        worker.role = payload.role.strip()
    if payload.department is not None:
        worker.department = payload.department.strip()
    if payload.supervisor_id is not None:
        worker.supervisor_id = payload.supervisor_id
    if payload.supervisor_email is not None:
        worker.supervisor_email = str(payload.supervisor_email).strip().lower()
    if payload.is_authorized is not None:
        worker.is_authorized = payload.is_authorized

    await db.commit()
    await db.refresh(worker)

    return _to_worker_response(worker)


@router.post(
    "/{worker_id}/enroll-face",
    response_model=FaceEnrollResponse,
    summary="Upload face portrait and extract 512-D DeepFace biometric embedding",
    responses={
        400: {"description": "No face detected or invalid image format"},
        404: {"description": "Worker not found"},
    },
)
async def enroll_face(
    worker_id: int,
    photo: Annotated[UploadFile, File(description="Worker portrait image file (JPEG/PNG)")],
    db: Annotated[AsyncSession, Depends(get_db)],
    face_verifier: Annotated[FaceVerifier, Depends(get_face_verifier)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
    _: Annotated[User, Depends(get_current_user)],
) -> FaceEnrollResponse:
    """Ingest portrait image, extract Facenet512 512-D embedding vector, and store in DB."""
    stmt = select(Worker).where(Worker.id == worker_id)
    result = await db.execute(stmt)
    worker = result.scalars().first()

    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with ID {worker_id} not found",
        )

    photo_bytes = await photo.read()
    if len(photo_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    # Decode image into OpenCV BGR numpy array
    nparr = np.frombuffer(photo_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None or image.size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image format; cannot decode image bytes",
        )

    # Extract 512-D embedding
    embedding = face_verifier.extract_embedding(image)
    if embedding is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No face detected in portrait image. Ensure worker face is well-lit and unobstructed.",
        )

    # Save photo to temporary file and upload to R2
    photo_url: str | None = None
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(photo_bytes)
        tmp_path = tmp.name

    try:
        photo_key = f"faces/worker_{worker.id}.jpg"
        photo_url = storage_service.upload_clip(tmp_path, photo_key)
    except Exception:
        # Fall back gracefully if R2 upload fails
        photo_url = f"/static/faces/worker_{worker.id}.jpg"

    # Update worker record
    worker.face_embedding = embedding.tolist()
    worker.face_photo_url = photo_url
    await db.commit()
    await db.refresh(worker)

    return FaceEnrollResponse(
        worker_id=worker.id,
        worker_name=worker.name,
        face_enrolled=True,
        embedding_dimensions=len(worker.face_embedding),
        face_photo_url=worker.face_photo_url,
        message="Face embedding successfully extracted and enrolled",
    )
