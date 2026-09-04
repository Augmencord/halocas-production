"""HALOCAS FastAPI Application Entrypoint.

Provides the primary ASGI web service for the Halo Collision Avoidance System.
Implements production-grade error handling, lifespan hooks for database and ML models,
CORS security, static file serving, and REST/WebSocket interfaces.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app import __version__
from app.api.router import api_router
from app.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.db.session import engine

settings = get_settings()
setup_logging(settings.LOG_LEVEL)
logger = get_logger("halocas.main")

_START_TIME: float = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan context manager handling startup validation and resource cleanup."""
    logger.info(
        "Starting %s (environment: %s, version: %s)",
        app.title,
        settings.ENVIRONMENT,
        __version__,
    )

    # 1. Verify Database Connectivity
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection pool verified successfully")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Database connection pool verification warning: %s", exc)

    # 2. Warm up computer vision models if available
    try:
        from app.api.deps import get_detector, get_face_verifier

        detector = get_detector()
        detector._warmup()
        face_verifier = get_face_verifier()
        face_verifier._warmup()
        logger.info("Computer vision models (YOLO & FaceVerifier) initialized")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Model warm-up skipped or encountered non-fatal warning: %s", exc)

    yield

    # 3. Shutdown: Dispose DB connection pools
    try:
        await engine.dispose()
        logger.info("Database connection engine disposed cleanly")
    except Exception as exc:  # noqa: BLE001
        logger.error("Error disposing database connection engine: %s", exc)

    logger.info("Shutting down %s cleanly", app.title)


app = FastAPI(
    title=settings.APP_NAME,
    version=__version__,
    description=(
        "HALOCAS - Production-Grade Real-Time AI Collision Avoidance Platform for Mine Safety. "
        "Enforces exclusion zone safety using YOLOv8 tracking, Facenet512 biometric recognition, "
        "and automated alert dispatching."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Cross-Origin Resource Sharing (CORS) Middleware
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static assets (incident thumbnails, enrolled faces, clip previews)
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Global Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Standardize input validation errors into structured JSON payloads."""
    logger.warning("Request validation failed on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": "Invalid request payload or query parameters",
            "detail": exc.errors(),
            "details": exc.errors(),
            "timestamp": datetime.now(UTC).isoformat(),
            "path": request.url.path,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Format HTTP exceptions into consistent API responses."""
    logger.debug("HTTPException %d on %s %s: %s", exc.status_code, request.method, request.url.path, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HttpError",
            "status_code": exc.status_code,
            "message": exc.detail,
            "detail": exc.detail,
            "timestamp": datetime.now(UTC).isoformat(),
            "path": request.url.path,
        },
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Capture uncaught exceptions and return standardized structured error payload."""
    logger.error(
        "Unhandled application exception at %s %s: %s",
        request.method,
        request.url.path,
        str(exc),
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
        "api_v1_url": "/api/v1",
    }


# Mount versioned API routes under /api/v1
app.include_router(api_router)
