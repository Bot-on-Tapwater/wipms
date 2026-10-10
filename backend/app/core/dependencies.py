"""Reusable FastAPI dependencies: current user and permission checks."""
import uuid
from typing import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppError, ForbiddenError
from app.core.security import ACCESS_TOKEN_TYPE, TokenError, decode_token
from app.models.user import User
from app.services.permission_service import role_has_permission

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Return the logged in user from the ``Authorization: Bearer`` header.

    Args:
        credentials (HTTPAuthorizationCredentials): Bearer token from the Authorization header.
        db (Session): Database session.

    Returns:
        User: The logged in user.

    Raises:
        AppError(401): if the token is missing, invalid or out of date, or the
            user is inactive.
    """
    if credentials is None:
        raise AppError("Authentication credentials were not provided", 401)
    try:
        payload = decode_token(credentials.credentials, ACCESS_TOKEN_TYPE)
        user_id = uuid.UUID(payload["sub"])
    except (TokenError, KeyError, ValueError) as error:
        raise AppError("Invalid or expired token", 401) from error
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError("User not found or inactive", 401)
    if payload.get("ver") != user.token_version:
        raise AppError("Token is no longer valid, please log in again", 401)
    return user


def check_permission(db: Session, user: User, code: str) -> None:
    """
    Raise 403 if the user's role does not have the permission ``code``.

    Use this inside an endpoint when the permission depends on the request
    (for example on a path parameter).

    Args:
        db (Session): Database session.
        user (User): The logged in user performing the action.
        code (str): Permission code, e.g. ``works.create``.
    """
    if not role_has_permission(db, user.role, code):
        raise ForbiddenError(f"Missing permission: {code}")


def require_permission(code: str) -> Callable[..., User]:
    """
    Build a dependency that only lets users whose role has ``code`` through.

    Usage::

        @router.post("/", dependencies=[Depends(require_permission("projects.create"))])

    or, to also receive the user::

        user: User = Depends(require_permission("projects.create"))

    Args:
        code (str): Permission code, e.g. ``works.create``.

    Returns:
        Callable[..., User]: A FastAPI dependency that returns the user when allowed.
    """

    def permission_checker(
        user: User = Depends(get_current_user), db: Session = Depends(get_db)
    ) -> User:
        """
        Check the current user's role has the required permission.

        Args:
            user (User): The logged in user performing the action.
            db (Session): Database session.

        Returns:
            User: The logged in user.
        """
        check_permission(db, user, code)
        return user

    return permission_checker
