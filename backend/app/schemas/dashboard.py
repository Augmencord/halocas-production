"""Pydantic schemas for the real-time operations dashboard summary."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.incident import IncidentResponse


class ActiveAlertSummary(BaseModel):
    """Real-time active incident notice on dashboard."""

    model_config = ConfigDict(extra="ignore")

    incident_id: int
    machine_name: str
    worker_name: str
    distance_meters: float
    severity: str
    timestamp: datetime


class DashboardSummaryResponse(BaseModel):
    """High-level snapshot of active mine safety operations."""

    model_config = ConfigDict(extra="ignore")

    active_machines_count: int = Field(..., description="Count of equipment currently operational")
    total_machines_count: int = Field(..., description="Total fleet size")
    total_workers_count: int = Field(..., description="Total registered mine personnel")
    authorized_workers_count: int = Field(..., description="Personnel authorized in hazard perimeters")
    incidents_last_24h_count: int = Field(..., description="Proximity incidents recorded in past 24 hours")
    critical_incidents_count: int = Field(..., description="Critical (<3m) breaches in past 24 hours")
    system_status: str = Field(default="OPERATIONAL", description="Subsystem health status")
    recent_incidents: list[IncidentResponse] = Field(default_factory=list)
