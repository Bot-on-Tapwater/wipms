"""Payment flow: request, approve, pay labourers and subcontractor, retention.

The rules follow the old backend (``approve_payment`` in the Django
``projects/views.py`` and ``payment.md``), with these fixes:

1. Failed labourer payments are no longer added to the subcontractor's
   payout. The subcontractor gets ``total cost - labour due - retention``.
2. A work is only marked ``paid`` when every payment succeeded. If some
   failed it stays ``approved`` and the failed ones can be retried, so
   nobody is ever paid twice.
3. The work row is locked while paying so two approvals at the same moment
   cannot both trigger payouts.
4. Each project has its own wallet. Successful payouts are deducted from it.
"""
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional, Tuple

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.choices import PaymentStatus, PaymentType
from app.core.config import settings
from app.core.database import utc_now
from app.core.exceptions import AppError
from app.models.labourer import Labourer
from app.models.payment import PaymentRecord
from app.models.user import User
from app.models.work import Work
from app.services import notification_service
from app.services.payment_provider import get_payment_provider
from app.services.project_service import debit_wallet, lock_project, refresh_project_completion

MAIN_CONTRACTOR = "main_contractor"
CONTRACTOR_SUPERVISOR = "contractor_supervisor"


@dataclass
class PaymentOutcome:
    """What happened after a payment approval or retry."""

    message: str
    work: Work
    payments_made: int = 0
    payments_failed: int = 0


def lock_work(db: Session, work: Work) -> Work:
    """
    Reload the work and its project with row locks (PostgreSQL).

    The work lock stops two approvals at the same moment from both paying
    out. The project lock protects the wallet balance, which payouts of
    other works in the same project also change. ``populate_existing``
    replaces any copy already loaded in this session with the fresh row,
    so the checks below see the latest state.

    Args:
        db (Session): Database session.
        work (Work): The work.

    Returns:
        Work: The work, locked until the transaction ends.
    """
    statement = (
        select(Work)
        .where(Work.id == work.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    work = db.scalars(statement).one()
    lock_project(db, work.project)
    return work


def usable_wallet_balance(work: Work) -> Decimal:
    """
    The share of the project wallet that may be used (99% by default).

    Args:
        work (Work): The work.

    Returns:
        Decimal: Share of the wallet balance payments may use.
    """
    ratio = Decimal(str(settings.WALLET_USABLE_RATIO))
    return Decimal(work.project.wallet_balance) * ratio


def total_labour_due(work: Work) -> Decimal:
    """
    Sum of what every labourer on the work is owed.

    Args:
        work (Work): The work.

    Returns:
        Decimal: Total owed to the work's labourers.
    """
    total = Decimal("0")
    for link in work.labourer_links:
        total += link.amount_due
    return total


def subcontractor_amount(work: Work) -> Decimal:
    """
    What the subcontractor is paid now: total cost - labour due - retention.

    Args:
        work (Work): The work.

    Returns:
        Decimal: Amount owed to the subcontractor.
    """
    return work.total_cost - total_labour_due(work) - work.retention_money


def retention_amount_due(db: Session, work: Work) -> Decimal:
    """
    Retention money still to pay, capped so the work never pays more than its cost.

    When labour takes up most of the cost the subcontractor payout is zero,
    and paying the full retention on top would pay out more than the work
    costs. The retention is therefore limited to what is left of the total
    cost after the labourer and subcontractor payments.

    Args:
        db (Session): Database session.
        work (Work): The work.

    Returns:
        Decimal: Retention amount in KES (zero when nothing is left).
    """
    statement = select(PaymentRecord).where(
        PaymentRecord.work_id == work.id,
        PaymentRecord.successful.is_(True),
        PaymentRecord.payment_type != PaymentType.RETENTION.value,
    )
    paid = Decimal("0")
    for record in db.scalars(statement).all():
        paid += Decimal(record.amount_paid)
    remaining = work.total_cost - paid
    amount = min(work.retention_money, remaining)
    return max(amount, Decimal("0"))


def refresh_work_completion(work: Work) -> None:
    """
    Update ``is_completed`` for the work and its project.

    Rule from the old backend: with a subcontractor the work is complete once
    retention money is paid; without one, once payment is fully done.

    Args:
        work (Work): The work.
    """
    if work.assigned_subcontractor_id is not None:
        work.is_completed = work.retention_paid
    else:
        work.is_completed = work.payment_status == PaymentStatus.PAID.value
    refresh_project_completion(work.project)


def _send_payment(
    db: Session,
    work: Work,
    user: User,
    payment_type: str,
    amount: Decimal,
    recipient_name: str,
    recipient_phone: str,
    labourer: Optional[Labourer] = None,
    recipient_user: Optional[User] = None,
) -> PaymentRecord:
    """
    Send one payment through the provider and store the record.

    The record is saved whether the payment succeeds or fails. Successful
    payments are deducted from the project wallet. Does not commit.

    Args:
        db (Session): Database session.
        work (Work): The work.
        user (User): The logged in user whose approval triggered the payment.
        payment_type (str): What the payment is for: labourer, subcontractor or retention.
        amount (Decimal): Amount in KES.
        recipient_name (str): Name of the person being paid.
        recipient_phone (str): Phone number the money is sent to.
        labourer (Optional[Labourer]): The labourer being paid, if any.
        recipient_user (Optional[User]): The platform user being paid, if any.

    Returns:
        PaymentRecord: The stored payment record.
    """
    provider = get_payment_provider()
    remarks = f"Work {work.id} - {payment_type}"
    result = provider.send(recipient_phone, amount, remarks)
    record = PaymentRecord(
        project_id=work.project_id,
        work_id=work.id,
        labourer_id=labourer.id if labourer else None,
        recipient_user_id=recipient_user.id if recipient_user else None,
        initiated_by_id=user.id,
        payment_type=payment_type,
        recipient_name=recipient_name,
        recipient_phone=recipient_phone,
        amount_requested=amount,
        amount_paid=amount if result.successful else Decimal("0"),
        successful=result.successful,
        provider=provider.name,
        provider_reference=result.reference,
        provider_response=result.raw_response,
        failure_reason="" if result.successful else result.message,
        paid_at=utc_now() if result.successful else None,
    )
    db.add(record)
    if result.successful:
        debit_wallet(db, work.project, amount, f"{payment_type} payment {result.reference}", user)
    db.flush()
    return record


def request_payment(
    db: Session, work: Work, user: User, background_tasks: BackgroundTasks
) -> Work:
    """
    Mark a work as ready for payment and notify the approvers.

    Args:
        db (Session): Database session.
        work (Work): The work.
        user (User): The logged in user performing the action.
        background_tasks (BackgroundTasks): FastAPI background tasks used to send emails after the response.

    Returns:
        Work: The work.
    """
    work = lock_work(db, work)
    # Check if the work has already been paid or requested
    if work.payment_status != PaymentStatus.PENDING.value:
        raise AppError("Payment for this work has already been processed")
    if work.payment_requested:
        raise AppError("Payment has already been requested for this work")
    work.payment_requested = True
    work.payment_requested_at = utc_now()
    db.commit()
    db.refresh(work)
    # Notify the main contractor and contractor supervisors
    recipients = notification_service.main_contractor_of(work)
    recipients += notification_service.contractor_supervisors_of(work)
    notification_service.notify_users(
        background_tasks,
        recipients,
        "Payment Approval Request",
        f"{user.full_name} has requested payment for this work. Please review and approve.",
        work,
    )
    return work


def _check_ready_for_approval(work: Work, background_tasks: BackgroundTasks) -> None:
    """
    Check every approval needed before payment. Notifies the subcontractor when blocked.

    Args:
        work (Work): The work.
        background_tasks (BackgroundTasks): FastAPI background tasks used to send emails after the response.
    """
    # Check if payment has been requested
    if not work.payment_requested:
        raise AppError("Payment has not been requested for this work yet")
    # Check if cost is approved by main contractor
    if not work.cost_approval:
        notification_service.notify_users(
            background_tasks,
            notification_service.subcontractor_of(work),
            "Cost Approval Required",
            "The main contractor has not approved the cost of this work. Please review the cost.",
            work,
        )
        raise AppError(
            "Cost not approved by main contractor. Subcontractor has been notified to revise the cost."
        )
    # Check if contractor supervisor has approved the work
    if not work.contractor_supervisor_approval:
        raise AppError("Work not approved by contractor supervisor")
    # Check if attendance has been confirmed
    if not work.attendance_approval:
        notification_service.notify_users(
            background_tasks,
            notification_service.subcontractor_of(work),
            "Attendance Approval Required",
            "Labourer attendance for this work has not been approved by the contractor supervisor.",
            work,
        )
        raise AppError(
            "Attendance not confirmed. Subcontractor has been notified to seek attendance approval."
        )


def approve_payment(
    db: Session,
    work: Work,
    approval_type: str,
    user: User,
    background_tasks: BackgroundTasks,
) -> PaymentOutcome:
    """
    Give one of the two payment approvals; pay out once both are given.

    ``approval_type`` is ``main_contractor`` or ``contractor_supervisor``
    (the router checks the matching permission).

    Args:
        db (Session): Database session.
        work (Work): The work.
        approval_type (str): Which payment approval to give.
        user (User): The logged in user performing the action.
        background_tasks (BackgroundTasks): FastAPI background tasks used to send emails after the response.

    Returns:
        PaymentOutcome: Outcome with a message, payment counts and the updated work.
    """
    work = lock_work(db, work)
    # Check if payment has already been processed
    if work.payment_status == PaymentStatus.PAID.value:
        return PaymentOutcome("Payment has already been processed for this work.", work)
    if work.payment_status == PaymentStatus.APPROVED.value:
        raise AppError("Payment was processed but some payments failed. Retry the failed payments.")

    _check_ready_for_approval(work, background_tasks)

    # Record the approval and remind the other approver
    if approval_type == CONTRACTOR_SUPERVISOR:
        work.contractor_supervisor_payment_approval = True
        if not work.main_contractor_payment_approval:
            notification_service.notify_users(
                background_tasks,
                notification_service.main_contractor_of(work),
                "Payment Approval Reminder",
                "The contractor supervisor has approved payment. Your approval is still needed.",
                work,
            )
    elif approval_type == MAIN_CONTRACTOR:
        work.main_contractor_payment_approval = True
        if not work.contractor_supervisor_payment_approval:
            notification_service.notify_users(
                background_tasks,
                notification_service.contractor_supervisors_of(work),
                "Payment Approval Reminder",
                "The main contractor has approved payment. Your approval is still needed.",
                work,
            )
    else:
        raise AppError("approval_type must be 'main_contractor' or 'contractor_supervisor'")

    # Wait until both approvals are given before paying
    if not (work.contractor_supervisor_payment_approval and work.main_contractor_payment_approval):
        db.commit()
        db.refresh(work)
        return PaymentOutcome(f"{approval_type} payment approval recorded", work)

    return _process_payout(db, work, user, background_tasks)


def _process_payout(
    db: Session, work: Work, user: User, background_tasks: BackgroundTasks
) -> PaymentOutcome:
    """
    Pay every labourer, then the subcontractor. Called once both approvals exist.

    Args:
        db (Session): Database session.
        work (Work): The work.
        user (User): The logged in user performing the action.
        background_tasks (BackgroundTasks): FastAPI background tasks used to send emails after the response.

    Returns:
        PaymentOutcome: Outcome with a message, payment counts and the updated work.
    """
    # Check if the project wallet has enough money
    if work.total_cost > usable_wallet_balance(work):
        work.reset_payment_request()
        db.commit()
        raise AppError("Insufficient funds in project wallet to approve payment.")

    # Check if labour due is within the original estimate
    labour_due = total_labour_due(work)
    if labour_due > Decimal(work.cost_labor):
        work.reset_payment_request()
        db.commit()
        raise AppError(
            f"Labour cost {labour_due} exceeds original estimate {work.cost_labor}."
        )
    # Check if there is anyone to pay
    if not work.labourer_links and work.assigned_subcontractor is None:
        work.reset_payment_request()
        db.commit()
        raise AppError("This work has no labourers and no subcontractor to pay")

    made = 0
    failed = 0
    # Pay every labourer
    for link in work.labourer_links:
        labourer = link.labourer
        record = _send_payment(
            db, work, user, PaymentType.LABOURER.value, link.amount_due,
            labourer.name, labourer.phone_number, labourer=labourer,
        )
        if record.successful:
            made += 1
            labourer.project_lifetime_approved_working_days += link.days_worked
        else:
            failed += 1

    # Pay the subcontractor what is left
    subcontractor = work.assigned_subcontractor
    if subcontractor is not None:
        amount = subcontractor_amount(work)
        if amount > 0:
            record = _send_payment(
                db, work, user, PaymentType.SUBCONTRACTOR.value, amount,
                subcontractor.full_name, subcontractor.phone_number,
                recipient_user=subcontractor,
            )
            if record.successful:
                made += 1
            else:
                failed += 1

    # Save the totals and notify the subcontractor and main contractor
    work.payment_approved_at = utc_now()
    _update_payment_totals(db, work)
    db.commit()
    db.refresh(work)

    notification_service.notify_users(
        background_tasks,
        notification_service.subcontractor_of(work) + notification_service.main_contractor_of(work),
        "Payment Processed",
        f"Payment for this work has been processed: {made} successful, {failed} failed.",
        work,
    )
    message = "Payment approved and processed successfully"
    if failed:
        message = f"Payment processed with {failed} failed payment(s). Retry the failed payments."
    return PaymentOutcome(message, work, made, failed)


def _outstanding_failed_records(db: Session, work: Work) -> List[PaymentRecord]:
    """
    Failed labourer/subcontractor payments of the work that were not retried yet.

    Args:
        db (Session): Database session.
        work (Work): The work.

    Returns:
        List[PaymentRecord]: List of payment records.
    """
    statement = select(PaymentRecord).where(
        PaymentRecord.work_id == work.id,
        PaymentRecord.successful.is_(False),
        PaymentRecord.is_retried.is_(False),
        PaymentRecord.payment_type != PaymentType.RETENTION.value,
    )
    return list(db.scalars(statement).all())


def _failed_retention_records(db: Session, work: Work) -> List[PaymentRecord]:
    """
    Failed retention payments of the work that were not retried yet.

    Args:
        db (Session): Database session.
        work (Work): The work.

    Returns:
        List[PaymentRecord]: List of payment records.
    """
    statement = select(PaymentRecord).where(
        PaymentRecord.work_id == work.id,
        PaymentRecord.successful.is_(False),
        PaymentRecord.is_retried.is_(False),
        PaymentRecord.payment_type == PaymentType.RETENTION.value,
    )
    return list(db.scalars(statement).all())


def _update_payment_totals(db: Session, work: Work) -> None:
    """
    Recalculate amount paid to labourers, payment status and completion.

    Args:
        db (Session): Database session.
        work (Work): The work.
    """
    db.flush()
    # Add up what labourers have been paid
    statement = select(PaymentRecord).where(
        PaymentRecord.work_id == work.id,
        PaymentRecord.successful.is_(True),
        PaymentRecord.payment_type == PaymentType.LABOURER.value,
    )
    paid_out = Decimal("0")
    for record in db.scalars(statement).all():
        paid_out += Decimal(record.amount_paid)
    work.total_labourers_paid_out = paid_out

    # The work is only paid once no failed payments are left
    if _outstanding_failed_records(db, work):
        work.payment_status = PaymentStatus.APPROVED.value
    else:
        work.payment_status = PaymentStatus.PAID.value
        work.payment_completed_at = utc_now()
    refresh_work_completion(work)


def _retry_recipient(record: PaymentRecord) -> Tuple[str, str]:
    """
    Name and phone number to use when retrying a failed payment.

    The current details of the labourer or user are used, so a corrected phone
    number is picked up. The details saved on the record are the fallback.

    Args:
        record (PaymentRecord): The failed payment record.

    Returns:
        Tuple[str, str]: The recipient's name and phone number.
    """
    if record.labourer is not None:
        return record.labourer.name, record.labourer.phone_number
    if record.recipient_user is not None:
        return record.recipient_user.full_name, record.recipient_user.phone_number
    return record.recipient_name, record.recipient_phone


def retry_failed_payments(db: Session, work: Work, user: User) -> PaymentOutcome:
    """
    Send every failed (not yet retried) payment of the work again.

    Args:
        db (Session): Database session.
        work (Work): The work.
        user (User): The logged in user performing the action.

    Returns:
        PaymentOutcome: Outcome with a message, payment counts and the updated work.
    """
    work = lock_work(db, work)
    failed_records = _outstanding_failed_records(db, work)
    # Check if there are failed payments to retry
    if not failed_records:
        raise AppError("There are no failed payments to retry for this work")
    # Check if the project wallet can cover the retries
    total = Decimal("0")
    for record in failed_records:
        total += Decimal(record.amount_requested)
    if total > usable_wallet_balance(work):
        raise AppError("Insufficient funds in project wallet to retry the payments.")

    made = 0
    failed = 0
    # Send each failed payment again as a new record
    for old in failed_records:
        old.is_retried = True
        labourer = old.labourer
        name, phone = _retry_recipient(old)
        record = _send_payment(
            db, work, user, old.payment_type, Decimal(old.amount_requested), name, phone,
            labourer=labourer, recipient_user=old.recipient_user,
        )
        if record.successful:
            made += 1
            if labourer is not None:
                for link in work.labourer_links:
                    if link.labourer_id == labourer.id:
                        labourer.project_lifetime_approved_working_days += link.days_worked
        else:
            failed += 1

    _update_payment_totals(db, work)
    db.commit()
    db.refresh(work)
    message = "All failed payments were retried successfully"
    if failed:
        message = f"{made} payment(s) succeeded, {failed} still failed"
    return PaymentOutcome(message, work, made, failed)


def request_retention(
    db: Session, work: Work, user: User, background_tasks: BackgroundTasks
) -> Work:
    """
    Ask the main contractor to release retention money for a paid work.

    Args:
        db (Session): Database session.
        work (Work): The work.
        user (User): The logged in user performing the action.
        background_tasks (BackgroundTasks): FastAPI background tasks used to send emails after the response.

    Returns:
        Work: The work.
    """
    work = lock_work(db, work)
    # Check if retention money can be requested for this work
    if work.assigned_subcontractor_id is None:
        raise AppError("Retention money only applies to works with a subcontractor")
    if work.payment_status != PaymentStatus.PAID.value:
        raise AppError("The work must be fully paid before retention money can be requested")
    if work.retention_paid:
        raise AppError("Retention money has already been paid")
    if work.retention_payment_requested:
        raise AppError("Retention money has already been requested")
    work.retention_payment_requested = True
    db.commit()
    db.refresh(work)
    # Notify the main contractor
    notification_service.notify_users(
        background_tasks,
        notification_service.main_contractor_of(work),
        "Retention Money Request",
        f"{user.full_name} has requested release of retention money "
        f"(KES {retention_amount_due(db, work):,.2f}).",
        work,
    )
    return work


def approve_retention(
    db: Session, work: Work, user: User, background_tasks: BackgroundTasks
) -> PaymentOutcome:
    """
    Pay the retention money to the subcontractor (main contractor only).

    Args:
        db (Session): Database session.
        work (Work): The work.
        user (User): The logged in user performing the action.
        background_tasks (BackgroundTasks): FastAPI background tasks used to send emails after the response.

    Returns:
        PaymentOutcome: Outcome with a message, payment counts and the updated work.
    """
    work = lock_work(db, work)
    # Check if retention money can be paid
    if work.retention_paid:
        return PaymentOutcome("Retention money has already been paid", work)
    if not work.retention_payment_requested:
        raise AppError("Retention money has not been requested")
    if work.payment_status != PaymentStatus.PAID.value:
        raise AppError("The work must be fully paid before retention money is released")
    subcontractor = work.assigned_subcontractor
    if subcontractor is None:
        raise AppError("This work has no subcontractor")
    amount = retention_amount_due(db, work)
    work.retention_payment_approved = True
    # Nothing left to pay, mark it as paid
    if amount == 0:
        work.retention_paid = True
        refresh_work_completion(work)
        db.commit()
        db.refresh(work)
        return PaymentOutcome("No retention money is left to pay for this work", work)
    # Check if the project wallet has enough money
    if amount > usable_wallet_balance(work):
        raise AppError("Insufficient funds in project wallet to pay retention money.")

    # Pay the retention money; an earlier failed attempt counts as retried
    for old in _failed_retention_records(db, work):
        old.is_retried = True
    record = _send_payment(
        db, work, user, PaymentType.RETENTION.value, amount,
        subcontractor.full_name, subcontractor.phone_number, recipient_user=subcontractor,
    )
    if record.successful:
        work.retention_paid = True
    refresh_work_completion(work)
    db.commit()
    db.refresh(work)

    if not record.successful:
        return PaymentOutcome(
            "Retention payment failed. You can approve it again to retry.", work, 0, 1
        )

    # Notify the subcontractor that it has been paid
    notification_service.notify_users(
        background_tasks,
        notification_service.subcontractor_of(work),
        "Retention Money Paid",
        f"Retention money of KES {amount:,.2f} has been paid to you.",
        work,
    )
    return PaymentOutcome("Retention money paid successfully", work, 1, 0)


def payment_summary(db: Session, work: Work) -> dict:
    """
    Breakdown of the amounts a work pays out, for review before approving.

    Args:
        db (Session): Database session.
        work (Work): The work.

    Returns:
        dict: Amounts paid, due and failed for the work.
    """
    return {
        "work_id": work.id,
        "total_cost": work.total_cost,
        "cost_labor": work.cost_labor,
        "cost_overhead": work.cost_overhead,
        "total_labour_due": total_labour_due(work),
        "retention_money": work.retention_money,
        "subcontractor_amount": max(subcontractor_amount(work), Decimal("0")),
        "total_labourers_paid_out": work.total_labourers_paid_out,
        "usable_wallet_balance": usable_wallet_balance(work).quantize(Decimal("0.01")),
        "payment_status": work.payment_status,
        "failed_payments_outstanding": len(_outstanding_failed_records(db, work)),
    }


def list_payment_records(
    db: Session,
    project_id: Optional[uuid.UUID] = None,
    work_id: Optional[uuid.UUID] = None,
    labourer_id: Optional[uuid.UUID] = None,
    successful: Optional[bool] = None,
    subcontractor_id: Optional[uuid.UUID] = None,
    project_ids: Optional[List[uuid.UUID]] = None,
) -> List[PaymentRecord]:
    """
    Return payment records filtered by project, work, labourer and/or outcome.

    ``subcontractor_id`` limits the records to works assigned to that
    subcontractor (subcontractors must not see each other's payments).

    Args:
        db (Session): Database session.
        project_id (Optional[uuid.UUID]): ID of the project.
        work_id (Optional[uuid.UUID]): ID of the work.
        labourer_id (Optional[uuid.UUID]): ID of the labourer.
        successful (Optional[bool]): True for successful payments only, False for failed only, None for both.
        subcontractor_id (Optional[uuid.UUID]): ID of the subcontractor.
        project_ids (Optional[List[uuid.UUID]]): Only records of these projects (the projects a user is on).

    Returns:
        List[PaymentRecord]: List of payment records.
    """
    statement = select(PaymentRecord).order_by(PaymentRecord.created_at.desc())
    if project_ids is not None:
        statement = statement.where(PaymentRecord.project_id.in_(project_ids))
    if subcontractor_id is not None:
        statement = statement.join(Work, PaymentRecord.work_id == Work.id).where(
            Work.assigned_subcontractor_id == subcontractor_id
        )
    if project_id is not None:
        statement = statement.where(PaymentRecord.project_id == project_id)
    if work_id is not None:
        statement = statement.where(PaymentRecord.work_id == work_id)
    if labourer_id is not None:
        statement = statement.where(PaymentRecord.labourer_id == labourer_id)
    if successful is not None:
        statement = statement.where(PaymentRecord.successful.is_(successful))
    return list(db.scalars(statement).all())
