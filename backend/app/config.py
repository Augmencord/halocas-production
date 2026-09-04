"""HALOCAS Configuration Module.

This module defines the centralized application configuration for the Halo Collision
Avoidance System (HALOCAS). All settings are loaded from environment variables using
`pydantic-settings.BaseSettings` with strict typing, runtime validation, and sensible
defaults tailored for local development and safety-critical production mining deployments.
"""

import secrets
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and environmental configuration for HALOCAS.

    Attributes:
        APP_NAME: Display name of the platform.
        ENVIRONMENT: Current deployment stage ('development', 'staging', 'production').
        DEBUG: Boolean flag enabling verbose debug outputs and autoreload behaviors.
        PORT: Network port the ASGI web server binds to.
        LOG_LEVEL: Logging verbosity ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL').
        DATABASE_URL: PostgreSQL connection URI with asyncpg dialect.
        R2_ENDPOINT: S3-compatible Cloudflare R2 endpoint URL for incident video clips.
        R2_ACCESS_KEY: Cloudflare R2 access key identifier.
        R2_SECRET_KEY: Cloudflare R2 secret access key.
        R2_BUCKET: Cloudflare R2 storage bucket designation for safety recordings.
        RESEND_API_KEY: Authentication token for Resend transactional email dispatch.
        SMTP_SENDER: Dedicated email address emitting automated safety breach alerts.
        JWT_SECRET: Cryptographic secret key used to sign and verify JSON Web Tokens.
        JWT_ALGORITHM: Symmetric cryptographic algorithm utilized for JWT signing.
        JWT_EXPIRY_MINUTES: Lifetime in minutes for issued access tokens.
        YOLO_MODEL_PATH: Local filesystem path or pretrained model identifier for YOLOv8.
        DEEPFACE_MODEL: Facial recognition model architecture name (e.g., 'Facenet512').
        SAFETY_CRITICAL_DISTANCE: Spatial threshold in meters triggering imminent danger alert.
        SAFETY_WARNING_DISTANCE: Spatial threshold in meters triggering proximity caution alert.
        PIXELS_PER_METER: Optical calibration factor converting pixel measurements to meters.
        ALERT_COOLDOWN_SECONDS: Minimum suppression duration preventing redundant notifications.
        CLIP_DURATION_SECONDS: Length in seconds of captured incident video recordings.
        FPS: Expected video feed frame rate for time-series distance analysis.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # General Application Settings
    APP_NAME: str = Field(
        default="HALOCAS - Collision Avoidance System",
        description="Official title and service identifier of the platform.",
    )
    ENVIRONMENT: str = Field(
        default="development",
        description="Deployment target environment (development, staging, production).",
    )
    DEBUG: bool = Field(
        default=False,
        description="Flag enabling verbose debugging mechanisms.",
    )
    PORT: int = Field(
        default=8000,
        description="Network port on which the web server listens.",
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Global logging verbosity level.",
    )

    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://localhost/halocas",
        description="Asynchronous PostgreSQL connection URI using asyncpg driver.",
    )

    # Cloudflare R2 Object Storage Configuration
    R2_ENDPOINT: str | None = Field(
        default=None,
        description="Cloudflare R2 S3-compatible endpoint URL for video clip storage.",
    )
    R2_ACCESS_KEY: str | None = Field(
        default=None,
        description="Cloudflare R2 access key ID.",
    )
    R2_SECRET_KEY: str | None = Field(
        default=None,
        description="Cloudflare R2 secret access key.",
    )
    R2_BUCKET: str = Field(
        default="halocas-clips",
        description="Designated storage bucket name for recorded incident clips.",
    )

    # Email Alert Configuration (Resend)
    RESEND_API_KEY: str | None = Field(
        default=None,
        description="Resend API authentication key for automated safety alert emails.",
    )
    SMTP_SENDER: str = Field(
        default="alerts@halocas.safety",
        description="Outbound sender email address for critical safety alerts.",
    )

    # Authentication & Security
    JWT_SECRET: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Cryptographic secret used for signing and verifying JWT tokens.",
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="Cryptographic hashing algorithm used for JWT token signing.",
    )
    JWT_EXPIRY_MINUTES: int = Field(
        default=30,
        description="Lifespan of issued JSON Web Tokens expressed in minutes.",
    )

    # Computer Vision & Deep Learning Models
    YOLO_MODEL_PATH: str = Field(
        default="yolov8n.pt",
        description="File path or repository identifier for the YOLOv8 object detection model.",
    )
    DEEPFACE_MODEL: str = Field(
        default="Facenet512",
        description="Neural network architecture used for facial recognition embedding extraction.",
    )

    # Safety Distance Parameters & Calibration
    SAFETY_CRITICAL_DISTANCE: float = Field(
        default=3.0,
        description="Proximity threshold in meters triggering critical red collision alert.",
    )
    SAFETY_WARNING_DISTANCE: float = Field(
        default=10.0,
        description="Proximity threshold in meters triggering cautionary yellow advisory alert.",
    )
    PIXELS_PER_METER: float = Field(
        default=20.0,
        description="Calibration ratio translating pixel coordinate distances to real-world meters.",
    )
    ALERT_COOLDOWN_SECONDS: int = Field(
        default=60,
        description="Cooldown window in seconds preventing repetitive alerts for identical entities.",
    )
    CLIP_DURATION_SECONDS: int = Field(
        default=5,
        description="Temporal length in seconds of safety breach video recordings.",
    )
    FPS: int = Field(
        default=30,
        description="Video stream frame rate processed for proximity and trajectory calculations.",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retrieve and cache the singleton application settings instance.

    Uses `functools.lru_cache` to ensure environment variables and .env configuration
    files are parsed only once during application runtime.

    Returns:
        Settings: Validated configuration settings singleton.
    """
    return Settings()
