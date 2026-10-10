"""Schemas for the permission system."""
from typing import Dict, List

from pydantic import BaseModel

from app.schemas.common import ORMModel


class PermissionRead(ORMModel):
    """A permission in the catalogue."""

    code: str
    description: str


class MyPermissions(BaseModel):
    """Permissions of the logged in user (used by the frontend to show/hide UI)."""

    role: str
    permissions: List[str]


class RolePermissions(BaseModel):
    """All roles and their permission codes."""

    roles: Dict[str, List[str]]


class PermissionChange(BaseModel):
    """Body for granting or revoking one permission for a role."""

    code: str
