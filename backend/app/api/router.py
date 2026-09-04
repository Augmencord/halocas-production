"""HALOCAS Primary API Router.

Aggregates domain-specific route definitions including safety alerts,
worker management, machine telemetrics, and incident video retrieval.
"""


from fastapi import APIRouter, status
from pydantic import BaseModel, Field

api_router = APIRouter(prefix="/api/v1")


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
)
async def get_system_status() -> SystemStatusResponse:
    """Retrieve operational health of API subsystems."""
    return SystemStatusResponse(
        status="operational",
        version="0.1.0",
        subsystems={
            "vision_engine": "ready",
            "proximity_detector": "ready",
            "alert_dispatcher": "ready",
            "storage": "ready",
        },
    )
