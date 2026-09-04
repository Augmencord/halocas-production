"""Pydantic schemas for heavy mining equipment and machinery."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MachineCreate(BaseModel):
    """Schema for registering a new machine into the safety tracking fleet."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=2, max_length=100, description="Equipment name or unit callsign")
    type: str = Field(..., min_length=2, max_length=50, description="Machinery type (e.g., Haul Truck, Shovel)")
    zone: str = Field(..., min_length=2, max_length=50, description="Operational mining zone")
    status: str = Field(default="ACTIVE", max_length=20, description="Status (ACTIVE, MAINTENANCE, OFFLINE)")


class MachineStatusUpdate(BaseModel):
    """Schema for updating operational machine status."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(..., min_length=2, max_length=20, description="New operational status")


class MachineResponse(BaseModel):
    """Machine representation returned by API endpoints."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    name: str
    type: str
    zone: str
    status: str
    created_at: datetime
