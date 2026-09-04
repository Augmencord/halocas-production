"""Tests for application configuration and environment settings."""

import os
from unittest.mock import patch

from app.config import Settings, get_settings


def test_default_settings() -> None:
    """Verify default values comply with HALOCAS safety requirements."""
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.APP_NAME == "HALOCAS - Collision Avoidance System"
    assert settings.DATABASE_URL == "postgresql+asyncpg://localhost/halocas"
    assert settings.SAFETY_CRITICAL_DISTANCE == 3.0
    assert settings.SAFETY_WARNING_DISTANCE == 10.0
    assert settings.PIXELS_PER_METER == 20.0
    assert settings.ALERT_COOLDOWN_SECONDS == 60
    assert settings.CLIP_DURATION_SECONDS == 5
    assert settings.FPS == 30
    assert settings.R2_BUCKET == "halocas-clips"
    assert settings.SMTP_SENDER == "alerts@halocas.safety"
    assert settings.JWT_ALGORITHM == "HS256"
    assert settings.JWT_EXPIRY_MINUTES == 30
    assert settings.YOLO_MODEL_PATH == "yolov8n.pt"
    assert settings.DEEPFACE_MODEL == "Facenet512"


def test_custom_settings_override() -> None:
    """Verify environment variables properly override defaults."""
    custom_env = {
        "ENVIRONMENT": "production",
        "PORT": "9000",
        "DATABASE_URL": "postgresql+asyncpg://prod_user:prod_pass@neon.tech/halocas_prod",
        "SAFETY_CRITICAL_DISTANCE": "2.5",
        "SAFETY_WARNING_DISTANCE": "8.0",
        "PIXELS_PER_METER": "25.0",
        "R2_BUCKET": "production-clips",
    }
    with patch.dict(os.environ, custom_env, clear=False):
        settings = Settings()
        assert settings.ENVIRONMENT == "production"
        assert settings.PORT == 9000
        assert settings.DATABASE_URL == "postgresql+asyncpg://prod_user:prod_pass@neon.tech/halocas_prod"
        assert settings.SAFETY_CRITICAL_DISTANCE == 2.5
        assert settings.SAFETY_WARNING_DISTANCE == 8.0
        assert settings.PIXELS_PER_METER == 25.0
        assert settings.R2_BUCKET == "production-clips"


def test_get_settings_cached() -> None:
    """Verify get_settings returns a cached instance."""
    instance_1 = get_settings()
    instance_2 = get_settings()
    assert instance_1 is instance_2
