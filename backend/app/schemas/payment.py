"""Schemas for payment requests, approvals, retention and payment records."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel

from app.schemas.common import ORMModel
from app.schemas.work import WorkRead

PaymentApprovalType = Literal["contractor_supervisor", "main_contractor"]


class PaymentApproval(BaseModel):
    """Body for giving one of the two payment approvals."""

    approval_type: PaymentApprovalType


class PaymentOutcomeRead(BaseModel):
    """Result of a payment approval, retry or retention payment."""

    message: str
    payments_made: int
    payments_failed: int
    work: WorkRead


class PaymentSummary(BaseModel):
    """Breakdown of what a work will pay (or has paid) to whom."""

    work_id: uuid.UUID
    total_cost: Decimal
    cost_labor: Decimal
    cost_overhead: Decimal
    total_labour_due: Decimal
    retention_money: Decimal
    subcontractor_amount: Decimal
    total_labourers_paid_out: Decimal
    usable_wallet_balance: Decimal
    payment_status: str
    failed_payments_outstanding: int


class PaymentRecordRead(ORMModel):
    """One payment attempt (successful or failed)."""

    id: uuid.UUID
    project_id: uuid.UUID
    work_id: uuid.UUID
    labourer_id: Optional[uuid.UUID]
    recipient_user_id: Optional[uuid.UUID]
    initiated_by_id: Optional[uuid.UUID]
    payment_type: str
    recipient_name: str
    recipient_phone: str
    amount_requested: Decimal
    amount_paid: Decimal
    successful: bool
    provider: str
    provider_reference: str
    failure_reason: str
    is_retried: bool
    paid_at: Optional[datetime]
    created_at: datetime
