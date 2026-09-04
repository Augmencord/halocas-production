"""HALOCAS FastAPI Application Entrypoint.

Provides the primary ASGI web service for the Halo Collision Avoidance System.
Implements production-grade error handling, lifespan hooks, structured logging,
and REST/WebSocket interfaces.
"""

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.router import api_router
from app.config import get_settings
from app.core.logging import get_logger, setup_logging

settings = get_settings()
setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)

_START_TIME: float = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan context manager for startup and shutdown procedures."""
    logger.info(
        "Starting %s",
        app.title,
        extra={"environment": settings.ENVIRONMENT, "version": __version__},
    )
    yield
    logger.info("Shutting down %s cleanly", app.title)


app = FastAPI(
    title=settings.APP_NAME,
    version=__version__,
    description="HALOCAS - Real-time AI Collision Avoidance Platform for Mine Safety",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Cross-Origin Resource Sharing (CORS) Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production via environment configuration
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Capture uncaught exceptions and return standardized structured error payload."""
    logger.error(
        f"Unhandled application exception at {request.method} {request.url.path}: {exc!s}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected server error occurred. Safety systems logged this incident.",
            "timestamp": datetime.now(UTC).isoformat(),
            "path": request.url.path,
        },
    )


@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description="Returns current service health, uptime, environment, and system timestamp.",
    tags=["System"],
)
async def health_check() -> dict[str, Any]:
    """Execute active health probe for container orchestrator and load balancers."""
    uptime_seconds = round(time.time() - _START_TIME, 2)
    return {
        "status": "healthy",
        "service": "halocas-backend",
        "version": __version__,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": uptime_seconds,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Root Information",
    description="Returns platform identity and service documentation pointers.",
    tags=["System"],
)
async def root() -> dict[str, str]:
    """Return welcome payload with active API documentation links."""
    return {
        "name": settings.APP_NAME,
        "version": __version__,
        "docs_url": "/docs",
        "health_url": "/health",
    }


# Mount versioned API routes
app.include_router(api_router)
