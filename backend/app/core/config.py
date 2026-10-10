"""Application settings loaded from environment variables (.env file)."""
from functools import lru_cache
from typing import List

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All configurable values for the backend.

    Every value can be overridden with an environment variable of the
    same name (case-insensitive). See ``.env.example`` for the full list.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # General
    APP_NAME: str = "Ijenga API"
    ENVIRONMENT: str = "local"

    # Database
    DATABASE_URL: str = "postgresql+psycopg://ijenga:ijenga@db:5432/ijenga"

    # Security / JWT
    SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_EXPIRE_MINUTES: int = 60

    # CORS (comma separated list of allowed origins)
    CORS_ORIGINS: str = "http://localhost:3000"

    # Frontend URL used inside emails (e.g. password reset link)
    FRONTEND_URL: str = "http://localhost:3000"

    # Only these emails may self-register as main contractor
    # (comma separated). Previously hard-coded in the old backend.
    MAIN_CONTRACTOR_EMAILS: str = ""
    # Password used by the create_superuser script. Leave empty to be asked
    # for it at the prompt (safer than keeping it in .env).
    SUPERUSER_PASSWORD: str = ""

    # Email (SMTP). If EMAIL_ENABLED is false, emails are only logged.
    EMAIL_ENABLED: bool = False
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_USE_TLS: bool = True
    EMAIL_HOST_USER: str = ""
    EMAIL_HOST_PASSWORD: str = ""
    DEFAULT_FROM_EMAIL: str = "noreply@ijenga.local"

    # File uploads (proof of work images)
    MEDIA_DIR: str = "media"
    MAX_UPLOAD_SIZE_MB: int = 5

    # Payment provider: only "mock" exists for now. The bank integration will
    # be added as a new provider class in app/services/payment_provider.py.
    PAYMENT_PROVIDER: str = "mock"

    # Mock payment provider: set to a value between 0 and 1 to simulate
    # random failures (0 = always succeed). Used until the bank API exists.
    MOCK_PAYMENT_FAILURE_RATE: float = 0.0

    # Payments may use at most this share of the wallet balance (old rule: 99%)
    WALLET_USABLE_RATIO: float = 0.99

    # Retention money share of a work's total cost (old rule: 10%)
    RETENTION_RATE: float = 0.10

    @model_validator(mode="after")
    def check_production_secret(self) -> "Settings":
        """
        Refuse to start in production with the default or a short secret key.

        Returns:
            Settings: The settings unchanged when the check passes.
        """
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY == "change-me" or len(self.SECRET_KEY) < 32:
                raise ValueError("Set a SECRET_KEY of at least 32 characters in production")
        return self


def split_csv(value: str) -> List[str]:
    """
    Turn a comma separated string into a clean list of strings.

    Args:
        value (str): Comma separated text.

    Returns:
        List[str]: Non-empty, stripped items.
    """
    items = []
    for item in value.split(","):
        item = item.strip()
        if item:
            items.append(item)
    return items


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    Returns:
        Settings: The settings, loaded once and cached.
    """
    return Settings()


settings = get_settings()
