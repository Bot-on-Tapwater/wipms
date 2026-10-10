"""Permission endpoints.

* ``GET /permissions/me`` is what the frontend calls to decide which
  buttons/components to show.
* The other endpoints let a super admin change permissions without a
  dashboard (a CLI exists too: ``app/scripts/manage_permissions.py``).
"""
from typing import Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.models.permission import Permission
from app.models.user import User
from app.schemas.permission import (
    MyPermissions,
    PermissionChange,
    PermissionRead,
    RolePermissions,
)
from app.services import permission_service

router = APIRouter(prefix="/permissions", tags=["Permissions"])


@router.get("/me", response_model=MyPermissions)
def my_permissions(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> MyPermissions:
    """
    Return the permission codes of the logged in user's role.

    Args:
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        MyPermissions: The role and its permission codes.
    """
    codes = permission_service.get_permissions_for_role(db, user.role)
    return MyPermissions(role=user.role, permissions=codes)


@router.get("", response_model=List[PermissionRead])
def list_permissions(
    user: User = Depends(require_permission("permissions.manage")),
    db: Session = Depends(get_db),
) -> List[Permission]:
    """
    List every permission in the catalogue.

    Args:
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        List[Permission]: List of permissions.
    """
    return permission_service.list_permissions(db)


@router.get("/roles", response_model=RolePermissions)
def list_role_permissions(
    user: User = Depends(require_permission("permissions.manage")),
    db: Session = Depends(get_db),
) -> RolePermissions:
    """
    Show the permissions of every role.

    Args:
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        RolePermissions: Permission codes of every role.
    """
    roles: Dict[str, List[str]] = {}
    for role in permission_service.all_role_values():
        roles[role] = permission_service.get_permissions_for_role(db, role)
    return RolePermissions(roles=roles)


@router.post("/roles/{role}/grant", response_model=MyPermissions)
def grant_permission(
    role: str,
    data: PermissionChange,
    user: User = Depends(require_permission("permissions.manage")),
    db: Session = Depends(get_db),
) -> MyPermissions:
    """
    Give a permission to a role.

    Args:
        role (str): Role value, e.g. ``subcontractor``.
        data (PermissionChange): Validated request body.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        MyPermissions: The role and its permission codes.
    """
    permission_service.grant_permission(db, role, data.code)
    return MyPermissions(role=role, permissions=permission_service.get_permissions_for_role(db, role))


@router.post("/roles/{role}/revoke", response_model=MyPermissions)
def revoke_permission(
    role: str,
    data: PermissionChange,
    user: User = Depends(require_permission("permissions.manage")),
    db: Session = Depends(get_db),
) -> MyPermissions:
    """
    Take a permission away from a role.

    Args:
        role (str): Role value, e.g. ``subcontractor``.
        data (PermissionChange): Validated request body.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        MyPermissions: The role and its permission codes.
    """
    permission_service.revoke_permission(db, role, data.code)
    return MyPermissions(role=role, permissions=permission_service.get_permissions_for_role(db, role))
