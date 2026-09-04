"""Authentication, JWT token, and User Pydantic validation schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class Token(BaseModel):
    """JWT bearer access token response."""

    model_config = ConfigDict(extra="ignore")

    access_token: str = Field(..., description="Cryptographic JSON Web Token string")
    token_type: str = Field(default="bearer", description="Token authorization type")
    expires_in: int = Field(..., description="Token validity lifetime expressed in seconds")


class TokenPayload(BaseModel):
    """Decoded internal JWT claim payload."""

    model_config = ConfigDict(extra="ignore")

    sub: str | None = None
    role: str = "operator"
    exp: int | None = None


class LoginRequest(BaseModel):
    """User credentials submitted for session authentication."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(..., description="Registered account email address")
    password: str = Field(..., min_length=6, description="Account password")


class UserCreate(BaseModel):
    """Administrative request schema for registering a new user account."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(..., description="Unique email address for user login")
    password: str = Field(..., min_length=8, description="Initial account password (min 8 chars)")
    full_name: str = Field(..., min_length=2, max_length=100, description="Full legal name of user")
    role: UserRole = Field(default=UserRole.OPERATOR, description="Access tier (admin, supervisor, operator)")


class UserResponse(BaseModel):
    """User profile response representation."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
