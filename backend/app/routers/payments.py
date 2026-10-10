"""Payment endpoints: request, approvals, retries, retention and records.

Payments are mocked until the bank API is available (see
``services/payment_provider.py``).
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.constants.roles import Role
from app.core.database import get_db
from app.core.dependencies import check_permission, get_current_user, require_permission
from app.models.payment import PaymentRecord
from app.models.user import User
from app.models.work import Work
from app.schemas.payment import (
    PaymentApproval,
    PaymentOutcomeRead,
    PaymentRecordRead,
    PaymentSummary,
)
from app.schemas.work import WorkRead
from app.services import payment_service
from app.services.access_service import get_accessible_project, get_accessible_work
from app.services.payment_service import PaymentOutcome
from app.services.permission_service import role_has_permission
from app.services.project_service import list_projects_for_user

router = APIRouter(tags=["Payments"])

APPROVAL_PERMISSIONS = {
    payment_service.CONTRACTOR_SUPERVISOR: "payments.approve_as_contractor_supervisor",
    payment_service.MAIN_CONTRACTOR: "payments.approve_as_main_contractor",
}


def _outcome_to_schema(outcome: PaymentOutcome) -> PaymentOutcomeRead:
    """
    Convert a service outcome into the API response.

    Args:
        outcome (PaymentOutcome): Result returned by the payment service.

    Returns:
        PaymentOutcomeRead: Outcome with a message, payment counts and the updated work.
    """
    return PaymentOutcomeRead(
        message=outcome.message,
        payments_made=outcome.payments_made,
        payments_failed=outcome.payments_failed,
        work=WorkRead.model_validate(outcome.work),
    )


@router.post("/works/{work_id}/payment-request", response_model=WorkRead)
def request_payment(
    work_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_permission("payments.request")),
    db: Session = Depends(get_db),
) -> Work:
    """
    Request payment for a work. Notifies the main contractor and contractor supervisors.

    Args:
        work_id (uuid.UUID): ID of the work.
        background_tasks (BackgroundTasks): FastAPI background tasks used to send emails after the response.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        Work: The work.
    """
    work = get_accessible_work(db, work_id, user)
    return payment_service.request_payment(db, work, user, background_tasks)


@router.post("/works/{work_id}/payment-approvals", response_model=PaymentOutcomeRead)
def approve_payment(
    work_id: uuid.UUID,
    data: PaymentApproval,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentOutcomeRead:
    """
    Give the contractor supervisor or main contractor payment approval.

    Once both approvals exist, labourers and the subcontractor are paid
    automatically. Each approval type needs its own permission.

    Args:
        work_id (uuid.UUID): ID of the work.
        data (PaymentApproval): Validated request body.
        background_tasks (BackgroundTasks): FastAPI background tasks used to send emails after the response.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        PaymentOutcomeRead: Outcome with a message, payment counts and the updated work.
    """
    check_permission(db, user, APPROVAL_PERMISSIONS[data.approval_type])
    work = get_accessible_work(db, work_id, user)
    outcome = payment_service.approve_payment(
        db, work, data.approval_type, user, background_tasks
    )
    return _outcome_to_schema(outcome)


@router.post("/works/{work_id}/payments/retry", response_model=PaymentOutcomeRead)
def retry_failed_payments(
    work_id: uuid.UUID,
    user: User = Depends(require_permission("payments.approve_as_main_contractor")),
    db: Session = Depends(get_db),
) -> PaymentOutcomeRead:
    """
    Retry every failed payment of the work. Successful ones are never repeated.

    Args:
        work_id (uuid.UUID): ID of the work.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        PaymentOutcomeRead: Outcome with a message, payment counts and the updated work.
    """
    work = get_accessible_work(db, work_id, user)
    return _outcome_to_schema(payment_service.retry_failed_payments(db, work, user))


@router.post("/works/{work_id}/retention-request", response_model=WorkRead)
def request_retention(
    work_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_permission("payments.request_retention")),
    db: Session = Depends(get_db),
) -> Work:
    """
    Request release of the retention money for a fully paid work.

    Args:
        work_id (uuid.UUID): ID of the work.
        background_tasks (BackgroundTasks): FastAPI background tasks used to send emails after the response.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        Work: The work.
    """
    work = get_accessible_work(db, work_id, user)
    return payment_service.request_retention(db, work, user, background_tasks)


@router.post("/works/{work_id}/retention-approval", response_model=PaymentOutcomeRead)
def approve_retention(
    work_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_permission("payments.approve_retention")),
    db: Session = Depends(get_db),
) -> PaymentOutcomeRead:
    """
    Approve and pay the retention money to the subcontractor.

    Args:
        work_id (uuid.UUID): ID of the work.
        background_tasks (BackgroundTasks): FastAPI background tasks used to send emails after the response.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        PaymentOutcomeRead: Outcome with a message, payment counts and the updated work.
    """
    work = get_accessible_work(db, work_id, user)
    outcome = payment_service.approve_retention(db, work, user, background_tasks)
    return _outcome_to_schema(outcome)


@router.get("/works/{work_id}/payment-summary", response_model=PaymentSummary)
def get_payment_summary(
    work_id: uuid.UUID,
    user: User = Depends(require_permission("payments.view")),
    db: Session = Depends(get_db),
) -> dict:
    """
    Show how much goes to labourers, the subcontractor and retention. Requires ``payments.view``.

    Args:
        work_id (uuid.UUID): ID of the work.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        dict: Amounts paid, due and failed for the work.
    """
    work = get_accessible_work(db, work_id, user)
    return payment_service.payment_summary(db, work)


@router.get("/payments/records", response_model=List[PaymentRecordRead])
def list_payment_records(
    project_id: Optional[uuid.UUID] = None,
    work_id: Optional[uuid.UUID] = None,
    labourer_id: Optional[uuid.UUID] = None,
    successful: Optional[bool] = None,
    user: User = Depends(require_permission("payments.view")),
    db: Session = Depends(get_db),
) -> List[PaymentRecord]:
    """
    List payment attempts, newest first. Filter by project, work, labourer or outcome.

    Without ``project_id`` or ``work_id``, users without ``projects.view_all``
    get the payments of every project they are on. Subcontractors only see
    payments of their own works.

    Args:
        project_id (Optional[uuid.UUID]): ID of the project.
        work_id (Optional[uuid.UUID]): ID of the work.
        labourer_id (Optional[uuid.UUID]): ID of the labourer.
        successful (Optional[bool]): True for successful payments only, False for failed only, None for both.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        List[PaymentRecord]: List of payment records.
    """
    project_ids = None
    if work_id is not None:
        work = get_accessible_work(db, work_id, user)
        project_id = work.project_id
    elif project_id is not None:
        get_accessible_project(db, project_id, user)
    elif not role_has_permission(db, user.role, "projects.view_all"):
        project_ids = []
        for project in list_projects_for_user(db, user):
            project_ids.append(project.id)
    subcontractor_id = None
    if user.role == Role.SUBCONTRACTOR.value:
        subcontractor_id = user.id
    return payment_service.list_payment_records(
        db, project_id=project_id, work_id=work_id, labourer_id=labourer_id,
        successful=successful, subcontractor_id=subcontractor_id, project_ids=project_ids,
    )
