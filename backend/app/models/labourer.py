"""Labourers who get paid for works."""
import uuid
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.models.user import User
from app.models.work import WorkLabourer


class Labourer(TimestampMixin, Base):
    """
    A skilled or unskilled worker. Not a platform user (cannot log in).

    Attributes:
        id: UUID primary key
        name: Full name
        title: Trade of the labourer, e.g. masonry or carpenter
        national_id_number: National ID number, unique
        phone_number: M-Pesa number the labourer is paid on, starting with 254
        daily_rate: Pay per day worked in KES
        overhead_cost: Extra amount paid once per work in KES
        project_lifetime_approved_working_days: Days worked on all works that have been paid
        created_by_id: User who registered the labourer
        work_links: Works the labourer is assigned to, with the days worked on each
    """

    __tablename__ = "labourers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(50), index=True)
    national_id_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    phone_number: Mapped[str] = mapped_column(String(12))
    daily_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    overhead_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    project_lifetime_approved_working_days: Mapped[int] = mapped_column(Integer, default=0)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_by: Mapped[Optional[User]] = relationship()
    work_links: Mapped[List[WorkLabourer]] = relationship(
        back_populates="labourer", cascade="all, delete-orphan"
    )
