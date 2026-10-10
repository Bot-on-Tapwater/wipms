"""User accounts and revoked (logged out) tokens."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class User(TimestampMixin, Base):
    """
    A person who logs into the platform. Their ``role`` decides permissions.

    Attributes:
        id: UUID primary key
        first_name: First name
        last_name: Last name
        email: Login email, unique
        phone_number: Phone number starting with 254
        role: Role of the user, e.g. main-contractor or subcontractor
        hashed_password: Hash of the password (the password itself is never stored)
        is_active: Inactive users cannot log in
        token_version: Raised on a password change or reset to cancel older tokens
        password_reset_token: Hash of the latest password reset token, if any
        password_reset_expires_at: When the password reset token stops working
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone_number: Mapped[str] = mapped_column(String(12))
    role: Mapped[str] = mapped_column(String(30), index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Written into every token. Raising it (on a password change or reset)
    # makes all tokens issued before that moment invalid.
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    password_reset_token: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    password_reset_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    @property
    def full_name(self) -> str:
        """
        Return the user's first and last name together.

        Returns:
            str: First and last name separated by a space.
        """
        return f"{self.first_name} {self.last_name}"


class RevokedToken(TimestampMixin, Base):
    """
    A refresh token that was logged out and must not be used again.

    Attributes:
        jti: Unique ID of the token (primary key)
        expires_at: When the token would have expired
    """

    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
