"""Projects, their team members and the project wallet."""
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Column, ForeignKey, Numeric, String, Table, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.models.user import User

if TYPE_CHECKING:
    from app.models.work import Work


project_contractor_supervisors = Table(
    "project_contractor_supervisors",
    Base.metadata,
    Column("project_id", Uuid, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)

project_consultant_supervisors = Table(
    "project_consultant_supervisors",
    Base.metadata,
    Column("project_id", Uuid, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)

project_subcontractors = Table(
    "project_subcontractors",
    Base.metadata,
    Column("project_id", Uuid, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


class Project(TimestampMixin, Base):
    """
    A construction project. Works are created under a project.

    Attributes:
        id: UUID primary key
        name: Name of the project
        location: Physical location
        description: Optional description
        wallet_balance: Money in the project wallet in KES, used to pay for works
        is_completed: True once the project is finished
        created_by_id: Main contractor who created the project
        contractor_supervisors: Contractor's supervisors on the project
        consultant_supervisors: Consultant's supervisors on the project
        subcontractors: Subcontractors on the project
        works: Works created under the project
        wallet_transactions: Every deposit and payout of the wallet
    """

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), index=True)
    location: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    wallet_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_by: Mapped[Optional[User]] = relationship(foreign_keys=[created_by_id])
    contractor_supervisors: Mapped[List[User]] = relationship(
        secondary=project_contractor_supervisors
    )
    consultant_supervisors: Mapped[List[User]] = relationship(
        secondary=project_consultant_supervisors
    )
    subcontractors: Mapped[List[User]] = relationship(secondary=project_subcontractors)
    works: Mapped[List["Work"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    wallet_transactions: Mapped[List["WalletTransaction"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class WalletTransaction(TimestampMixin, Base):
    """
    A deposit into or payout from a project's wallet (audit trail).

    Attributes:
        id: UUID primary key
        project_id: Project whose wallet changed
        transaction_type: deposit or payout
        amount: Amount in KES (always positive)
        balance_after: Wallet balance right after this transaction
        reference: What the money was for, e.g. a payment reference
        created_by_id: User who made the deposit or payout
    """

    __tablename__ = "wallet_transactions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    transaction_type: Mapped[str] = mapped_column(String(20))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    reference: Mapped[str] = mapped_column(String(255), default="")
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    project: Mapped[Project] = relationship(back_populates="wallet_transactions")
