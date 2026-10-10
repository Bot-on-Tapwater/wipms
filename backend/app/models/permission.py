"""Permission catalogue and the mapping of permissions to roles."""
from typing import List

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class Permission(TimestampMixin, Base):
    """
    A single action someone can perform, e.g. ``projects.create``.

    Attributes:
        id: Primary key
        code: Unique code of the permission, e.g. projects.create
        description: What the permission allows
        roles: The roles that have this permission
    """

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(255), default="")

    roles: Mapped[List["RolePermission"]] = relationship(
        back_populates="permission", cascade="all, delete-orphan"
    )


class RolePermission(TimestampMixin, Base):
    """
    Grants one permission to every user with the given role.

    Attributes:
        id: Primary key
        role: Role that gets the permission
        permission_id: The permission given
    """

    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role", "permission_id", name="uq_role_permission"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(30), index=True)
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id", ondelete="CASCADE"))

    permission: Mapped[Permission] = relationship(back_populates="roles")
