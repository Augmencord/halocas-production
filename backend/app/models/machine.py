"""Machine database model for heavy mining equipment."""

from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.incident import Incident


class Machine(Base, TimestampMixin):
    """Represents heavy mining equipment monitored by the Collision Avoidance System.

    Monitors haul trucks, excavators, loaders, dozers, and continuous mining equipment,
    recording operational zone assignments and telemetry state.
    """

    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Machinery category: 'Haul Truck', 'Excavator', 'Wheel Loader', 'Dozer'",
    )
    zone: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Active operating sector: e.g. 'Zone-A Pit', 'Zone-B Crusher'",
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="active",
        nullable=False,
        comment="Operational status: 'active', 'idle', 'maintenance', 'offline'",
    )

    # Relationships
    incidents: Mapped[list["Incident"]] = relationship(
        "Incident",
        back_populates="machine",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """Provide concise debug representation of the machine entity."""
        return (
            f"<Machine(id={self.id}, name={self.name!r}, type={self.type!r}, "
            f"zone={self.zone!r}, status={self.status!r})>"
        )
