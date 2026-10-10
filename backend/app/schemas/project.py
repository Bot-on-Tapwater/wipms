"""Schemas for projects and the project wallet."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.schemas.user import UserBrief


class ProjectCreate(BaseModel):
    """Data needed to create a project."""

    name: str = Field(min_length=1, max_length=255)
    location: str = Field(min_length=1, max_length=255)
    description: str = ""


class ProjectUpdate(BaseModel):
    """Fields that can be edited on a project. All optional."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    location: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None


class ProjectRead(ORMModel):
    """Full project details with its team."""

    id: uuid.UUID
    name: str
    location: str
    description: str
    wallet_balance: Decimal
    is_completed: bool
    created_by: Optional[UserBrief]
    contractor_supervisors: List[UserBrief]
    consultant_supervisors: List[UserBrief]
    subcontractors: List[UserBrief]
    created_at: datetime
    updated_at: datetime


class AssignUsers(BaseModel):
    """List of user ids to add to a project role."""

    user_ids: List[uuid.UUID] = Field(min_length=1)


class WalletDeposit(BaseModel):
    """Add money to a project wallet (mocked until the bank API is ready)."""

    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    reference: str = Field(default="", max_length=255)


class WalletTransactionRead(ORMModel):
    """One deposit or payout on a project wallet."""

    id: uuid.UUID
    transaction_type: str
    amount: Decimal
    balance_after: Decimal
    reference: str
    created_at: datetime
