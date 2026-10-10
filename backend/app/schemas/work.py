"""Schemas for works, their labourers, comments, approvals and images."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.constants.choices import TaskCategory
from app.schemas.common import ORMModel
from app.schemas.labourer import LabourerCreate, LabourerRead
from app.schemas.user import UserBrief


class WorkCreate(BaseModel):
    """Data needed to create a work under a project."""

    project_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    category: TaskCategory
    cost_labor: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    cost_overhead: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    assigned_subcontractor_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Ignored when a subcontractor creates the work (they are assigned automatically)",
    )


class WorkUpdate(BaseModel):
    """Editable work fields. All optional. Locked once the work is paid."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[TaskCategory] = None
    cost_labor: Optional[Decimal] = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    cost_overhead: Optional[Decimal] = Field(default=None, ge=0, max_digits=14, decimal_places=2)


class WorkRead(ORMModel):
    """Full work details including approvals and payment state."""

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str
    category: str
    cost_labor: Decimal
    cost_overhead: Decimal
    total_cost: Decimal
    retention_money: Decimal
    assigned_subcontractor: Optional[UserBrief]
    created_by: Optional[UserBrief]
    contractor_supervisor_comments: str
    consultant_supervisor_comments: str
    consultant_approval: bool
    contractor_supervisor_approval: bool
    attendance_approval: bool
    cost_approval: bool
    contractor_supervisor_payment_approval: bool
    main_contractor_payment_approval: bool
    is_fully_approved: bool
    payment_requested: bool
    payment_status: str
    payment_requested_at: Optional[datetime]
    payment_approved_at: Optional[datetime]
    payment_completed_at: Optional[datetime]
    total_labourers_paid_out: Decimal
    retention_payment_requested: bool
    retention_payment_approved: bool
    retention_paid: bool
    is_completed: bool
    created_at: datetime
    updated_at: datetime


class AssignSubcontractor(BaseModel):
    """Body for assigning a subcontractor to a work."""

    subcontractor_id: uuid.UUID


class AssignLabourer(BaseModel):
    """Body for assigning an existing labourer to a work."""

    labourer_id: uuid.UUID
    days_worked: int = Field(default=1, ge=1, le=366)


class CreateAndAssignLabourer(LabourerCreate):
    """Register a new labourer and assign them to the work in one step."""

    days_worked: int = Field(default=1, ge=1, le=366)


class UpdateDaysWorked(BaseModel):
    """Body for changing the days a labourer worked on a work."""

    days_worked: int = Field(ge=1, le=366)


class WorkLabourerRead(ORMModel):
    """A labourer on a work, with days worked and amount due."""

    labourer: LabourerRead
    days_worked: int
    amount_due: Decimal


class CommentCreate(BaseModel):
    """Body for adding a supervisor comment."""

    comment: str = Field(min_length=1, max_length=5000)


ApprovalType = Literal["consultant", "contractor_supervisor", "attendance", "cost"]


class ApprovalChange(BaseModel):
    """Body for approving or disapproving a work."""

    approval_type: ApprovalType
    approved: bool


class WorkImageRead(ORMModel):
    """A proof-of-work image (download it from ``file_url``)."""

    id: uuid.UUID
    work_id: uuid.UUID
    description: str
    created_at: datetime
    file_url: str = ""
