"""Schemas for users, registration, login and passwords."""
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, field_validator, model_validator

from app.constants.roles import Role
from app.schemas.common import (
    ORMModel,
    validate_letters_only,
    validate_password_length,
    validate_phone_number,
)


class UserRegister(BaseModel):
    """Data needed to create an account."""

    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    role: Role
    password: str
    re_enter_password: str

    @field_validator("first_name", "last_name")
    @classmethod
    def check_names(cls, value: str) -> str:
        """
        Names may only contain letters.

        Args:
            value (str): Name to check.

        Returns:
            str: The cleaned name.
        """
        return validate_letters_only(value)

    @field_validator("phone_number")
    @classmethod
    def check_phone(cls, value: str) -> str:
        """
        Phone number must be 254XXXXXXXXX.

        Args:
            value (str): Phone number to check.

        Returns:
            str: The cleaned phone number.
        """
        return validate_phone_number(value)

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        """
        Password must be at least 8 characters.

        Args:
            value (str): Password to check.

        Returns:
            str: The password unchanged.
        """
        return validate_password_length(value)

    @model_validator(mode="after")
    def check_passwords_match(self) -> "UserRegister":
        """
        Both password fields must be the same.

        Returns:
            UserRegister: The validated request body.
        """
        if self.password != self.re_enter_password:
            raise ValueError("Passwords do not match")
        return self


class UserUpdate(BaseModel):
    """Fields a user may change on their own profile. All are optional."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[Role] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def check_names(cls, value: Optional[str]) -> Optional[str]:
        """
        Names may only contain letters.

        Args:
            value (Optional[str]): Name to check, or None.

        Returns:
            Optional[str]: The cleaned name, or None.
        """
        if value is None:
            return value
        return validate_letters_only(value)

    @field_validator("phone_number")
    @classmethod
    def check_phone(cls, value: Optional[str]) -> Optional[str]:
        """
        Phone number must be 254XXXXXXXXX.

        Args:
            value (Optional[str]): Phone number to check, or None.

        Returns:
            Optional[str]: The cleaned phone number, or None.
        """
        if value is None:
            return value
        return validate_phone_number(value)


class UserRead(ORMModel):
    """Public information about a user."""

    id: uuid.UUID
    first_name: str
    last_name: str
    full_name: str
    email: EmailStr
    phone_number: str
    role: str
    is_active: bool
    created_at: datetime


class UserBrief(ORMModel):
    """Short user info used inside other objects (projects, works)."""

    id: uuid.UUID
    full_name: str
    email: EmailStr
    role: str


class LoginRequest(BaseModel):
    """Email and password login."""

    email: EmailStr
    password: str


class TokenPair(BaseModel):
    """Access and refresh tokens returned after login."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginResponse(TokenPair):
    """Login result: tokens, the user and their permissions."""

    user: UserRead
    permissions: List[str]


class RefreshRequest(BaseModel):
    """Body for refreshing tokens or logging out."""

    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    """Body for requesting a password reset email."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Body for setting a new password using a reset token."""

    user_id: uuid.UUID
    token: str
    new_password: str
    re_enter_password: str

    @field_validator("new_password")
    @classmethod
    def check_password(cls, value: str) -> str:
        """
        Password must be at least 8 characters.

        Args:
            value (str): Password to check.

        Returns:
            str: The password unchanged.
        """
        return validate_password_length(value)

    @model_validator(mode="after")
    def check_passwords_match(self) -> "ResetPasswordRequest":
        """
        Both password fields must be the same.

        Returns:
            ResetPasswordRequest: The validated request body.
        """
        if self.new_password != self.re_enter_password:
            raise ValueError("Passwords do not match")
        return self


class ChangePasswordRequest(BaseModel):
    """Body for changing the password while logged in."""

    current_password: str
    new_password: str
    re_enter_password: str

    @field_validator("new_password")
    @classmethod
    def check_password(cls, value: str) -> str:
        """
        Password must be at least 8 characters.

        Args:
            value (str): Password to check.

        Returns:
            str: The password unchanged.
        """
        return validate_password_length(value)

    @model_validator(mode="after")
    def check_passwords_match(self) -> "ChangePasswordRequest":
        """
        Both new password fields must be the same.

        Returns:
            ChangePasswordRequest: The validated request body.
        """
        if self.new_password != self.re_enter_password:
            raise ValueError("Passwords do not match")
        return self
