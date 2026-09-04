"""Pytest fixtures for HALOCAS backend testing."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import app


@pytest.fixture
def test_settings() -> Settings:
    """Provide deterministic test settings."""
    return Settings(
        ENVIRONMENT="testing",
        DEBUG=True,
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        JWT_SECRET="test_secret_key_for_testing_purposes_only_12345",
        SAFETY_CRITICAL_DISTANCE=3.0,
        SAFETY_WARNING_DISTANCE=10.0,
        PIXELS_PER_METER=20.0,
        ALERT_COOLDOWN_SECONDS=60,
        CLIP_DURATION_SECONDS=5,
        FPS=30,
    )


@pytest.fixture
async def async_client() -> AsyncIterator[AsyncClient]:
    """Provide an asynchronous HTTP test client bound to the FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
