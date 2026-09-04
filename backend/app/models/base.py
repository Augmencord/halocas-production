"""Base declarative models and mixins for SQLAlchemy ORM."""

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative root class for all HALOCAS models."""

    def __repr__(self) -> str:
        """Provide readable string representation of model instances."""
        attrs = [f"{k}={v!r}" for k, v in self.__dict__.items() if not k.startswith("_")]
        return f"<{self.__class__.__name__}({', '.join(attrs)})>"


class TimestampMixin:
    """Mixin adding timezone-aware creation and modification timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
