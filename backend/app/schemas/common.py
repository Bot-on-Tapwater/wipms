"""Shared schema helpers and validators."""
from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    """Base schema that can be built directly from SQLAlchemy objects."""

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """Simple response containing a message for the user."""

    message: str


def validate_phone_number(value: str) -> str:
    """
    Check a Kenyan mobile number is in the format 254XXXXXXXXX.

    Args:
        value (str): Phone number to check.

    Returns:
        str: The cleaned phone number.
    """
    if not value.isdigit() or not value.startswith("254") or len(value) != 12:
        raise ValueError("Phone number must start with '254' followed by 9 digits")
    return value


def validate_letters_only(value: str) -> str:
    """
    Check a name contains only letters, and capitalise it.

    Args:
        value (str): Text to check.

    Returns:
        str: The stripped text.
    """
    value = value.strip()
    if not value.isalpha():
        raise ValueError("Name should only contain letters")
    return value.capitalize()


def validate_password_length(value: str) -> str:
    """
    Check a password is at least 8 characters long.

    Args:
        value (str): Password to check.

    Returns:
        str: The password unchanged.
    """
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long")
    return value
