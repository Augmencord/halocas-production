"""Heavy mining equipment and fleet tracking API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.machine import Machine
from app.models.user import User
from app.schemas.common import PaginationParams
from app.schemas.machine import MachineCreate, MachineResponse, MachineStatusUpdate

router = APIRouter(prefix="/machines", tags=["Machines"])


@router.get(
    "",
    response_model=list[MachineResponse],
    summary="List all registered mining machinery",
)
async def list_machines(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    pagination: Annotated[PaginationParams, Depends()] = PaginationParams(),
) -> list[MachineResponse]:
    """Retrieve list of all mining equipment with status."""
    count_stmt = select(func.count(Machine.id))
    count_res = await db.execute(count_stmt)
    total_count = count_res.scalar_one()

    response.headers["X-Total-Count"] = str(total_count)

    stmt = (
        select(Machine)
        .order_by(Machine.id.asc())
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    result = await db.execute(stmt)
    machines = result.scalars().all()

    return [MachineResponse.model_validate(m) for m in machines]


@router.post(
    "",
    response_model=MachineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new heavy equipment unit",
)
async def create_machine(
    payload: MachineCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> MachineResponse:
    """Register equipment unit (haul truck, hydraulic excavator, wheel loader)."""
    machine = Machine(
        name=payload.name.strip(),
        type=payload.type.strip(),
        zone=payload.zone.strip(),
        status=payload.status.strip().upper(),
    )
    db.add(machine)
    await db.commit()
    await db.refresh(machine)

    return MachineResponse.model_validate(machine)


@router.put(
    "/{machine_id}/status",
    response_model=MachineResponse,
    summary="Update operational status of a machine",
    responses={404: {"description": "Machine not found"}},
)
async def update_machine_status(
    machine_id: int,
    payload: MachineStatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> MachineResponse:
    """Update status of machinery (e.g. ACTIVE, MAINTENANCE, OFFLINE)."""
    stmt = select(Machine).where(Machine.id == machine_id)
    result = await db.execute(stmt)
    machine = result.scalars().first()

    if machine is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with ID {machine_id} not found",
        )

    machine.status = payload.status.strip().upper()
    await db.commit()
    await db.refresh(machine)

    return MachineResponse.model_validate(machine)
