"""Safety incidents proximity violations and video playback API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db, get_storage_service
from app.models.incident import Incident, IncidentSeverity
from app.models.user import User
from app.schemas.common import PaginationParams
from app.schemas.incident import (
    IncidentDetailResponse,
    IncidentResponse,
    IncidentStatsResponse,
)
from app.services.storage import StorageService

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get(
    "",
    response_model=list[IncidentResponse],
    summary="List safety incidents with filtering and pagination",
)
async def list_incidents(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    severity: Annotated[IncidentSeverity | None, Query(description="Filter by severity tier")] = None,
    worker_id: Annotated[int | None, Query(description="Filter by involved worker ID")] = None,
    machine_id: Annotated[int | None, Query(description="Filter by involved machine ID")] = None,
    start_date: Annotated[datetime | None, Query(description="Filter events after timestamp")] = None,
    end_date: Annotated[datetime | None, Query(description="Filter events before timestamp")] = None,
    pagination: Annotated[PaginationParams, Depends()] = PaginationParams(),
) -> list[IncidentResponse]:
    """Retrieve paginated proximity breach incidents matching filter criteria.

    Includes the total count of matching records in the `X-Total-Count` header.

    Args:
        response: FastAPI response object for setting custom headers.
        db: Database session.
        severity: Optional severity filter.
        worker_id: Optional worker filter.
        machine_id: Optional machine filter.
        start_date: Optional start datetime filter.
        end_date: Optional end datetime filter.
        pagination: Offset/limit pagination parameters.

    Returns:
        list[IncidentResponse]: Sequence of matching incident models.
    """
    conditions = []
    if severity is not None:
        conditions.append(Incident.severity == severity)
    if worker_id is not None:
        conditions.append(Incident.worker_id == worker_id)
    if machine_id is not None:
        conditions.append(Incident.machine_id == machine_id)
    if start_date is not None:
        conditions.append(Incident.timestamp >= start_date)
    if end_date is not None:
        conditions.append(Incident.timestamp <= end_date)

    # 1. Query total matching count for pagination header
    count_stmt = select(func.count(Incident.id))
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    count_result = await db.execute(count_stmt)
    total_count = count_result.scalar_one()

    response.headers["X-Total-Count"] = str(total_count)

    # 2. Query paginated results
    query = (
        select(Incident)
        .order_by(Incident.timestamp.desc())
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    if conditions:
        query = query.where(*conditions)

    result = await db.execute(query)
    incidents = result.scalars().all()

    return [IncidentResponse.model_validate(inc) for inc in incidents]


@router.get(
    "/stats",
    response_model=IncidentStatsResponse,
    summary="Get aggregated safety statistics and breach frequency",
)
async def get_incident_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> IncidentStatsResponse:
    """Compute aggregate spatial proximity analytics and violation totals."""
    # Total count
    total_stmt = select(func.count(Incident.id))
    total_res = await db.execute(total_stmt)
    total_count = total_res.scalar_one()

    # Severity counts
    critical_stmt = select(func.count(Incident.id)).where(Incident.severity == IncidentSeverity.CRITICAL)
    warning_stmt = select(func.count(Incident.id)).where(Incident.severity == IncidentSeverity.WARNING)
    caution_stmt = select(func.count(Incident.id)).where(Incident.severity == IncidentSeverity.CAUTION)

    crit_res = await db.execute(critical_stmt)
    warn_res = await db.execute(warning_stmt)
    caut_res = await db.execute(caution_stmt)

    critical_count = crit_res.scalar_one()
    warning_count = warn_res.scalar_one()
    caution_count = caut_res.scalar_one()

    # Average distance
    avg_dist_stmt = select(func.avg(Incident.distance_meters))
    avg_dist_res = await db.execute(avg_dist_stmt)
    avg_dist = avg_dist_res.scalar_one() or 0.0

    # Incidents today (UTC midnight to now)
    now = datetime.now(UTC)
    start_of_today = datetime.combine(now.date(), time.min, tzinfo=UTC)
    today_stmt = select(func.count(Incident.id)).where(Incident.timestamp >= start_of_today)
    today_res = await db.execute(today_stmt)
    incidents_today = today_res.scalar_one()

    return IncidentStatsResponse(
        total_incidents=total_count,
        critical_count=critical_count,
        warning_count=warning_count,
        caution_count=caution_count,
        avg_distance_meters=round(float(avg_dist), 2),
        incidents_today=incidents_today,
    )


@router.get(
    "/{incident_id}",
    response_model=IncidentDetailResponse,
    summary="Get single incident with full details and alert audit logs",
    responses={404: {"description": "Incident not found"}},
)
async def get_incident(
    incident_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> IncidentDetailResponse:
    """Retrieve full incident record and associated supervisor dispatch logs."""
    stmt = (
        select(Incident)
        .options(selectinload(Incident.alert_logs))
        .where(Incident.id == incident_id)
    )
    result = await db.execute(stmt)
    incident = result.scalars().first()

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found",
        )

    return IncidentDetailResponse.model_validate(incident)


@router.get(
    "/{incident_id}/clip",
    summary="Redirect to presigned Cloudflare R2 video clip URL",
    responses={
        307: {"description": "Temporary redirect to presigned video clip URL"},
        404: {"description": "Incident or video recording not found"},
    },
)
async def get_incident_clip_redirect(
    incident_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
    _: Annotated[User, Depends(get_current_user)],
) -> RedirectResponse:
    """Generate a time-limited presigned URL for the incident video clip and redirect."""
    stmt = select(Incident).where(Incident.id == incident_id)
    result = await db.execute(stmt)
    incident = result.scalars().first()

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found",
        )

    if not incident.clip_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No video recording available for incident {incident_id}",
        )

    # If clip_url contains an R2 object key or full URL, generate presigned URL or redirect
    clip_url = incident.clip_url
    if "incidents/" in clip_url:
        # Extract the object key portion starting at 'incidents/'
        object_key = "incidents/" + clip_url.split("incidents/", 1)[1]
        try:
            presigned_url = storage_service.generate_presigned_url(object_key, expiry_seconds=3600)
            return RedirectResponse(
                url=presigned_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT
            )
        except Exception:
            # Fall back to raw URL if presigning fails
            pass

    return RedirectResponse(url=clip_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
