"""Reading and changing which roles have which permissions."""
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.permissions import PERMISSIONS, default_permissions_for_role
from app.constants.roles import Role
from app.core.exceptions import AppError, NotFoundError
from app.models.permission import Permission, RolePermission


def all_role_values() -> List[str]:
    """
    Return every role value as a list of strings.

    Returns:
        List[str]: Every role value, e.g. ``subcontractor``.
    """
    values = []
    for role in Role:
        values.append(role.value)
    return values


def validate_role(role: str) -> None:
    """
    Raise an error if ``role`` is not a known role.

    Args:
        role (str): Role value, e.g. ``subcontractor``.
    """
    if role not in all_role_values():
        raise AppError(f"Unknown role '{role}'")


def seed_permissions(db: Session, reset_roles: bool = False) -> None:
    """
    Make sure every permission in the catalogue exists in the database.

    Args:
        db (Session): Database session.
        reset_roles (bool): If True, role permissions are reset to the defaults
            in ``app/constants/permissions.py``. If False, defaults are only
            added for permissions that are brand new, so manual changes made
            later are kept.
    """
    new_codes = []
    for code, description in PERMISSIONS.items():
        permission = db.scalar(select(Permission).where(Permission.code == code))
        if permission is None:
            db.add(Permission(code=code, description=description))
            new_codes.append(code)
        else:
            permission.description = description
    db.flush()

    if reset_roles:
        for link in db.scalars(select(RolePermission)).all():
            db.delete(link)
        db.flush()

    for role in all_role_values():
        for code in default_permissions_for_role(role):
            if reset_roles or code in new_codes:
                _add_role_permission(db, role, code)
    db.commit()


def _add_role_permission(db: Session, role: str, code: str) -> None:
    """
    Link a permission to a role if it is not linked already.

    Args:
        db (Session): Database session.
        role (str): Role value, e.g. ``subcontractor``.
        code (str): Permission code, e.g. ``works.create``.
    """
    permission = db.scalar(select(Permission).where(Permission.code == code))
    if permission is None:
        raise NotFoundError(f"Unknown permission '{code}'")
    existing = db.scalar(
        select(RolePermission).where(
            RolePermission.role == role, RolePermission.permission_id == permission.id
        )
    )
    if existing is None:
        db.add(RolePermission(role=role, permission_id=permission.id))
        db.flush()


def get_permissions_for_role(db: Session, role: str) -> List[str]:
    """
    Return the sorted list of permission codes a role has.

    Args:
        db (Session): Database session.
        role (str): Role value, e.g. ``subcontractor``.

    Returns:
        List[str]: Permission codes of the role.
    """
    statement = (
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role == role)
        .order_by(Permission.code)
    )
    return list(db.scalars(statement).all())


def role_has_permission(db: Session, role: str, code: str) -> bool:
    """
    Return True if the role has the given permission.

    Args:
        db (Session): Database session.
        role (str): Role value, e.g. ``subcontractor``.
        code (str): Permission code, e.g. ``works.create``.

    Returns:
        bool: True if the role has the permission.
    """
    statement = (
        select(RolePermission.id)
        .join(Permission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role == role, Permission.code == code)
    )
    return db.scalar(statement) is not None


def list_permissions(db: Session) -> List[Permission]:
    """
    Return every permission in the catalogue.

    Args:
        db (Session): Database session.

    Returns:
        List[Permission]: List of permissions.
    """
    return list(db.scalars(select(Permission).order_by(Permission.code)).all())


def grant_permission(db: Session, role: str, code: str) -> None:
    """
    Give a permission to a role.

    Args:
        db (Session): Database session.
        role (str): Role value, e.g. ``subcontractor``.
        code (str): Permission code, e.g. ``works.create``.
    """
    validate_role(role)
    _add_role_permission(db, role, code)
    db.commit()


def revoke_permission(db: Session, role: str, code: str) -> None:
    """
    Take a permission away from a role.

    Args:
        db (Session): Database session.
        role (str): Role value, e.g. ``subcontractor``.
        code (str): Permission code, e.g. ``works.create``.
    """
    validate_role(role)
    permission = db.scalar(select(Permission).where(Permission.code == code))
    if permission is None:
        raise NotFoundError(f"Unknown permission '{code}'")
    link = db.scalar(
        select(RolePermission).where(
            RolePermission.role == role, RolePermission.permission_id == permission.id
        )
    )
    if link is not None:
        db.delete(link)
        db.commit()
