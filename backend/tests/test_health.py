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
