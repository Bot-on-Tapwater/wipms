"""Records of every payment attempt (successful or failed)."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.models.labourer import Labourer
from app.models.project import Project
from app.models.user import User
from app.models.work import Work


class PaymentRecord(TimestampMixin, Base):
    """
    One payment attempt to a labourer or subcontractor.

    Failed attempts are stored too so reports can show them.

    Attributes:
        id: UUID primary key
        project_id: Project the money came from
        work_id: Work the payment was for
        labourer_id: Labourer paid, if the payment was to a labourer
        recipient_user_id: Subcontractor paid, if the payment was to a subcontractor
        initiated_by_id: User whose approval started the payment
        payment_type: labourer, subcontractor or retention
        recipient_name: Name of the person paid, kept even if they are deleted later
        recipient_phone: M-Pesa number the money was sent to
        amount_requested: Amount that should have been paid in KES
        amount_paid: Amount actually paid in KES (0 if the payment failed)
        successful: True if the payment went through
        provider: Payment provider used, e.g. mock
        provider_reference: Unique reference from the payment provider
        provider_response: Full response from the payment provider
        failure_reason: Why the payment failed, empty if it went through
        is_retried: True once a failed payment has been retried (the retry is a new record)
        paid_at: When the payment went through
    """

    __tablename__ = "payment_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    work_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("works.id", ondelete="CASCADE"), index=True
    )
    labourer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("labourers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    recipient_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    initiated_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    payment_type: Mapped[str] = mapped_column(String(20), index=True)
    recipient_name: Mapped[str] = mapped_column(String(150))
    recipient_phone: Mapped[str] = mapped_column(String(12))
    amount_requested: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    successful: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    provider: Mapped[str] = mapped_column(String(50))
    provider_reference: Mapped[str] = mapped_column(String(100), unique=True)
    provider_response: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    failure_reason: Mapped[str] = mapped_column(String(255), default="")
    # True once a failed payment has been retried (the retry is a new record)
    is_retried: Mapped[bool] = mapped_column(Boolean, default=False)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped[Project] = relationship()
    work: Mapped[Work] = relationship()
    labourer: Mapped[Optional[Labourer]] = relationship()
    recipient_user: Mapped[Optional[User]] = relationship(foreign_keys=[recipient_user_id])
