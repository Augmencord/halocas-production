"""HALOCAS Pydantic Data Validation and Serialization Schemas."""

from app.schemas.auth import LoginRequest, Token, TokenPayload, UserCreate, UserResponse
from app.schemas.common import MessageResponse, PaginationParams
from app.schemas.dashboard import ActiveAlertSummary, DashboardSummaryResponse
from app.schemas.incident import (
    AlertLogResponse,
    IncidentDetailResponse,
    IncidentResponse,
    IncidentStatsResponse,
)
from app.schemas.machine import MachineCreate, MachineResponse, MachineStatusUpdate
from app.schemas.worker import (
    FaceEnrollResponse,
    WorkerCreate,
    WorkerDetailResponse,
    WorkerResponse,
    WorkerUpdate,
)

__all__ = [
    "ActiveAlertSummary",
    "AlertLogResponse",
    "DashboardSummaryResponse",
    "FaceEnrollResponse",
    "IncidentDetailResponse",
    "IncidentResponse",
    "IncidentStatsResponse",
    "LoginRequest",
    "MachineCreate",
    "MachineResponse",
    "MachineStatusUpdate",
    "MessageResponse",
    "PaginationParams",
    "Token",
    "TokenPayload",
    "UserCreate",
    "UserResponse",
    "WorkerCreate",
    "WorkerDetailResponse",
    "WorkerResponse",
    "WorkerUpdate",
]
