"""Pydantic validation schemas for mine workers and biometric enrollment."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.incident import IncidentResponse


class WorkerCreate(BaseModel):
    """Schema for registering a new worker into the system."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=2, max_length=100, description="Full worker name")
    role: str = Field(..., min_length=2, max_length=50, description="Operational role assignment")
    department: str = Field(..., min_length=2, max_length=50, description="Department name")
    supervisor_id: int | None = Field(default=None, description="Optional supervisor worker ID")
    supervisor_email: EmailStr | None = Field(default=None, description="Supervisor alert notification email")
    is_authorized: bool = Field(default=False, description="Hazardous zone authorization flag")


class WorkerUpdate(BaseModel):
    """Schema for modifying existing worker attributes."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=100)
    role: str | None = Field(default=None, min_length=2, max_length=50)
    department: str | None = Field(default=None, min_length=2, max_length=50)
    supervisor_id: int | None = None
    supervisor_email: EmailStr | None = None
    is_authorized: bool | None = None


class WorkerResponse(BaseModel):
    """Summary worker response representation."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    name: str
    role: str
    department: str
    supervisor_id: int | None = None
    supervisor_email: str | None = None
    face_photo_url: str | None = None
    is_authorized: bool
    has_face_embedding: bool = False
    created_at: datetime


class WorkerDetailResponse(WorkerResponse):
    """Full worker profile including proximity incident history."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    total_incidents: int = 0
    recent_incidents: list[IncidentResponse] = Field(default_factory=list)


class FaceEnrollResponse(BaseModel):
    """Response returned upon successful biometric portrait enrollment."""

    model_config = ConfigDict(extra="ignore")

    worker_id: int
    worker_name: str
    face_enrolled: bool
    embedding_dimensions: int
    face_photo_url: str | None = None
    message: str
