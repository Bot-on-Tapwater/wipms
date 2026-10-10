"""User profile and user listing endpoints."""
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.constants.roles import Role
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate
from app.services import auth_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserRead)
def get_profile(user: User = Depends(get_current_user)) -> User:
    """
    Return the logged in user's profile.

    Args:
        user (User): The logged in user performing the action.

    Returns:
        User: The user.
    """
    return user


@router.patch("/me", response_model=UserRead)
def update_profile(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """
    Update the logged in user's profile (names, phone, role).

    Args:
        data (UserUpdate): Validated request body.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        User: The user.
    """
    return auth_service.update_profile(db, user, data)


@router.get("", response_model=List[UserRead])
def list_users(
    role: Optional[Role] = None,
    user: User = Depends(require_permission("users.view_all")),
    db: Session = Depends(get_db),
) -> List[User]:
    """
    List active users, optionally filtered by ``role``.

    Args:
        role (Optional[Role]): Role value, e.g. ``subcontractor``.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        List[User]: List of users.
    """
    role_value = None
    if role is not None:
        role_value = role.value
    return auth_service.list_users(db, role_value)
