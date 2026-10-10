"""Business logic for labourers, including autocomplete search."""
import uuid
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.constants.choices import PaymentStatus
from app.core.exceptions import AppError, ForbiddenError, NotFoundError
from app.models.labourer import Labourer
from app.models.user import User
from app.schemas.labourer import LabourerCreate, LabourerUpdate
from app.services.permission_service import role_has_permission

MAX_SEARCH_RESULTS = 20


def get_labourer_or_404(db: Session, labourer_id: uuid.UUID) -> Labourer:
    """
    Load a labourer or raise 404.

    Args:
        db (Session): Database session.
        labourer_id (uuid.UUID): ID of the labourer.

    Returns:
        Labourer: The labourer.
    """
    labourer = db.get(Labourer, labourer_id)
    if labourer is None:
        raise NotFoundError("Labourer not found")
    return labourer


def get_by_national_id(db: Session, national_id_number: str) -> Optional[Labourer]:
    """
    Find a labourer by national ID number.

    Args:
        db (Session): Database session.
        national_id_number (str): National ID number.

    Returns:
        Optional[Labourer]: The labourer, or None if not found.
    """
    return db.scalar(
        select(Labourer).where(Labourer.national_id_number == national_id_number)
    )


def create_labourer(db: Session, data: LabourerCreate, user: User) -> Labourer:
    """
    Register a new labourer. National ID numbers must be unique.

    Args:
        db (Session): Database session.
        data (LabourerCreate): Validated request body.
        user (User): The logged in user performing the action.

    Returns:
        Labourer: The labourer.
    """
    if get_by_national_id(db, data.national_id_number) is not None:
        raise AppError(
            "A labourer with this national ID number already exists. "
            "Search for them instead of creating a new record."
        )
    labourer = Labourer(
        name=data.name,
        title=data.title.value,
        national_id_number=data.national_id_number,
        phone_number=data.phone_number,
        daily_rate=data.daily_rate,
        overhead_cost=data.overhead_cost,
        created_by_id=user.id,
    )
    db.add(labourer)
    db.commit()
    db.refresh(labourer)
    return labourer


def can_edit_labourer(db: Session, labourer: Labourer, user: User) -> bool:
    """
    The creator, or someone who can see all projects, may edit a labourer.

    Args:
        db (Session): Database session.
        labourer (Labourer): The labourer.
        user (User): The logged in user performing the action.

    Returns:
        bool: True if the user may edit the labourer.
    """
    if labourer.created_by_id == user.id:
        return True
    return role_has_permission(db, user.role, "projects.view_all")


def _reset_unpaid_works(labourer: Labourer) -> None:
    """
    After a pay change, unpaid works of the labourer need fresh approvals.

    The amount each labourer is owed comes from their daily rate and
    overhead, so the attendance approval and any payment request on works
    that have not been paid yet are withdrawn. Paid works keep their records.

    Args:
        labourer (Labourer): The labourer whose pay changed.
    """
    for link in labourer.work_links:
        work = link.work
        if work.payment_status == PaymentStatus.PENDING.value:
            work.attendance_approval = False
            work.reset_payment_request()


def update_labourer(db: Session, labourer: Labourer, data: LabourerUpdate, user: User) -> Labourer:
    """
    Update a labourer's details. A pay change withdraws approvals on unpaid works.

    Args:
        db (Session): Database session.
        labourer (Labourer): The labourer.
        data (LabourerUpdate): Validated request body.
        user (User): The logged in user performing the action.

    Returns:
        Labourer: The labourer.
    """
    if not can_edit_labourer(db, labourer, user):
        raise ForbiddenError("Only the person who registered this labourer can edit them")
    if data.name is not None:
        labourer.name = " ".join(data.name.split())
    if data.title is not None:
        labourer.title = data.title.value
    if data.phone_number is not None:
        labourer.phone_number = data.phone_number
    pay_changed = False
    if data.daily_rate is not None and data.daily_rate != labourer.daily_rate:
        labourer.daily_rate = data.daily_rate
        pay_changed = True
    if data.overhead_cost is not None and data.overhead_cost != labourer.overhead_cost:
        labourer.overhead_cost = data.overhead_cost
        pay_changed = True
    if pay_changed:
        _reset_unpaid_works(labourer)
    db.commit()
    db.refresh(labourer)
    return labourer


def list_my_labourers(db: Session, user: User) -> List[Labourer]:
    """
    Labourers registered by the given user, newest first.

    Args:
        db (Session): Database session.
        user (User): The logged in user performing the action.

    Returns:
        List[Labourer]: List of labourers.
    """
    statement = (
        select(Labourer)
        .where(Labourer.created_by_id == user.id)
        .order_by(Labourer.created_at.desc())
    )
    return list(db.scalars(statement).all())


def search_labourers(db: Session, query: str, limit: int = 10) -> List[Labourer]:
    """
    Autocomplete search by name (contains) or national ID number (starts with).

    Args:
        db (Session): Database session.
        query (str): Search text typed by the user.
        limit (int): Maximum number of results.

    Returns:
        List[Labourer]: List of labourers.
    """
    query = query.strip()
    if len(query) < 2:
        return []
    if limit > MAX_SEARCH_RESULTS:
        limit = MAX_SEARCH_RESULTS
    statement = (
        select(Labourer)
        .where(
            or_(
                Labourer.name.icontains(query, autoescape=True),
                Labourer.national_id_number.startswith(query, autoescape=True),
            )
        )
        .order_by(Labourer.name)
        .limit(limit)
    )
    return list(db.scalars(statement).all())
