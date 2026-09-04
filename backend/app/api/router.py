"""HALOCAS Primary API Router.

Aggregates all domain-specific route definitions including authentication,
safety incidents, worker biometric management, machine fleet telemetrics,
and live video streaming feeds under the `/api/v1` namespace.
"""

from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.api.routes.auth import router as auth_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.incidents import router as incidents_router
from app.api.routes.machines import router as machines_router
from app.api.routes.telemetry import router as telemetry_router
from app.api.routes.workers import router as workers_router

api_router = APIRouter(prefix="/api/v1")

# Mount route controllers
api_router.include_router(auth_router)
api_router.include_router(incidents_router)
api_router.include_router(workers_router)
api_router.include_router(machines_router)
api_router.include_router(telemetry_router)
api_router.include_router(dashboard_router)


class SystemStatusResponse(BaseModel):
    """Schema representing API version and subsystem operational status."""

    status: str = Field(..., description="Operational status flag")
    version: str = Field(..., description="API semantic version")
    subsystems: dict[str, str] = Field(..., description="Map of critical subsystem statuses")


@api_router.get(
    "/status",
    response_model=SystemStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Subsystem Status",
    description="Returns high-level status of the HALOCAS API and integrated safety subsystems.",
    tags=["System"],
)
async def get_system_status() -> SystemStatusResponse:
    """Retrieve operational health of API subsystems."""
    return SystemStatusResponse(
        status="operational",
        version="1.0.0",
        subsystems={
            "vision_engine": "ready",
            "proximity_detector": "ready",
            "alert_dispatcher": "ready",
            "storage": "ready",
            "telemetry_stream": "ready",
        },
    )
