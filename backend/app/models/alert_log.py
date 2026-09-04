"""Alert log database model tracking notification deliveries."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.incident import Incident


class DeliveryStatus(enum.StrEnum):
    """Notification dispatch lifecycle status."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


class AlertLog(Base, TimestampMixin):
    """Tracks automated notification attempts dispatched for safety incidents.

    Records target recipient emails, dispatch timestamps, retry attempts,
    and external email provider (Resend/SMTP) delivery diagnostics.
    """

    __tablename__ = "alert_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    delivery_status: Mapped[DeliveryStatus] = mapped_column(
        SAEnum(DeliveryStatus, name="alert_delivery_status_enum", native_enum=False),
        default=DeliveryStatus.PENDING,
        nullable=False,
        index=True,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Count of retransmission attempts executed",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Diagnostic failure message or provider error code",
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when delivery was acknowledged",
    )

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident", back_populates="alert_logs")

    def __repr__(self) -> str:
        """Provide concise debug representation of alert transmission log."""
        return (
            f"<AlertLog(id={self.id}, incident_id={self.incident_id}, "
            f"recipient={self.recipient_email!r}, status={self.delivery_status.value})>"
        )
