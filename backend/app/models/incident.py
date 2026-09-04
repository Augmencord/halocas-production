"""Incident database model recording proximity breaches and safety hazards."""

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.alert_log import AlertLog
    from app.models.machine import Machine
    from app.models.worker import Worker


class IncidentSeverity(enum.StrEnum):
    """Classification of spatial proximity breach severity."""

    CRITICAL = "CRITICAL"  # Penetration of critical danger radius (< 3m)
    WARNING = "WARNING"    # Breach of warning boundary (< 10m)
    CAUTION = "CAUTION"    # Advisory proximity notification


class Incident(Base, TimestampMixin):
    """Records real-time safety violations and near-miss proximity incidents.

    Stores spatial metrics (distance, closing velocity), involved machinery,
    detected personnel, cloud video recording URLs, and automated notification status.
    """

    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    machine_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("machines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    worker_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("workers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    worker_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    distance_meters: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Estimated Euclidean distance in meters between worker and equipment",
    )
    severity: Mapped[IncidentSeverity] = mapped_column(
        SAEnum(IncidentSeverity, name="incident_severity_enum", native_enum=False),
        nullable=False,
        index=True,
    )
    closing_velocity: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Relative approach speed in meters per second",
    )
    clip_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="URL pointing to incident recording stored on Cloudflare R2",
    )
    clip_duration_sec: Mapped[float] = mapped_column(
        Float,
        default=5.0,
        nullable=False,
        comment="Duration of captured incident video in seconds",
    )
    supervisor_notified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    supervisor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notification_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    face_match_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Cosine similarity / confidence score from DeepFace identification",
    )
    zone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    machine: Mapped["Machine"] = relationship("Machine", back_populates="incidents")
    worker: Mapped["Worker | None"] = relationship("Worker", back_populates="incidents")
    alert_logs: Mapped[list["AlertLog"]] = relationship(
        "AlertLog",
        back_populates="incident",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """Provide readable debug representation of incident record."""
        return (
            f"<Incident(id={self.id}, machine_id={self.machine_id}, worker_id={self.worker_id}, "
            f"distance={self.distance_meters}m, severity={self.severity.value})>"
        )
