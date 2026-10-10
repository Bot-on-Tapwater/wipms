"""Subcontracted works, the labourers assigned to them and proof-of-work images."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.choices import PaymentStatus
from app.core.config import settings
from app.core.database import Base, TimestampMixin
from app.models.user import User

if TYPE_CHECKING:
    from app.models.labourer import Labourer
    from app.models.project import Project


class Work(TimestampMixin, Base):
    """
    A piece of work (task) inside a project that labourers are paid for.

    Called ``SubcontractedWork`` in the old backend.

    Attributes:
        id: UUID primary key
        project_id: Project the work belongs to
        title: Short name of the work
        description: Optional description
        category: Type of work, e.g. bricklaying or woodworking
        cost_labor: Labour cost in KES
        cost_overhead: Overhead cost in KES
        assigned_subcontractor_id: Subcontractor doing the work
        created_by_id: User who created the work
        contractor_supervisor_comments: Comments from the contractor's supervisor
        consultant_supervisor_comments: Comments from the consultant's supervisor
        consultant_approval: Consultant's supervisor approved the work
        contractor_supervisor_approval: Contractor's supervisor approved the work
        attendance_approval: The labourers' days worked were confirmed
        cost_approval: Main contractor approved the cost
        contractor_supervisor_payment_approval: Contractor's supervisor approved the payment
        main_contractor_payment_approval: Main contractor approved the payment
        payment_requested: Payment has been requested
        payment_status: pending, approved or paid
        payment_requested_at: When payment was requested
        payment_approved_at: When payment was fully approved and sent out
        payment_completed_at: When every payment went through
        total_labourers_paid_out: Amount paid to labourers so far in KES
        retention_payment_requested: Release of the retention money has been requested
        retention_payment_approved: Main contractor approved the retention money
        retention_paid: Retention money has been paid
        is_completed: True once the work is finished
        labourer_links: Labourers on the work, with the days each worked
        images: Proof of work photos
    """

    __tablename__ = "works"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(50), index=True)
    cost_labor: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    cost_overhead: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    assigned_subcontractor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Comments
    contractor_supervisor_comments: Mapped[str] = mapped_column(Text, default="")
    consultant_supervisor_comments: Mapped[str] = mapped_column(Text, default="")

    # Approvals
    consultant_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    contractor_supervisor_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    attendance_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    cost_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    contractor_supervisor_payment_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    main_contractor_payment_approval: Mapped[bool] = mapped_column(Boolean, default=False)

    # Payment state
    payment_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    payment_status: Mapped[str] = mapped_column(String(20), default=PaymentStatus.PENDING.value)
    payment_requested_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    payment_approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    payment_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_labourers_paid_out: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0")
    )

    # Retention money
    retention_payment_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    retention_payment_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    retention_paid: Mapped[bool] = mapped_column(Boolean, default=False)

    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    project: Mapped["Project"] = relationship(back_populates="works")
    assigned_subcontractor: Mapped[Optional[User]] = relationship(
        foreign_keys=[assigned_subcontractor_id]
    )
    created_by: Mapped[Optional[User]] = relationship(foreign_keys=[created_by_id])
    labourer_links: Mapped[List["WorkLabourer"]] = relationship(
        back_populates="work", cascade="all, delete-orphan"
    )
    images: Mapped[List["WorkImage"]] = relationship(
        back_populates="work", cascade="all, delete-orphan"
    )

    @property
    def total_cost(self) -> Decimal:
        """
        Labour cost plus overhead cost.

        Returns:
            Decimal: Total cost in KES.
        """
        return Decimal(self.cost_labor or 0) + Decimal(self.cost_overhead or 0)

    @property
    def retention_money(self) -> Decimal:
        """
        Share of the total cost held back until the work is finished (10% by default).

        Returns:
            Decimal: Retention amount in KES, rounded to cents.
        """
        rate = Decimal(str(settings.RETENTION_RATE))
        return (self.total_cost * rate).quantize(Decimal("0.01"))

    def reset_payment_request(self) -> None:
        """
        Withdraw the payment request and both payment approvals.

        Used when the amounts to pay change, or a payout is refused, so the
        payment has to be requested and approved again with the new amounts.
        """
        self.payment_requested = False
        self.payment_requested_at = None
        self.contractor_supervisor_payment_approval = False
        self.main_contractor_payment_approval = False

    @property
    def is_fully_approved(self) -> bool:
        """
        True when both the contractor supervisor and consultant approved the work.

        Returns:
            bool: True when both approvals are given.
        """
        return self.contractor_supervisor_approval and self.consultant_approval


class WorkLabourer(TimestampMixin, Base):
    """
    Links a labourer to a work and stores the days they worked on it.

    In the old backend ``number_of_days_worked`` lived on the labourer itself,
    which broke when one labourer worked on several works. It now lives here.

    Attributes:
        work_id: The work (part of the primary key)
        labourer_id: The labourer (part of the primary key)
        days_worked: Days the labourer worked on this work
    """

    __tablename__ = "work_labourers"

    work_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("works.id", ondelete="CASCADE"), primary_key=True
    )
    labourer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("labourers.id", ondelete="CASCADE"), primary_key=True
    )
    days_worked: Mapped[int] = mapped_column(Integer, default=1)

    work: Mapped[Work] = relationship(back_populates="labourer_links")
    labourer: Mapped["Labourer"] = relationship(back_populates="work_links")

    @property
    def amount_due(self) -> Decimal:
        """
        What this labourer is owed for this work: daily rate x days + overhead.

        Returns:
            Decimal: Amount due in KES.
        """
        daily_rate = Decimal(self.labourer.daily_rate)
        overhead = Decimal(self.labourer.overhead_cost or 0)
        return daily_rate * self.days_worked + overhead


class WorkImage(TimestampMixin, Base):
    """
    A proof-of-work photo uploaded for a work.

    Attributes:
        id: UUID primary key
        work_id: Work the photo belongs to
        file_path: Where the file is stored, inside MEDIA_DIR
        description: Optional description
        created_by_id: User who uploaded the photo
    """

    __tablename__ = "work_images"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    work_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("works.id", ondelete="CASCADE"), index=True
    )
    file_path: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(String(255), default="")
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    work: Mapped[Work] = relationship(back_populates="images")
