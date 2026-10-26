"""Labour insights: labourers by trade, site, gender and age group, and pay per trade.

Users with ``stats.view_all`` see every project. Everyone else with
``stats.view`` only sees projects they created or are on the team of, even
if their role can see all projects elsewhere in the app.

Gender and age are only ever shown as totals, never next to a name.
Pay per trade uses the labourer's current trade.
"""
import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Callable, Dict, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.constants.choices import Gender, PaymentType, label_for
from app.core.database import utc_now
from app.core.exceptions import ForbiddenError
from app.models.labourer import Labourer
from app.models.payment import PaymentRecord
from app.models.project import Project
from app.models.user import User
from app.models.work import Work, WorkLabourer
from app.schemas.stats import (
    LabourStats,
    MonthStats,
    ProjectOption,
    ProjectStats,
    StatsBucket,
    StatsTotals,
    TopLabourer,
)
from app.services.access_service import get_project_or_404, is_project_member
from app.services.permission_service import role_has_permission
from app.services.project_service import list_projects_for_user
from app.services.report_service import end_of_day, start_of_day

NOT_GIVEN = "not_given"
AGE_GROUPS: List[Tuple[str, int, int]] = [
    ("18-24", 18, 24),
    ("25-34", 25, 34),
    ("35-44", 35, 44),
    ("45-54", 45, 54),
    ("55+", 55, 200),
]
TOP_LABOURERS = 10


@dataclass
class StatsFilters:
    """Filters picked on the Insights page. None means "all"."""

    project_id: Optional[uuid.UUID] = None
    trade: Optional[str] = None
    gender: Optional[str] = None
    age_group: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None


@dataclass
class Tally:
    """Running totals for one group of labourers."""

    labourer_ids: Set[uuid.UUID] = field(default_factory=set)
    days_worked: int = 0
    amount_paid: Decimal = Decimal("0")


def age_group_of(birth_year: Optional[int], year: int) -> str:
    """
    Return the age group of a labourer, e.g. ``25-34``.

    Args:
        birth_year (Optional[int]): Year of birth, or None when not given.
        year (int): The current year.

    Returns:
        str: Age group key, or ``not_given``.
    """
    if birth_year is None:
        return NOT_GIVEN
    age = year - birth_year
    for key, youngest, oldest in AGE_GROUPS:
        if youngest <= age <= oldest:
            return key
    return NOT_GIVEN


def gender_of(labourer: Labourer) -> str:
    """
    Return the gender key of a labourer.

    Args:
        labourer (Labourer): The labourer.

    Returns:
        str: ``male``, ``female`` or ``not_given``.
    """
    return labourer.gender or NOT_GIVEN


def matches(labourer: Labourer, filters: StatsFilters, year: int) -> bool:
    """
    True if the labourer fits the trade, gender and age group filters.

    Args:
        labourer (Labourer): The labourer.
        filters (StatsFilters): Filters picked on the Insights page.
        year (int): The current year.

    Returns:
        bool: True if the labourer should be counted.
    """
    if filters.trade and labourer.title != filters.trade:
        return False
    if filters.gender and gender_of(labourer) != filters.gender:
        return False
    if filters.age_group and age_group_of(labourer.birth_year, year) != filters.age_group:
        return False
    return True


def scope_projects(db: Session, user: User, see_all: bool) -> List[Project]:
    """
    Projects the user may get insights on.

    Args:
        db (Session): Database session.
        user (User): The logged in user performing the action.
        see_all (bool): True if the user has ``stats.view_all``.

    Returns:
        List[Project]: List of projects, newest first.
    """
    if see_all:
        return list(db.scalars(select(Project).order_by(Project.created_at.desc())).all())
    return list_projects_for_user(db, user, only_mine=True)


def selected_projects(
    db: Session, user: User, see_all: bool, projects: List[Project], project_id: Optional[uuid.UUID]
) -> List[Project]:
    """
    Narrow the projects down to the one picked in the filter, if any.

    Args:
        db (Session): Database session.
        user (User): The logged in user performing the action.
        see_all (bool): True if the user has ``stats.view_all``.
        projects (List[Project]): Projects the user may get insights on.
        project_id (Optional[uuid.UUID]): ID of the project picked in the filter.

    Returns:
        List[Project]: The projects to count.

    Raises:
        ForbiddenError: If the user is not part of the picked project.
    """
    if project_id is None:
        return projects
    project = get_project_or_404(db, project_id)
    if not see_all and not is_project_member(project, user):
        raise ForbiddenError("You are not part of this project")
    return [project]


def load_links(db: Session, project_ids: List[uuid.UUID], filters: StatsFilters) -> List[WorkLabourer]:
    """
    Labourers on works of the given projects, with the days they worked.

    The date filters use the date the work was created.

    Args:
        db (Session): Database session.
        project_ids (List[uuid.UUID]): IDs of the projects to count.
        filters (StatsFilters): Filters picked on the Insights page.

    Returns:
        List[WorkLabourer]: The labourer links of the works.
    """
    statement = (
        select(WorkLabourer)
        .join(Work, WorkLabourer.work_id == Work.id)
        .where(Work.project_id.in_(project_ids))
        .options(joinedload(WorkLabourer.labourer), joinedload(WorkLabourer.work))
    )
    if filters.date_from is not None:
        statement = statement.where(Work.created_at >= start_of_day(filters.date_from))
    if filters.date_to is not None:
        statement = statement.where(Work.created_at <= end_of_day(filters.date_to))
    return list(db.scalars(statement).unique().all())


def load_payments(db: Session, project_ids: List[uuid.UUID], filters: StatsFilters) -> List[PaymentRecord]:
    """
    Successful payments to labourers on the given projects.

    Args:
        db (Session): Database session.
        project_ids (List[uuid.UUID]): IDs of the projects to count.
        filters (StatsFilters): Filters picked on the Insights page.

    Returns:
        List[PaymentRecord]: The payment records.
    """
    statement = (
        select(PaymentRecord)
        .where(
            PaymentRecord.project_id.in_(project_ids),
            PaymentRecord.successful.is_(True),
            PaymentRecord.payment_type == PaymentType.LABOURER.value,
            PaymentRecord.labourer_id.is_not(None),
        )
        .options(joinedload(PaymentRecord.labourer))
    )
    if filters.date_from is not None:
        statement = statement.where(PaymentRecord.created_at >= start_of_day(filters.date_from))
    if filters.date_to is not None:
        statement = statement.where(PaymentRecord.created_at <= end_of_day(filters.date_to))
    return list(db.scalars(statement).unique().all())


def load_registered(
    db: Session, whole_platform: bool, project_ids: List[uuid.UUID], filters: StatsFilters
) -> List[Labourer]:
    """
    Labourers registered in the date range.

    On the whole platform this is every labourer record. Otherwise it is the
    labourers who appear on works of the given projects.

    Args:
        db (Session): Database session.
        whole_platform (bool): True to count every labourer record.
        project_ids (List[uuid.UUID]): IDs of the projects to count.
        filters (StatsFilters): Filters picked on the Insights page.

    Returns:
        List[Labourer]: The labourers.
    """
    statement = select(Labourer)
    if not whole_platform:
        linked = (
            select(WorkLabourer.labourer_id)
            .join(Work, WorkLabourer.work_id == Work.id)
            .where(Work.project_id.in_(project_ids))
        )
        statement = statement.where(Labourer.id.in_(linked))
    if filters.date_from is not None:
        statement = statement.where(Labourer.created_at >= start_of_day(filters.date_from))
    if filters.date_to is not None:
        statement = statement.where(Labourer.created_at <= end_of_day(filters.date_to))
    return list(db.scalars(statement).all())


def tally(
    links: List[WorkLabourer],
    payments: List[PaymentRecord],
    key: Callable[[Labourer, uuid.UUID], str],
) -> Dict[str, Tally]:
    """
    Add up labourers, days worked and pay per group.

    Args:
        links (List[WorkLabourer]): Labourers on works, with days worked.
        payments (List[PaymentRecord]): Successful labourer payments.
        key (Callable[[Labourer, uuid.UUID], str]): Gives the group of a labourer on a project.

    Returns:
        Dict[str, Tally]: Totals per group key.
    """
    tallies: Dict[str, Tally] = {}
    for link in links:
        group = tallies.setdefault(key(link.labourer, link.work.project_id), Tally())
        group.labourer_ids.add(link.labourer_id)
        group.days_worked += link.days_worked
    for record in payments:
        group = tallies.setdefault(key(record.labourer, record.project_id), Tally())
        group.labourer_ids.add(record.labourer_id)
        group.amount_paid += Decimal(record.amount_paid)
    return tallies


def bucket(key: str, label: str, totals: Optional[Tally]) -> StatsBucket:
    """
    Turn a tally into one chart bar.

    Args:
        key (str): Group key used by the filters, e.g. ``masonry``.
        label (str): Text shown on the bar, e.g. ``Masonry``.
        totals (Optional[Tally]): Totals of the group, or None when it is empty.

    Returns:
        StatsBucket: The chart bar.
    """
    if totals is None:
        totals = Tally()
    return StatsBucket(
        key=key,
        label=label,
        labourers=len(totals.labourer_ids),
        days_worked=totals.days_worked,
        amount_paid=totals.amount_paid,
    )


def trade_buckets(links: List[WorkLabourer], payments: List[PaymentRecord]) -> List[StatsBucket]:
    """
    One bar per trade, the trade with most labourers first.

    Args:
        links (List[WorkLabourer]): Labourers on works, with days worked.
        payments (List[PaymentRecord]): Successful labourer payments.

    Returns:
        List[StatsBucket]: The chart bars.
    """
    tallies = tally(links, payments, lambda labourer, project_id: labourer.title)
    buckets = []
    for key, totals in tallies.items():
        buckets.append(bucket(key, label_for(key), totals))
    buckets.sort(key=lambda item: (-item.labourers, -item.days_worked, item.label))
    return buckets


def gender_buckets(links: List[WorkLabourer], payments: List[PaymentRecord]) -> List[StatsBucket]:
    """
    One bar each for male, female and not given.

    Args:
        links (List[WorkLabourer]): Labourers on works, with days worked.
        payments (List[PaymentRecord]): Successful labourer payments.

    Returns:
        List[StatsBucket]: The chart bars.
    """
    tallies = tally(links, payments, lambda labourer, project_id: gender_of(labourer))
    buckets = []
    for gender in Gender:
        buckets.append(bucket(gender.value, label_for(gender.value), tallies.get(gender.value)))
    buckets.append(bucket(NOT_GIVEN, "Not given", tallies.get(NOT_GIVEN)))
    return buckets


def age_buckets(links: List[WorkLabourer], payments: List[PaymentRecord], year: int) -> List[StatsBucket]:
    """
    One bar per age group, youngest first, then not given.

    Args:
        links (List[WorkLabourer]): Labourers on works, with days worked.
        payments (List[PaymentRecord]): Successful labourer payments.
        year (int): The current year.

    Returns:
        List[StatsBucket]: The chart bars.
    """
    tallies = tally(
        links, payments, lambda labourer, project_id: age_group_of(labourer.birth_year, year)
    )
    buckets = []
    for key, youngest, oldest in AGE_GROUPS:
        buckets.append(bucket(key, key, tallies.get(key)))
    buckets.append(bucket(NOT_GIVEN, "Not given", tallies.get(NOT_GIVEN)))
    return buckets


def project_rows(
    projects: List[Project], links: List[WorkLabourer], payments: List[PaymentRecord]
) -> List[ProjectStats]:
    """
    One row per project with its labourers, days, pay and trades. Busiest first.

    Args:
        projects (List[Project]): Projects to count.
        links (List[WorkLabourer]): Labourers on works, with days worked.
        payments (List[PaymentRecord]): Successful labourer payments.

    Returns:
        List[ProjectStats]: The project rows.
    """
    rows = []
    for project in projects:
        project_links = [link for link in links if link.work.project_id == project.id]
        project_payments = [record for record in payments if record.project_id == project.id]
        totals = tally(project_links, project_payments, lambda labourer, project_id: "all")
        summary = bucket("all", project.name, totals.get("all"))
        rows.append(ProjectStats(
            id=project.id,
            name=project.name,
            location=project.location,
            labourers=summary.labourers,
            days_worked=summary.days_worked,
            amount_paid=summary.amount_paid,
            trades=trade_buckets(project_links, project_payments),
        ))
    rows.sort(key=lambda row: (-row.labourers, -row.days_worked, row.name))
    return rows


def month_rows(links: List[WorkLabourer], registered: List[Labourer]) -> List[MonthStats]:
    """
    Labourers registered and days worked per month, oldest month first.

    Args:
        links (List[WorkLabourer]): Labourers on works, with days worked.
        registered (List[Labourer]): Labourers registered in the date range.

    Returns:
        List[MonthStats]: One row per month.
    """
    worked: Dict[str, Tally] = {}
    for link in links:
        group = worked.setdefault(link.work.created_at.strftime("%Y-%m"), Tally())
        group.labourer_ids.add(link.labourer_id)
        group.days_worked += link.days_worked
    new: Dict[str, int] = {}
    for labourer in registered:
        month = labourer.created_at.strftime("%Y-%m")
        new[month] = new.get(month, 0) + 1
    rows = []
    for month in sorted(set(worked) | set(new)):
        totals = worked.get(month, Tally())
        rows.append(MonthStats(
            month=month,
            registered=new.get(month, 0),
            labourers=len(totals.labourer_ids),
            days_worked=totals.days_worked,
        ))
    return rows


def top_labourers(links: List[WorkLabourer], payments: List[PaymentRecord]) -> List[TopLabourer]:
    """
    Labourers who came back for the most works, with days worked and pay.

    Args:
        links (List[WorkLabourer]): Labourers on works, with days worked.
        payments (List[PaymentRecord]): Successful labourer payments.

    Returns:
        List[TopLabourer]: Up to ``TOP_LABOURERS`` labourers, most works first.
    """
    works: Dict[uuid.UUID, Set[uuid.UUID]] = {}
    projects: Dict[uuid.UUID, Set[uuid.UUID]] = {}
    days: Dict[uuid.UUID, int] = {}
    people: Dict[uuid.UUID, Labourer] = {}
    for link in links:
        people[link.labourer_id] = link.labourer
        works.setdefault(link.labourer_id, set()).add(link.work_id)
        projects.setdefault(link.labourer_id, set()).add(link.work.project_id)
        days[link.labourer_id] = days.get(link.labourer_id, 0) + link.days_worked
    paid: Dict[uuid.UUID, Decimal] = {}
    for record in payments:
        paid[record.labourer_id] = paid.get(record.labourer_id, Decimal("0")) + Decimal(record.amount_paid)
    rows = []
    for labourer_id, labourer in people.items():
        rows.append(TopLabourer(
            id=labourer_id,
            name=labourer.name,
            trade=label_for(labourer.title),
            works=len(works[labourer_id]),
            projects=len(projects[labourer_id]),
            days_worked=days[labourer_id],
            amount_paid=paid.get(labourer_id, Decimal("0")),
        ))
    rows.sort(key=lambda row: (-row.works, -row.days_worked, row.name))
    return rows[:TOP_LABOURERS]


def labour_stats(db: Session, user: User, filters: StatsFilters) -> LabourStats:
    """
    Build the labour insights for the projects the user may see.

    Args:
        db (Session): Database session.
        user (User): The logged in user performing the action.
        filters (StatsFilters): Filters picked on the Insights page.

    Returns:
        LabourStats: Totals, chart bars, months and top labourers.

    Raises:
        ForbiddenError: If the user is not part of the picked project.
    """
    # Work out which projects the user may count
    year = utc_now().year
    see_all = role_has_permission(db, user.role, "stats.view_all")
    projects = scope_projects(db, user, see_all)
    chosen = selected_projects(db, user, see_all, projects, filters.project_id)
    project_ids = [project.id for project in chosen]

    # Load the records and keep the labourers that fit the filters
    links = []
    for link in load_links(db, project_ids, filters):
        if matches(link.labourer, filters, year):
            links.append(link)
    payments = []
    for record in load_payments(db, project_ids, filters):
        if matches(record.labourer, filters, year):
            payments.append(record)
    registered = []
    whole_platform = see_all and filters.project_id is None
    for labourer in load_registered(db, whole_platform, project_ids, filters):
        if matches(labourer, filters, year):
            registered.append(labourer)

    # Add everything up
    overall = tally(links, payments, lambda labourer, project_id: "all").get("all", Tally())
    totals = StatsTotals(
        projects=len(chosen),
        registered=len(registered),
        labourers=len(overall.labourer_ids),
        days_worked=overall.days_worked,
        amount_paid=overall.amount_paid,
    )
    return LabourStats(
        scope="all" if see_all else "mine",
        projects=[ProjectOption(id=project.id, name=project.name) for project in projects],
        totals=totals,
        by_trade=trade_buckets(links, payments),
        by_project=project_rows(chosen, links, payments),
        by_gender=gender_buckets(links, payments),
        by_age_group=age_buckets(links, payments, year),
        by_month=month_rows(links, registered),
        top_labourers=top_labourers(links, payments),
    )
