"""Schemas for reports."""
import uuid
from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel

from app.constants.choices import PaymentStatus, PaymentType

ReportType = Literal["payments", "labourers", "works", "projects"]
ReportFormat = Literal["json", "html", "pdf"]


class ReportItem(BaseModel):
    """A label and value pair, used for filters and totals."""

    label: str
    value: str


class ReportRead(BaseModel):
    """A report as JSON. The same data is used for the HTML and PDF versions."""

    report_type: str
    title: str
    generated_at: datetime
    generated_by: str
    filters: List[ReportItem]
    columns: List[str]
    rows: List[List[str]]
    summary: List[ReportItem]


class ReportEmailRequest(BaseModel):
    """
    Email a report as a PDF to the requesting user.

    Only the filters that apply to the chosen report type are used.
    """

    report_type: ReportType
    project_id: Optional[uuid.UUID] = None
    successful: Optional[bool] = None
    payment_type: Optional[PaymentType] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    payment_status: Optional[PaymentStatus] = None
    is_completed: Optional[bool] = None
