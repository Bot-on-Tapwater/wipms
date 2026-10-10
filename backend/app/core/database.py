"""Database engine, session factory and the declarative base class."""
from datetime import datetime, timezone
from typing import Generator

from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.core.config import settings


def utc_now() -> datetime:
    """
    Return the current time in UTC (timezone aware).

    Returns:
        datetime: The current time in UTC.
    """
    return datetime.now(timezone.utc)


engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class TimestampMixin:
    """Adds ``created_at`` and ``updated_at`` columns to a model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session and closes it.

    Yields:
        Session: A database session that is closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
