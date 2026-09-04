"""API route controllers package."""

from app.api.routes.auth import router as auth_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.incidents import router as incidents_router
from app.api.routes.machines import router as machines_router
from app.api.routes.telemetry import router as telemetry_router
from app.api.routes.workers import router as workers_router

__all__ = [
    "auth_router",
    "dashboard_router",
    "incidents_router",
    "machines_router",
    "telemetry_router",
    "workers_router",
]
