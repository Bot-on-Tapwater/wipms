"""Printable reports: payments, labourers, works and projects.

Every report is built as a ``Report`` (title, columns, rows, summary) so it
can be returned as JSON, rendered to printable HTML, or converted to PDF
with the same template. Users only see data from projects they can access,
and subcontractors only see their own works.
"""
import io
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session
from xhtml2pdf import pisa

from app.constants.choices import PaymentStatus, label_for
from app.constants.roles import Role
from app.core.config import settings
from app.core.database import utc_now
from app.core.exceptions import AppError
from app.core.templates import render_template
from app.models.labourer import Labourer
from app.models.payment import PaymentRecord
from app.models.project import Project
from app.models.user import User
from app.models.work import Work
from app.services.access_service import get_accessible_project
from app.services.project_service import list_projects_for_user

REPORT_TYPES = ("payments", "labourers", "works", "projects")


@dataclass
class Report:
    """A report ready to be shown as JSON, HTML or PDF."""

    report_type: str
    title: str
    columns: List[str]
    rows: List[List[str]]
    summary: List[Tuple[str, str]] = field(default_factory=list)
    filters: List[Tuple[str, str]] = field(default_factory=list)
    generated_by: str = ""
    generated_at: datetime = field(default_factory=utc_now)


def money(value: Optional[Decimal]) -> str:
    """
    Format an amount as ``KES 1,234.50``.

    Args:
        value (Optional[Decimal]): Amount, or None.

    Returns:
        str: The amount formatted like ``KES 1,234.00``.
    """
    if value is None:
        value = Decimal("0")
    return f"KES {Decimal(value):,.2f}"


def date_text(value: Optional[datetime]) -> str:
    """
    Format a datetime as ``2025-01-31 14:05`` (empty when missing).

    Args:
        value (Optional[datetime]): Date or datetime, or None.

    Returns:
        str: The date as text, or an empty string.
    """
    if value is None:
        return ""
    return value.strftime("%Y-%m-%d %H:%M")


def yes_no(value: bool) -> str:
    """
    Show a boolean as Yes / No.

    Args:
        value (bool): Boolean value.

    Returns:
        str: ``Yes`` or ``No``.
    """
    return "Yes" if value else "No"


def start_of_day(value: date) -> datetime:
    """
    Midnight UTC at the start of the given date.

    Args:
        value (date): The date.

    Returns:
        datetime: Midnight at the start of the day.
    """
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def end_of_day(value: date) -> datetime:
    """
    The last moment (UTC) of the given date.

    Args:
        value (date): The date.

    Returns:
        datetime: The last moment of the day.
    """
    return datetime.combine(value, time.max, tzinfo=timezone.utc)


def visible_projects(db: Session, user: User, project_id: Optional[uuid.UUID]) -> List[Project]:
    """
    Projects the report may include: one project, or all the user can see.

    Args:
        db (Session): Database session.
        user (User): The logged in user performing the action.
        project_id (Optional[uuid.UUID]): ID of the project.

    Returns:
        List[Project]: List of projects.
    """
    if project_id is not None:
        return [get_accessible_project(db, project_id, user)]
    return list_projects_for_user(db, user)


def visible_works(db: Session, user: User, projects: List[Project]) -> List[Work]:
    """
    Works in the given projects. Subcontractors only get their own works.

    Args:
        db (Session): Database session.
        user (User): The logged in user performing the action.
        projects (List[Project]): Projects to include.

    Returns:
        List[Work]: List of works.
    """
    project_ids = [project.id for project in projects]
    if not project_ids:
        return []
    statement = select(Work).where(Work.project_id.in_(project_ids)).order_by(Work.created_at)
    if user.role == Role.SUBCONTRACTOR.value:
        statement = statement.where(Work.assigned_subcontractor_id == user.id)
    return list(db.scalars(statement).all())


def _filters_text(project: Optional[Project], extra: Dict[str, str]) -> List[Tuple[str, str]]:
    """
    Describe the filters used, for the report header.

    Args:
        project (Optional[Project]): Project filter, or None.
        extra (Dict[str, str]): Extra filter labels and values; empty values are skipped.

    Returns:
        List[Tuple[str, str]]: List of (label, value) tuples.
    """
    result = [("Project", project.name if project else "All accessible projects")]
    for label, value in extra.items():
        if value:
            result.append((label, value))
    return result


def _load_payment_records(
    db: Session,
    work_ids: List[uuid.UUID],
    successful: Optional[bool],
    payment_type: Optional[str],
    date_from: Optional[date],
    date_to: Optional[date],
) -> List[PaymentRecord]:
    """
    Load the payment records of the given works that match the filters, newest first.

    Args:
        db (Session): Database session.
        work_ids (List[uuid.UUID]): IDs of the works the user is allowed to see.
        successful (Optional[bool]): True for successful payments only, False for failed only, None for both.
        payment_type (Optional[str]): Only include this payment type.
        date_from (Optional[date]): Only include records on or after this date.
        date_to (Optional[date]): Only include records on or before this date.

    Returns:
        List[PaymentRecord]: The matching payment records.
    """
    if not work_ids:
        return []
    statement = select(PaymentRecord).where(PaymentRecord.work_id.in_(work_ids))
    if successful is not None:
        statement = statement.where(PaymentRecord.successful.is_(successful))
    if payment_type:
        statement = statement.where(PaymentRecord.payment_type == payment_type)
    if date_from is not None:
        statement = statement.where(PaymentRecord.created_at >= start_of_day(date_from))
    if date_to is not None:
        statement = statement.where(PaymentRecord.created_at <= end_of_day(date_to))
    statement = statement.order_by(PaymentRecord.created_at.desc())
    return list(db.scalars(statement).all())


def payments_report(
    db: Session,
    user: User,
    project_id: Optional[uuid.UUID] = None,
    successful: Optional[bool] = None,
    payment_type: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> Report:
    """
    All payment attempts (successful and failed), newest first.

    Args:
        db (Session): Database session.
        user (User): The logged in user performing the action.
        project_id (Optional[uuid.UUID]): ID of the project.
        successful (Optional[bool]): True for successful payments only, False for failed only, None for both.
        payment_type (Optional[str]): Only include this payment type.
        date_from (Optional[date]): Only include records on or after this date.
        date_to (Optional[date]): Only include records on or before this date.

    Returns:
        Report: The report data.
    """
    # Get the payment records the user is allowed to see
    projects = visible_projects(db, user, project_id)
    work_ids = [work.id for work in visible_works(db, user, projects)]
    records = _load_payment_records(db, work_ids, successful, payment_type, date_from, date_to)

    # Build one row per payment and add up the totals
    rows = []
    total_paid = Decimal("0")
    total_failed = Decimal("0")
    failed_count = 0
    for record in records:
        status = "Successful" if record.successful else "Failed"
        if record.successful:
            total_paid += Decimal(record.amount_paid)
        else:
            failed_count += 1
            total_failed += Decimal(record.amount_requested)
            if record.is_retried:
                status = "Failed (retried)"
        rows.append([
            date_text(record.created_at),
            record.project.name,
            record.work.title,
            label_for(record.payment_type),
            record.recipient_name,
            record.recipient_phone,
            money(record.amount_requested),
            money(record.amount_paid),
            status,
            record.provider_reference,
            record.failure_reason,
        ])

    # Describe the filters used at the top of the report
    status_filter = ""
    if successful is True:
        status_filter = "Successful only"
    elif successful is False:
        status_filter = "Failed only"
    filters = _filters_text(
        projects[0] if project_id else None,
        {
            "Status": status_filter,
            "Payment type": label_for(payment_type) if payment_type else "",
            "From": date_from.isoformat() if date_from else "",
            "To": date_to.isoformat() if date_to else "",
        },
    )
    return Report(
        report_type="payments",
        title="Payments Report",
        columns=[
            "Date", "Project", "Work", "Type", "Recipient", "Phone",
            "Amount", "Paid", "Status", "Reference", "Failure reason",
        ],
        rows=rows,
        summary=[
            ("Payment attempts", str(len(records))),
            ("Successful", str(len(records) - failed_count)),
            ("Failed", str(failed_count)),
            ("Total paid", money(total_paid)),
            ("Total failed", money(total_failed)),
        ],
        filters=filters,
        generated_by=user.full_name,
    )


def labourers_report(db: Session, user: User, project_id: Optional[uuid.UUID] = None) -> Report:
    """
    Labourers on the visible works with days worked and amounts paid.

    Args:
        db (Session): Database session.
        user (User): The logged in user performing the action.
        project_id (Optional[uuid.UUID]): ID of the project.

    Returns:
        Report: The report data.
    """
    projects = visible_projects(db, user, project_id)
    works = visible_works(db, user, projects)

    # Count the works and days of each labourer
    labourers: Dict[uuid.UUID, Labourer] = {}
    days: Dict[uuid.UUID, int] = {}
    work_count: Dict[uuid.UUID, int] = {}
    for work in works:
        for link in work.labourer_links:
            labourer_id = link.labourer_id
            labourers[labourer_id] = link.labourer
            days[labourer_id] = days.get(labourer_id, 0) + link.days_worked
            work_count[labourer_id] = work_count.get(labourer_id, 0) + 1

    # Add up what each labourer has been paid
    paid: Dict[uuid.UUID, Decimal] = {}
    work_ids = [work.id for work in works]
    if work_ids:
        statement = select(PaymentRecord).where(
            PaymentRecord.work_id.in_(work_ids),
            PaymentRecord.labourer_id.is_not(None),
            PaymentRecord.successful.is_(True),
        )
        for record in db.scalars(statement).all():
            paid[record.labourer_id] = paid.get(record.labourer_id, Decimal("0")) + Decimal(
                record.amount_paid
            )

    # Build one row per labourer, sorted by name
    rows = []
    total_paid = Decimal("0")
    for labourer in sorted(labourers.values(), key=_labourer_sort_key):
        amount = paid.get(labourer.id, Decimal("0"))
        total_paid += amount
        rows.append([
            labourer.name,
            labourer.national_id_number,
            label_for(labourer.title),
            labourer.phone_number,
            money(labourer.daily_rate),
            str(work_count[labourer.id]),
            str(days[labourer.id]),
            str(labourer.project_lifetime_approved_working_days),
            money(amount),
        ])
    return Report(
        report_type="labourers",
        title="Labourers Report",
        columns=[
            "Name", "ID number", "Title", "Phone", "Daily rate", "Works",
            "Days worked", "Lifetime approved days", "Total paid",
        ],
        rows=rows,
        summary=[("Labourers", str(len(rows))), ("Total paid", money(total_paid))],
        filters=_filters_text(projects[0] if project_id else None, {}),
        generated_by=user.full_name,
    )


def _labourer_sort_key(labourer: Labourer) -> str:
    """
    Sort labourers alphabetically by name.

    Args:
        labourer (Labourer): The labourer.

    Returns:
        str: The labourer's name in lower case.
    """
    return labourer.name.lower()


def works_report(
    db: Session,
    user: User,
    project_id: Optional[uuid.UUID] = None,
    payment_status: Optional[str] = None,
    is_completed: Optional[bool] = None,
) -> Report:
    """
    Works with their cost, approvals and payment state.

    Args:
        db (Session): Database session.
        user (User): The logged in user performing the action.
        project_id (Optional[uuid.UUID]): ID of the project.
        payment_status (Optional[str]): Only include works with this payment status.
        is_completed (Optional[bool]): Only include completed (True) or unfinished (False) works.

    Returns:
        Report: The report data.
    """
    projects = visible_projects(db, user, project_id)
    rows = []
    total_cost = Decimal("0")
    # Build one row per work, skipping works that do not match the filters
    for work in visible_works(db, user, projects):
        if payment_status and work.payment_status != payment_status:
            continue
        if is_completed is not None and work.is_completed != is_completed:
            continue
        total_cost += work.total_cost
        subcontractor = work.assigned_subcontractor
        rows.append([
            work.project.name,
            work.title,
            label_for(work.category),
            subcontractor.full_name if subcontractor else "",
            money(work.total_cost),
            str(len(work.labourer_links)),
            yes_no(work.is_fully_approved),
            label_for(work.payment_status),
            money(work.total_labourers_paid_out),
            yes_no(work.retention_paid),
            yes_no(work.is_completed),
        ])
    # Describe the filters used at the top of the report
    completed_filter = ""
    if is_completed is not None:
        completed_filter = yes_no(is_completed)
    filters = _filters_text(
        projects[0] if project_id else None,
        {
            "Payment status": label_for(payment_status) if payment_status else "",
            "Completed": completed_filter,
        },
    )
    return Report(
        report_type="works",
        title="Works Report",
        columns=[
            "Project", "Work", "Category", "Subcontractor", "Total cost", "Labourers",
            "Fully approved", "Payment status", "Paid to labourers", "Retention paid", "Completed",
        ],
        rows=rows,
        summary=[("Works", str(len(rows))), ("Total cost", money(total_cost))],
        filters=filters,
        generated_by=user.full_name,
    )


def projects_report(db: Session, user: User) -> Report:
    """
    Projects with wallet balance, work counts and amounts paid.

    Args:
        db (Session): Database session.
        user (User): The logged in user performing the action.

    Returns:
        Report: The report data.
    """
    rows = []
    for project in list_projects_for_user(db, user):
        works = visible_works(db, user, [project])
        total_cost = Decimal("0")
        paid_count = 0
        work_ids = []
        # Add up the cost of the works and count the paid ones
        for work in works:
            total_cost += work.total_cost
            work_ids.append(work.id)
            if work.payment_status == PaymentStatus.PAID.value:
                paid_count += 1
        # Only payments of the visible works, so subcontractors never see
        # amounts paid on other subcontractors' works.
        statement = select(PaymentRecord).where(
            PaymentRecord.work_id.in_(work_ids), PaymentRecord.successful.is_(True)
        )
        total_paid = Decimal("0")
        for record in db.scalars(statement).all():
            total_paid += Decimal(record.amount_paid)
        rows.append([
            project.name,
            project.location,
            project.created_by.full_name if project.created_by else "",
            str(len(works)),
            str(paid_count),
            money(total_cost),
            money(total_paid),
            money(project.wallet_balance),
            yes_no(project.is_completed),
        ])
    return Report(
        report_type="projects",
        title="Projects Report",
        columns=[
            "Project", "Location", "Main contractor", "Works", "Works paid",
            "Total cost", "Total paid", "Wallet balance", "Completed",
        ],
        rows=rows,
        summary=[("Projects", str(len(rows)))],
        filters=[],
        generated_by=user.full_name,
    )


def render_report_html(report: Report, for_pdf: bool = False) -> str:
    """
    Render the report as a printable HTML page (no print button in PDFs).

    Args:
        report (Report): The report to render.
        for_pdf (bool): True when the HTML is converted to PDF (hides the print button).

    Returns:
        str: The report as an HTML page.
    """
    return render_template(
        "reports/report.html",
        {"report": report, "app_name": settings.APP_NAME, "for_pdf": for_pdf},
    )


def render_report_pdf(report: Report) -> bytes:
    """
    Convert the printable HTML report to a PDF document.

    Args:
        report (Report): The report to render.

    Returns:
        bytes: The report as PDF bytes.
    """
    output = io.BytesIO()
    result = pisa.CreatePDF(render_report_html(report, for_pdf=True), dest=output, encoding="utf-8")
    if result.err:
        raise AppError("Could not generate the PDF report", status_code=500)
    return output.getvalue()


def report_filename(report: Report, extension: str) -> str:
    """
    File name like ``payments-report-2025-01-31.pdf``.

    Args:
        report (Report): The report being downloaded.
        extension (str): File extension without the dot.

    Returns:
        str: Download file name for the report.
    """
    return f"{report.report_type}-report-{report.generated_at:%Y-%m-%d}.{extension}"
