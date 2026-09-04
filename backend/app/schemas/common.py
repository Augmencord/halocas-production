"""Common shared Pydantic schemas, pagination parameters, and response wrappers."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PaginationParams(BaseModel):
    """Standard URL query parameters for list offset-based pagination."""

    model_config = ConfigDict(extra="forbid")

    offset: int = Field(default=0, ge=0, description="Zero-indexed starting record index")
    limit: int = Field(default=50, ge=1, le=100, description="Maximum number of records to return")


class MessageResponse(BaseModel):
    """Generic status or notification response message."""

    model_config = ConfigDict(extra="ignore")

    message: str = Field(..., description="Human-readable informational or error message")
