"""User database model for authentication, authorization, and RBAC."""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class UserRole(enum.StrEnum):
    """Role-based access control tier."""

    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    OPERATOR = "operator"


class User(Base, TimestampMixin):
    """Represents an authenticated dashboard user or safety supervisor.

    Stores authentication credentials (bcrypt hash), contact details, role tiers,
    and administrative privileges.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique user login email address",
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt cryptographic password hash",
    )
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role_enum", native_enum=False),
        default=UserRole.OPERATOR,
        nullable=False,
        index=True,
        comment="Access tier (admin, supervisor, operator)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Flag indicating whether account is permitted to authenticate",
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Master administrator bypass flag",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of most recent successful authentication",
    )

    def __repr__(self) -> str:
        """Provide readable debug representation of user account."""
        return (
            f"<User(id={self.id}, email={self.email!r}, role={self.role.value}, "
            f"active={self.is_active})>"
        )
