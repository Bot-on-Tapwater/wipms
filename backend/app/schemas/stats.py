"""Schemas for labour insights."""
import uuid
from decimal import Decimal
from typing import List, Literal

from pydantic import BaseModel

GenderFilter = Literal["male", "female", "not_given"]
AgeGroupFilter = Literal["18-24", "25-34", "35-44", "45-54", "55+", "not_given"]


class StatsTotals(BaseModel):
    """Headline numbers for the chosen filters."""

    projects: int
    registered: int
    labourers: int
    days_worked: int
    amount_paid: Decimal


class StatsBucket(BaseModel):
    """One bar of a chart: labourers, days worked and pay for one group."""

    key: str
    label: str
    labourers: int
    days_worked: int
    amount_paid: Decimal


class ProjectStats(BaseModel):
    """Labourers, days worked and pay on one project, with its trades."""

    id: uuid.UUID
    name: str
    location: str
    labourers: int
    days_worked: int
    amount_paid: Decimal
    trades: List[StatsBucket]


class MonthStats(BaseModel):
    """Labourers registered and days worked in one month (``YYYY-MM``)."""

    month: str
    registered: int
    labourers: int
    days_worked: int


class TopLabourer(BaseModel):
    """A labourer who came back for the most works, and what they were paid."""

    id: uuid.UUID
    name: str
    trade: str
    works: int
    projects: int
    days_worked: int
    amount_paid: Decimal


class ProjectOption(BaseModel):
    """A project the user can pick in the project filter."""

    id: uuid.UUID
    name: str


class LabourStats(BaseModel):
    """
    Everything the Insights page shows.

    ``scope`` is ``all`` when the user sees every project and ``mine`` when
    they only see projects they created or are on.
    """

    scope: Literal["all", "mine"]
    projects: List[ProjectOption]
    totals: StatsTotals
    by_trade: List[StatsBucket]
    by_project: List[ProjectStats]
    by_gender: List[StatsBucket]
    by_age_group: List[StatsBucket]
    by_month: List[MonthStats]
    top_labourers: List[TopLabourer]
