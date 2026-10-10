"""Password hashing and JWT token helpers."""
import secrets
import uuid
from datetime import timedelta
from typing import Any, Dict

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.database import utc_now

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


class TokenError(Exception):
    """Raised when a JWT token is invalid, expired or of the wrong type."""


def hash_password(password: str) -> str:
    """
    Return a bcrypt hash of the given plain password.

    Args:
        password (str): Plain text password.

    Returns:
        str: The bcrypt hash.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check a plain password against its stored hash.

    Args:
        plain_password (str): Plain text password entered by the user.
        hashed_password (str): Stored bcrypt hash.

    Returns:
        bool: True if the password matches the hash.
    """
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(user_id: str, token_version: int, token_type: str, expires: timedelta) -> str:
    """
    Build and sign a JWT for the given user.

    Args:
        user_id (str): ID of the user.
        token_version (int): The user's current token version (the ``ver`` claim).
        token_type (str): Either ``access`` or ``refresh``.
        expires (timedelta): How long the token is valid.

    Returns:
        str: The encoded JWT.
    """
    now = utc_now()
    payload: Dict[str, Any] = {
        "sub": user_id,
        "type": token_type,
        "ver": token_version,
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int((now + expires).timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str, token_version: int) -> str:
    """
    Create a short lived access token.

    Args:
        user_id (str): ID of the user.
        token_version (int): The user's current token version.

    Returns:
        str: The encoded access token.
    """
    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token(user_id, token_version, ACCESS_TOKEN_TYPE, expires)


def create_refresh_token(user_id: str, token_version: int) -> str:
    """
    Create a long lived refresh token.

    Args:
        user_id (str): ID of the user.
        token_version (int): The user's current token version.

    Returns:
        str: The encoded refresh token.
    """
    expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return _create_token(user_id, token_version, REFRESH_TOKEN_TYPE, expires)


def decode_token(token: str, expected_type: str) -> Dict[str, Any]:
    """
    Decode a JWT and make sure it has the expected type.

    Args:
        token (str): Token string.
        expected_type (str): Token type that is accepted (``access`` or ``refresh``).

    Returns:
        Dict[str, Any]: The token claims.

    Raises:
        TokenError: if the token is invalid, expired or of another type.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError as error:
        raise TokenError("Invalid or expired token") from error
    if payload.get("type") != expected_type:
        raise TokenError("Wrong token type")
    return payload


def generate_reset_token() -> str:
    """
    Generate a random, URL-safe password reset token.

    Returns:
        str: A random URL safe token.
    """
    return secrets.token_urlsafe(32)
