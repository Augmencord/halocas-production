"""Tests for application health and status endpoints."""

import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient) -> None:
    """Verify /health endpoint returns healthy status and metadata."""
    response = await async_client.get("/health")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "halocas-backend"
    assert "version" in data
    assert "environment" in data
    assert data["uptime_seconds"] >= 0.0
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient) -> None:
    """Verify root endpoint provides API information and docs link."""
    response = await async_client.get("/")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["docs_url"] == "/docs"
    assert data["health_url"] == "/health"


@pytest.mark.asyncio
async def test_subsystem_status_endpoint(async_client: AsyncClient) -> None:
    """Verify /api/v1/status endpoint reports subsystem operational readiness."""
    response = await async_client.get("/api/v1/status")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "operational"
    assert "subsystems" in data
    subsystems = data["subsystems"]
    assert subsystems["vision_engine"] == "ready"
    assert subsystems["proximity_detector"] == "ready"
    assert subsystems["alert_dispatcher"] == "ready"
    assert subsystems["storage"] == "ready"


@pytest.mark.asyncio
async def test_not_found_endpoint(async_client: AsyncClient) -> None:
    """Verify that non-existent routes return standard 404 response."""
    response = await async_client.get("/non-existent-route")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_application_lifespan() -> None:
    """Verify application startup verification and shutdown cleanup."""
    from unittest.mock import MagicMock, patch

    from app.main import app, lifespan

    mock_detector = MagicMock()
    mock_face_verifier = MagicMock()

    with (
        patch("app.api.deps.get_detector", return_value=mock_detector),
        patch("app.api.deps.get_face_verifier", return_value=mock_face_verifier),
    ):
        async with lifespan(app):
            assert app.title is not None
            assert len(app.routes) > 0

    mock_detector._warmup.assert_called_once()
    mock_face_verifier._warmup.assert_called_once()


@pytest.mark.asyncio
async def test_global_exception_handler() -> None:
    """Verify unhandled exception handler returns standardized 500 JSON response."""
    from unittest.mock import MagicMock

    from fastapi import Request

    from app.main import global_exception_handler

    mock_request = MagicMock(spec=Request)
    mock_request.method = "GET"
    mock_request.url.path = "/api/v1/trigger-error"

    response = await global_exception_handler(mock_request, RuntimeError("Simulated crash"))
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert b"InternalServerError" in response.body
