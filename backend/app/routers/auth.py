"""Authentication endpoints: register, login, refresh, logout, passwords."""
from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.user import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    ResetPasswordRequest,
    TokenPair,
    UserRead,
    UserRegister,
)
from app.services import auth_service
from app.services.email_service import queue_email
from app.services.permission_service import get_permissions_for_role

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(data: UserRegister, db: Session = Depends(get_db)) -> User:
    """
    Create a new account. Super admin cannot be chosen here.

    Args:
        data (UserRegister): Validated request body.
        db (Session): Database session.

    Returns:
        User: The user.
    """
    return auth_service.register_user(db, data)


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    """
    Log in with email and password. Returns tokens, user and permissions.

    Args:
        data (LoginRequest): Validated request body.
        db (Session): Database session.

    Returns:
        LoginResponse: Tokens, the user and their permission codes.
    """
    user = auth_service.authenticate(db, data.email, data.password)
    tokens = auth_service.issue_tokens(user)
    return LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        user=UserRead.model_validate(user),
        permissions=get_permissions_for_role(db, user.role),
    )


@router.post("/refresh", response_model=TokenPair)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    """
    Get a new token pair using a refresh token.

    Args:
        data (RefreshRequest): Validated request body.
        db (Session): Database session.

    Returns:
        TokenPair: New access and refresh tokens.
    """
    return auth_service.refresh_tokens(db, data.refresh_token)


@router.post("/logout", response_model=MessageResponse)
def logout(data: RefreshRequest, db: Session = Depends(get_db)) -> MessageResponse:
    """
    Log out by revoking the refresh token.

    Args:
        data (RefreshRequest): Validated request body.
        db (Session): Database session.

    Returns:
        MessageResponse: A confirmation message.
    """
    auth_service.logout(db, data.refresh_token)
    return MessageResponse(message="Successfully logged out")


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    """
    Return the logged in user. Also used to check if a token is still valid.

    Args:
        user (User): The logged in user performing the action.

    Returns:
        User: The user.
    """
    return user


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Email a password reset link. Always returns the same message.

    Args:
        data (ForgotPasswordRequest): Validated request body.
        background_tasks (BackgroundTasks): FastAPI background tasks used to send emails after the response.
        db (Session): Database session.

    Returns:
        MessageResponse: A confirmation message.
    """
    result = auth_service.create_password_reset(db, data.email)
    if result is not None:
        user, token = result
        queue_email(
            background_tasks,
            [user.email],
            "Password Reset Request",
            "password_reset.html",
            {
                "user": user,
                "reset_url": auth_service.build_reset_url(user, token),
                "expires_minutes": settings.PASSWORD_RESET_EXPIRE_MINUTES,
            },
        )
    return MessageResponse(
        message="If an account with that email exists, a reset link has been sent"
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)) -> MessageResponse:
    """
    Set a new password using the token from the reset email.

    Args:
        data (ResetPasswordRequest): Validated request body.
        db (Session): Database session.

    Returns:
        MessageResponse: A confirmation message.
    """
    auth_service.reset_password(db, data.user_id, data.token, data.new_password)
    return MessageResponse(message="Password has been reset successfully")


@router.post("/change-password", response_model=TokenPair)
def change_password(
    data: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TokenPair:
    """
    Change password while logged in. Returns new tokens; older tokens stop working.

    Args:
        data (ChangePasswordRequest): Validated request body.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        TokenPair: New access and refresh tokens.
    """
    return auth_service.change_password(db, user, data.current_password, data.new_password)
