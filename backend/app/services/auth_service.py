"""Business logic for registration, login, tokens, passwords and profiles."""
import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.constants.roles import Role
from app.core.config import settings, split_csv
from app.core.database import utc_now
from app.core.exceptions import AppError
from app.core.security import (
    REFRESH_TOKEN_TYPE,
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_reset_token,
    hash_password,
    verify_password,
)
from app.models.project import (
    Project,
    project_consultant_supervisors,
    project_contractor_supervisors,
    project_subcontractors,
)
from app.models.user import RevokedToken, User
from app.models.work import Work
from app.schemas.user import TokenPair, UserRegister, UserUpdate


def _hash_reset_token(token: str) -> str:
    """
    Hash a reset token so the raw value is never stored in the database.

    Args:
        token (str): Plain reset token.

    Returns:
        str: SHA-256 hex digest of the token.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def _as_aware(value: datetime) -> datetime:
    """
    Make a datetime timezone aware (SQLite returns naive datetimes).

    Args:
        value (datetime): Datetime that may be naive.

    Returns:
        datetime: The datetime in UTC.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Find a user by email (case-insensitive).

    Args:
        db (Session): Database session.
        email (str): Email address.

    Returns:
        Optional[User]: The user, or None if not found.
    """
    return db.scalar(select(User).where(User.email == email.lower()))


def register_user(db: Session, data: UserRegister) -> User:
    """
    Create a new user account.

    Rules carried over from the old backend:
    * email must be unique;
    * only emails listed in ``MAIN_CONTRACTOR_EMAILS`` may register as
      main contractor (this was a hard-coded email before).

    New rule: nobody can self-register as ``super-admin``. Super admins are
    created with ``python -m app.scripts.create_superuser``.

    Args:
        db (Session): Database session.
        data (UserRegister): Validated request body.

    Returns:
        User: The user.
    """
    email = data.email.lower()
    # Check if the email is already in use
    if get_user_by_email(db, email) is not None:
        raise AppError("Email is already in use")
    if data.role == Role.SUPER_ADMIN:
        raise AppError("Super admin accounts cannot be created through registration")
    # Only listed emails may register as main contractor
    if data.role == Role.MAIN_CONTRACTOR:
        allowed = []
        for item in split_csv(settings.MAIN_CONTRACTOR_EMAILS):
            allowed.append(item.lower())
        if email not in allowed:
            raise AppError(
                "Only the platform owner is allowed to register as a main contractor. "
                "Contact the platform administrator for assistance."
            )
    user = User(
        first_name=data.first_name,
        last_name=data.last_name,
        email=email,
        phone_number=data.phone_number,
        role=data.role.value,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    """
    Return the user if the email and password are correct.

    Args:
        db (Session): Database session.
        email (str): Email address.
        password (str): Plain text password.

    Returns:
        User: The user.
    """
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        raise AppError("Invalid credentials", 401)
    if not user.is_active:
        raise AppError("Account is disabled", 403)
    return user


def issue_tokens(user: User) -> TokenPair:
    """
    Create a new access and refresh token pair for a user.

    Args:
        user (User): The user the tokens are for.

    Returns:
        TokenPair: New access and refresh tokens.
    """
    user_id = str(user.id)
    return TokenPair(
        access_token=create_access_token(user_id, user.token_version),
        refresh_token=create_refresh_token(user_id, user.token_version),
    )


def _decode_refresh_token(db: Session, refresh_token: str) -> dict:
    """
    Decode a refresh token and make sure it was not logged out.

    Args:
        db (Session): Database session.
        refresh_token (str): Refresh token issued at login.

    Returns:
        dict: The token claims.
    """
    try:
        payload = decode_token(refresh_token, REFRESH_TOKEN_TYPE)
    except TokenError as error:
        raise AppError("Invalid refresh token", 401) from error
    if db.get(RevokedToken, payload["jti"]) is not None:
        raise AppError("Refresh token has been revoked", 401)
    return payload


def refresh_tokens(db: Session, refresh_token: str) -> TokenPair:
    """
    Swap a valid refresh token for a new token pair (the old one is revoked).

    Args:
        db (Session): Database session.
        refresh_token (str): Refresh token issued at login.

    Returns:
        TokenPair: New access and refresh tokens.
    """
    payload = _decode_refresh_token(db, refresh_token)
    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise AppError("User not found or inactive", 401)
    if payload.get("ver") != user.token_version:
        raise AppError("Refresh token is no longer valid, please log in again", 401)
    _revoke(db, payload)
    db.commit()
    return issue_tokens(user)


def logout(db: Session, refresh_token: str) -> None:
    """
    Revoke a refresh token so it can no longer be used.

    Args:
        db (Session): Database session.
        refresh_token (str): Refresh token issued at login.
    """
    payload = _decode_refresh_token(db, refresh_token)
    _revoke(db, payload)
    db.commit()


def _revoke(db: Session, payload: dict) -> None:
    """
    Store a token id in the revoked tokens table.

    Rows of tokens that have expired anyway are deleted at the same time,
    so the table does not keep growing.

    Args:
        db (Session): Database session.
        payload (dict): Decoded token claims.
    """
    db.execute(delete(RevokedToken).where(RevokedToken.expires_at < utc_now()))
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    db.add(RevokedToken(jti=payload["jti"], expires_at=expires_at))


def create_password_reset(db: Session, email: str) -> Optional[Tuple[User, str]]:
    """
    Create a password reset token for the user with this email.

    Returns ``(user, raw_token)`` or ``None`` when no such user exists.
    The router always answers with the same message so attackers cannot
    find out which emails are registered.

    Args:
        db (Session): Database session.
        email (str): Email address.

    Returns:
        Optional[Tuple[User, str]]: The user and the plain reset token, or None if no user has the email.
    """
    user = get_user_by_email(db, email)
    if user is None or not user.is_active:
        return None
    token = generate_reset_token()
    user.password_reset_token = _hash_reset_token(token)
    user.password_reset_expires_at = utc_now() + timedelta(
        minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES
    )
    db.commit()
    return user, token


def build_reset_url(user: User, token: str) -> str:
    """
    Return the frontend link the user clicks to reset their password.

    Args:
        user (User): The user who asked for the reset.
        token (str): Plain reset token.

    Returns:
        str: The reset link.
    """
    return f"{settings.FRONTEND_URL}/reset-password?user_id={user.id}&token={token}"


def reset_password(db: Session, user_id: uuid.UUID, token: str, new_password: str) -> None:
    """
    Set a new password if the reset token is valid and not expired.

    Every token issued before the reset stops working, so anyone else who
    was logged in as this user is logged out.

    Args:
        db (Session): Database session.
        user_id (uuid.UUID): ID of the user.
        token (str): Plain reset token from the email link.
        new_password (str): The new plain text password.
    """
    user = db.get(User, user_id)
    if user is None or user.password_reset_token is None:
        raise AppError("Invalid or expired reset token")
    if not hmac.compare_digest(user.password_reset_token, _hash_reset_token(token)):
        raise AppError("Invalid or expired reset token")
    expires_at = user.password_reset_expires_at
    if expires_at is None or _as_aware(expires_at) < utc_now():
        raise AppError("Invalid or expired reset token")
    user.hashed_password = hash_password(new_password)
    user.password_reset_token = None
    user.password_reset_expires_at = None
    user.token_version += 1
    db.commit()


def change_password(db: Session, user: User, current_password: str, new_password: str) -> TokenPair:
    """
    Change the password of a logged in user and return fresh tokens.

    Every token issued before the change stops working (other devices are
    logged out), so the caller gets a new token pair to stay logged in.

    Args:
        db (Session): Database session.
        user (User): The logged in user performing the action.
        current_password (str): The user's current password.
        new_password (str): The new plain text password.

    Returns:
        TokenPair: New access and refresh tokens.
    """
    if not verify_password(current_password, user.hashed_password):
        raise AppError("Current password is incorrect")
    user.hashed_password = hash_password(new_password)
    user.token_version += 1
    db.commit()
    return issue_tokens(user)


def user_is_on_any_project(db: Session, user: User) -> bool:
    """
    Return True if the user created, supervises or subcontracts on any project.

    Args:
        db (Session): Database session.
        user (User): The user to check.

    Returns:
        bool: True if the user is on at least one project.
    """
    if db.scalar(select(Project.id).where(Project.created_by_id == user.id).limit(1)):
        return True
    for table in (
        project_contractor_supervisors,
        project_consultant_supervisors,
        project_subcontractors,
    ):
        found = db.execute(
            select(table.c.project_id).where(table.c.user_id == user.id).limit(1)
        ).first()
        if found is not None:
            return True
    work = db.scalar(
        select(Work.id)
        .where(or_(Work.assigned_subcontractor_id == user.id, Work.created_by_id == user.id))
        .limit(1)
    )
    return work is not None


def update_profile(db: Session, user: User, data: UserUpdate) -> User:
    """
    Update the logged in user's profile.

    Rule from the old backend: the role cannot change while the user is
    assigned to any project. Changing to main contractor or super admin is
    never allowed through the profile.

    Args:
        db (Session): Database session.
        user (User): The logged in user performing the action.
        data (UserUpdate): Validated request body.

    Returns:
        User: The user.
    """
    if data.role is not None and data.role.value != user.role:
        if data.role in (Role.SUPER_ADMIN, Role.MAIN_CONTRACTOR):
            raise AppError("You cannot change your role to this role")
        if user_is_on_any_project(db, user):
            raise AppError("Cannot change role while assigned to projects")
        user.role = data.role.value
    if data.first_name is not None:
        user.first_name = data.first_name
    if data.last_name is not None:
        user.last_name = data.last_name
    if data.phone_number is not None:
        user.phone_number = data.phone_number
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session, role: Optional[str] = None) -> List[User]:
    """
    List active users, optionally filtered by role.

    Args:
        db (Session): Database session.
        role (Optional[str]): Role value, e.g. ``subcontractor``.

    Returns:
        List[User]: List of users.
    """
    statement = select(User).where(User.is_active.is_(True)).order_by(User.first_name)
    if role:
        statement = statement.where(User.role == role)
    return list(db.scalars(statement).all())
