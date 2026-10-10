"""Labourer endpoints, including autocomplete search for the frontend dropdown."""
import uuid
from typing import List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.labourer import Labourer
from app.models.user import User
from app.schemas.labourer import (
    LabourerCreate,
    LabourerRead,
    LabourerSuggestion,
    LabourerUpdate,
)
from app.services import labourer_service

router = APIRouter(prefix="/labourers", tags=["Labourers"])


@router.get("", response_model=List[LabourerRead])
def list_my_labourers(
    user: User = Depends(require_permission("labourers.view")),
    db: Session = Depends(get_db),
) -> List[Labourer]:
    """
    List labourers registered by the logged in user.

    Args:
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        List[Labourer]: List of labourers.
    """
    return labourer_service.list_my_labourers(db, user)


@router.get("/search", response_model=List[LabourerSuggestion])
def search_labourers(
    q: str = Query(min_length=2, description="Part of the name, or the start of the ID number"),
    limit: int = Query(default=10, ge=1, le=20),
    user: User = Depends(require_permission("labourers.view")),
    db: Session = Depends(get_db),
) -> List[Labourer]:
    """
    Autocomplete for the labourer name and national ID number fields.

    Args:
        q (str): Search text: part of a name, or the start of an ID number.
        limit (int): Maximum number of results.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        List[Labourer]: List of labourers.
    """
    return labourer_service.search_labourers(db, q, limit)


@router.post("", response_model=LabourerRead, status_code=status.HTTP_201_CREATED)
def create_labourer(
    data: LabourerCreate,
    user: User = Depends(require_permission("labourers.create")),
    db: Session = Depends(get_db),
) -> Labourer:
    """
    Register a labourer. Requires ``labourers.create``.

    Args:
        data (LabourerCreate): Validated request body.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        Labourer: The labourer.
    """
    return labourer_service.create_labourer(db, data, user)


@router.get("/{labourer_id}", response_model=LabourerRead)
def get_labourer(
    labourer_id: uuid.UUID,
    user: User = Depends(require_permission("labourers.view")),
    db: Session = Depends(get_db),
) -> Labourer:
    """
    Get one labourer's details.

    Args:
        labourer_id (uuid.UUID): ID of the labourer.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        Labourer: The labourer.
    """
    return labourer_service.get_labourer_or_404(db, labourer_id)


@router.patch("/{labourer_id}", response_model=LabourerRead)
def update_labourer(
    labourer_id: uuid.UUID,
    data: LabourerUpdate,
    user: User = Depends(require_permission("labourers.edit")),
    db: Session = Depends(get_db),
) -> Labourer:
    """
    Edit a labourer you registered. Requires ``labourers.edit``.

    Args:
        labourer_id (uuid.UUID): ID of the labourer.
        data (LabourerUpdate): Validated request body.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        Labourer: The labourer.
    """
    labourer = labourer_service.get_labourer_or_404(db, labourer_id)
    return labourer_service.update_labourer(db, labourer, data, user)
