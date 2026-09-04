"""Worker database model for mine personnel and biometric authorization."""

from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, JSON, Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.incident import Incident


class Worker(Base, TimestampMixin):
    """Represents mine personnel tracked by the Collision Avoidance System.

    Tracks identity, operational role, organizational hierarchy (supervisors),
    authorization credentials, and facial recognition biometric embeddings.
    """

    __tablename__ = "workers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Operational assignment, e.g., 'Authorized Mechanic' or 'General Worker'",
    )
    department: Mapped[str] = mapped_column(String(50), nullable=False)
    supervisor_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("workers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    supervisor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    face_embedding: Mapped[list[float] | None] = mapped_column(
        ARRAY(Float).with_variant(JSON, "sqlite"),
        nullable=True,
        comment="Facenet512 facial feature embedding vector (512 dimensions)",
    )
    face_photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_authorized: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Permitted within active heavy equipment hazard zones",
    )

    # Relationships
    supervisor: Mapped["Worker | None"] = relationship(
        "Worker",
        remote_side=[id],
        back_populates="subordinates",
    )
    subordinates: Mapped[list["Worker"]] = relationship(
        "Worker",
        back_populates="supervisor",
    )
    incidents: Mapped[list["Incident"]] = relationship(
        "Incident",
        back_populates="worker",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """Provide concise, informative debug representation of the worker."""
        return (
            f"<Worker(id={self.id}, name={self.name!r}, role={self.role!r}, "
            f"authorized={self.is_authorized})>"
        )
