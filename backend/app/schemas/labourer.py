"""Schemas for labourers."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.constants.choices import LabourerTitle
from app.schemas.common import ORMModel, validate_phone_number


def validate_national_id(value: str) -> str:
    """
    National ID numbers must be digits only (5 to 20 characters).

    Args:
        value (str): National ID number to check.

    Returns:
        str: The stripped ID number.
    """
    value = value.strip()
    if not value.isdigit() or len(value) < 5 or len(value) > 20:
        raise ValueError("National ID number must contain 5 to 20 digits")
    return value


class LabourerCreate(BaseModel):
    """Data needed to register a labourer."""

    name: str = Field(min_length=2, max_length=100)
    title: LabourerTitle
    national_id_number: str
    phone_number: str
    daily_rate: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    overhead_cost: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        """
        Remove extra spaces around the name.

        Args:
            value (str): Name to check.

        Returns:
            str: The cleaned name.
        """
        return " ".join(value.split())

    @field_validator("national_id_number")
    @classmethod
    def check_id(cls, value: str) -> str:
        """
        National ID must be digits only.

        Args:
            value (str): National ID number to check.

        Returns:
            str: The cleaned ID number.
        """
        return validate_national_id(value)

    @field_validator("phone_number")
    @classmethod
    def check_phone(cls, value: str) -> str:
        """
        Payment phone number must be 254XXXXXXXXX.

        Args:
            value (str): Phone number to check.

        Returns:
            str: The cleaned phone number.
        """
        return validate_phone_number(value)


class LabourerUpdate(BaseModel):
    """Editable labourer fields. All optional."""

    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    title: Optional[LabourerTitle] = None
    phone_number: Optional[str] = None
    daily_rate: Optional[Decimal] = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    overhead_cost: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)

    @field_validator("phone_number")
    @classmethod
    def check_phone(cls, value: Optional[str]) -> Optional[str]:
        """
        Payment phone number must be 254XXXXXXXXX.

        Args:
            value (Optional[str]): Phone number to check, or None.

        Returns:
            Optional[str]: The cleaned phone number, or None.
        """
        if value is None:
            return value
        return validate_phone_number(value)


class LabourerRead(ORMModel):
    """Full labourer details."""

    id: uuid.UUID
    name: str
    title: str
    national_id_number: str
    phone_number: str
    daily_rate: Decimal
    overhead_cost: Decimal
    project_lifetime_approved_working_days: int
    created_at: datetime
    updated_at: datetime


class LabourerSuggestion(ORMModel):
    """Short labourer info for the name / ID number autocomplete dropdown."""

    id: uuid.UUID
    name: str
    national_id_number: str
    title: str
    phone_number: str
    daily_rate: Decimal
    overhead_cost: Decimal
