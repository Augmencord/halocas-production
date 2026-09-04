"""Pydantic validation models for safety incidents and alert audit logs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.alert_log import DeliveryStatus
from app.models.incident import IncidentSeverity


class AlertLogResponse(BaseModel):
    """Audit log schema for an automated supervisor notification attempt."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    incident_id: int
    recipient_email: str
    delivery_status: DeliveryStatus
    retry_count: int
    error_message: str | None = None
    sent_at: datetime | None = None
    created_at: datetime


class IncidentResponse(BaseModel):
    """Proximity safety breach incident response schema."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    timestamp: datetime
    machine_id: int
    worker_id: int | None = None
    worker_name: str | None = None
    distance_meters: float
    severity: IncidentSeverity
    closing_velocity: float
    clip_url: str | None = None
    clip_duration_sec: float
    supervisor_notified: bool
    supervisor_email: str | None = None
    notification_sent_at: datetime | None = None
    face_match_confidence: float | None = None
    zone: str | None = None
    created_at: datetime


class IncidentDetailResponse(IncidentResponse):
    """Comprehensive incident profile including associated alert logs."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    alert_logs: list[AlertLogResponse] = Field(default_factory=list)


class IncidentStatsResponse(BaseModel):
    """Aggregate spatial and temporal statistics for safety incidents."""

    model_config = ConfigDict(extra="ignore")

    total_incidents: int
    critical_count: int
    warning_count: int
    caution_count: int
    avg_distance_meters: float
    incidents_today: int
