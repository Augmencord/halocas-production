"""HALOCAS Configuration Module.

Loads and validates all configuration parameters from environment variables
using pydantic-settings. Provides sensible defaults for local development
and strict typing for production safety enforcement.
"""

import secrets
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and environmental configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # General Application Settings
    APP_NAME: str = Field(default="HALOCAS - Collision Avoidance System", description="Name of application")
    ENVIRONMENT: str = Field(default="development", description="Execution environment (development, staging, production)")
    DEBUG: bool = Field(default=False, description="Debug mode flag")
    PORT: int = Field(default=8000, description="Server listening port")
    LOG_LEVEL: str = Field(default="INFO", description="Global logging verbosity")

    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://localhost/halocas",
        description="Async PostgreSQL connection string",
    )

    # Cloudflare R2 Object Storage Configuration
    R2_ENDPOINT: str | None = Field(
        default=None,
        description="Cloudflare R2 S3-compatible endpoint URL",
    )
    R2_ACCESS_KEY: str | None = Field(
        default=None,
        description="Cloudflare R2 access key ID",
    )
    R2_SECRET_KEY: str | None = Field(
        default=None,
        description="Cloudflare R2 secret access key",
    )
    R2_BUCKET: str = Field(
        default="halocas-clips",
        description="Bucket name for storing incident video clips",
    )

    # Email Alert Configuration (Resend)
    RESEND_API_KEY: str | None = Field(
        default=None,
        description="Resend API key for automated safety incident dispatch",
    )
    SMTP_SENDER: str = Field(
        default="alerts@halocas.safety",
        description="Sender email address for safety alerts",
    )

    # Authentication & Security
    JWT_SECRET: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Secret key for JWT verification and signing",
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="Cryptographic algorithm for JWT encoding",
    )
    JWT_EXPIRY_MINUTES: int = Field(
        default=30,
        description="JWT token validity period in minutes",
    )

    # Computer Vision & Deep Learning Models
    YOLO_MODEL_PATH: str = Field(
        default="yolov8n.pt",
        description="Path or model identifier for YOLO object detection weights",
    )
    DEEPFACE_MODEL: str = Field(
        default="Facenet512",
        description="Model architecture identifier for facial recognition embeddings",
    )

    # Safety Distance Parameters & Calibration
    SAFETY_CRITICAL_DISTANCE: float = Field(
        default=3.0,
        description="Threshold distance in meters triggering critical red alert",
    )
    SAFETY_WARNING_DISTANCE: float = Field(
        default=10.0,
        description="Threshold distance in meters triggering cautionary yellow alert",
    )
    PIXELS_PER_METER: float = Field(
        default=20.0,
        description="Spatial calibration ratio converting pixel distance to real-world meters",
    )
    ALERT_COOLDOWN_SECONDS: int = Field(
        default=60,
        description="Suppression window preventing duplicate alerts for identical worker-machine pair",
    )
    CLIP_DURATION_SECONDS: int = Field(
        default=5,
        description="Target duration of recorded incident video clips in seconds",
    )
    FPS: int = Field(
        default=30,
        description="Target frame rate for video ingest and processing",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retrieve cached application settings instance.

    Returns:
        Settings: Validated settings singleton.
    """
    return Settings()
