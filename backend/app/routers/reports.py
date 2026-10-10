"""Report endpoints.

Each report can be returned as JSON (``format=json``, default), as a
printable HTML page (``format=html``) or as a PDF download (``format=pdf``).
All reports need the ``reports.view`` permission and only include projects
the user can access.
"""
import uuid
from datetime import date
from typing import List, Optional, Tuple, Union

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.constants.choices import PaymentStatus, PaymentType
from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.report import ReportEmailRequest, ReportFormat, ReportItem, ReportRead
from app.services import report_service
from app.services.email_service import queue_email
from app.services.report_service import Report

router = APIRouter(prefix="/reports", tags=["Reports"])

REPORT_RESPONSES = {
    200: {
        "description": "The report as JSON, printable HTML or a PDF file",
        "content": {"text/html": {}, "application/pdf": {}},
    }
}


def _items(pairs: List[Tuple[str, str]]) -> List[ReportItem]:
    """
    Convert (label, value) pairs into ReportItem objects.

    Args:
        pairs (List[Tuple[str, str]]): List of (label, value) tuples.

    Returns:
        List[ReportItem]: List of ReportItem objects.
    """
    result = []
    for label, value in pairs:
        result.append(ReportItem(label=label, value=value))
    return result


def report_response(report: Report, output_format: str) -> Union[ReportRead, Response]:
    """
    Return the report in the requested format.

    Args:
        report (Report): The report to render.
        output_format (str): Output format: json, html or pdf.

    Returns:
        Union[ReportRead, Response]: The report as JSON, an HTML page or a PDF download.
    """
    if output_format == "html":
        return HTMLResponse(report_service.render_report_html(report))
    if output_format == "pdf":
        filename = report_service.report_filename(report, "pdf")
        return Response(
            content=report_service.render_report_pdf(report),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    return ReportRead(
        report_type=report.report_type,
        title=report.title,
        generated_at=report.generated_at,
        generated_by=report.generated_by,
        filters=_items(report.filters),
        columns=report.columns,
        rows=report.rows,
        summary=_items(report.summary),
    )


def _enum_value(value: Optional[object]) -> Optional[str]:
    """
    Return the string value of an optional enum.

    Args:
        value (Optional[object]): An enum member or None.

    Returns:
        Optional[str]: The enum's value, or None.
    """
    if value is None:
        return None
    return value.value


@router.get("/payments", response_model=ReportRead, responses=REPORT_RESPONSES)
def payments_report(
    project_id: Optional[uuid.UUID] = None,
    successful: Optional[bool] = None,
    payment_type: Optional[PaymentType] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    format: ReportFormat = "json",
    user: User = Depends(require_permission("reports.view")),
    db: Session = Depends(get_db),
) -> Union[ReportRead, Response]:
    """
    Payments report: successful and failed payments.

    Use ``successful=true`` for successful payments only or
    ``successful=false`` for failed payments only.

    Args:
        project_id (Optional[uuid.UUID]): ID of the project.
        successful (Optional[bool]): True for successful payments only, False for failed only, None for both.
        payment_type (Optional[PaymentType]): Only include this payment type.
        date_from (Optional[date]): Only include records on or after this date.
        date_to (Optional[date]): Only include records on or before this date.
        format (ReportFormat): Output format: json, html or pdf.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        Union[ReportRead, Response]: The report as JSON, an HTML page or a PDF download.
    """
    report = report_service.payments_report(
        db, user, project_id, successful, _enum_value(payment_type), date_from, date_to
    )
    return report_response(report, format)


@router.get("/labourers", response_model=ReportRead, responses=REPORT_RESPONSES)
def labourers_report(
    project_id: Optional[uuid.UUID] = None,
    format: ReportFormat = "json",
    user: User = Depends(require_permission("reports.view")),
    db: Session = Depends(get_db),
) -> Union[ReportRead, Response]:
    """
    Labourers report: days worked and amounts paid per labourer.

    Args:
        project_id (Optional[uuid.UUID]): ID of the project.
        format (ReportFormat): Output format: json, html or pdf.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        Union[ReportRead, Response]: The report as JSON, an HTML page or a PDF download.
    """
    return report_response(report_service.labourers_report(db, user, project_id), format)


@router.get("/works", response_model=ReportRead, responses=REPORT_RESPONSES)
def works_report(
    project_id: Optional[uuid.UUID] = None,
    payment_status: Optional[PaymentStatus] = None,
    is_completed: Optional[bool] = None,
    format: ReportFormat = "json",
    user: User = Depends(require_permission("reports.view")),
    db: Session = Depends(get_db),
) -> Union[ReportRead, Response]:
    """
    Works report: cost, approvals and payment state of each work.

    Args:
        project_id (Optional[uuid.UUID]): ID of the project.
        payment_status (Optional[PaymentStatus]): Only include works with this payment status.
        is_completed (Optional[bool]): Only include completed (True) or unfinished (False) works.
        format (ReportFormat): Output format: json, html or pdf.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        Union[ReportRead, Response]: The report as JSON, an HTML page or a PDF download.
    """
    report = report_service.works_report(
        db, user, project_id, _enum_value(payment_status), is_completed
    )
    return report_response(report, format)


@router.get("/projects", response_model=ReportRead, responses=REPORT_RESPONSES)
def projects_report(
    format: ReportFormat = "json",
    user: User = Depends(require_permission("reports.view")),
    db: Session = Depends(get_db),
) -> Union[ReportRead, Response]:
    """
    Projects report: works, totals paid and wallet balance per project.

    Args:
        format (ReportFormat): Output format: json, html or pdf.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        Union[ReportRead, Response]: The report as JSON, an HTML page or a PDF download.
    """
    return report_response(report_service.projects_report(db, user), format)


@router.post("/email", response_model=MessageResponse)
def email_report(
    data: ReportEmailRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_permission("reports.view")),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Generate a report as PDF and email it to the logged in user.

    Args:
        data (ReportEmailRequest): Validated request body.
        background_tasks (BackgroundTasks): FastAPI background tasks used to send emails after the response.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        MessageResponse: A confirmation message.
    """
    report = build_report(db, user, data)
    pdf = report_service.render_report_pdf(report)
    queue_email(
        background_tasks,
        [user.email],
        report.title,
        "report.html",
        {"recipient_name": user.first_name, "report_title": report.title},
        attachments=[(report_service.report_filename(report, "pdf"), pdf, "pdf")],
    )
    return MessageResponse(message=f"{report.title} will be emailed to {user.email}")


def build_report(db: Session, user: User, data: ReportEmailRequest) -> Report:
    """
    Build the report described by an email request.

    Args:
        db (Session): Database session.
        user (User): The logged in user performing the action.
        data (ReportEmailRequest): Validated request body.

    Returns:
        Report: The report data.
    """
    if data.report_type == "payments":
        return report_service.payments_report(
            db, user, data.project_id, data.successful, _enum_value(data.payment_type),
            data.date_from, data.date_to,
        )
    if data.report_type == "labourers":
        return report_service.labourers_report(db, user, data.project_id)
    if data.report_type == "works":
        return report_service.works_report(
            db, user, data.project_id, _enum_value(data.payment_status), data.is_completed
        )
    return report_service.projects_report(db, user)
