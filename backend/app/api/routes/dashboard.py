"""Executive safety operations dashboard API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.incident import Incident, IncidentSeverity
from app.models.machine import Machine
from app.models.user import User
from app.models.worker import Worker
from app.schemas.dashboard import DashboardSummaryResponse
from app.schemas.incident import IncidentResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Get real-time operational status and safety summary",
)
async def get_dashboard_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> DashboardSummaryResponse:
    """Retrieve operational dashboard summary metrics for heavy equipment and personnel."""
    now = datetime.now(UTC)
    last_24h = now - timedelta(hours=24)

    # 1. Machine metrics
    active_mach_stmt = select(func.count(Machine.id)).where(Machine.status == "ACTIVE")
    total_mach_stmt = select(func.count(Machine.id))

    active_mach_res = await db.execute(active_mach_stmt)
    total_mach_res = await db.execute(total_mach_stmt)

    active_machines = active_mach_res.scalar_one()
    total_machines = total_mach_res.scalar_one()

    # 2. Worker metrics
    total_work_stmt = select(func.count(Worker.id))
    auth_work_stmt = select(func.count(Worker.id)).where(Worker.is_authorized.is_(True))

    total_work_res = await db.execute(total_work_stmt)
    auth_work_res = await db.execute(auth_work_stmt)

    total_workers = total_work_res.scalar_one()
    authorized_workers = auth_work_res.scalar_one()

    # 3. Incident metrics
    inc_24h_stmt = select(func.count(Incident.id)).where(Incident.timestamp >= last_24h)
    crit_24h_stmt = select(func.count(Incident.id)).where(
        Incident.timestamp >= last_24h,
        Incident.severity == IncidentSeverity.CRITICAL,
    )

    inc_24h_res = await db.execute(inc_24h_stmt)
    crit_24h_res = await db.execute(crit_24h_stmt)

    incidents_24h = inc_24h_res.scalar_one()
    critical_incidents = crit_24h_res.scalar_one()

    # 4. Recent incidents
    recent_stmt = (
        select(Incident)
        .order_by(Incident.timestamp.desc())
        .limit(5)
    )
    recent_res = await db.execute(recent_stmt)
    recent_incidents = [IncidentResponse.model_validate(inc) for inc in recent_res.scalars().all()]

    system_status = "WARNING" if critical_incidents > 0 else "OPERATIONAL"

    return DashboardSummaryResponse(
        active_machines_count=active_machines,
        total_machines_count=total_machines,
        total_workers_count=total_workers,
        authorized_workers_count=authorized_workers,
        incidents_last_24h_count=incidents_24h,
        critical_incidents_count=critical_incidents,
        system_status=system_status,
        recent_incidents=recent_incidents,
    )
