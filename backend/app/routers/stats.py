"""Labour insights endpoints.

Needs the ``stats.view`` permission. Users with ``stats.view_all`` see every
project; everyone else only sees projects they created or are on.
"""
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.constants.choices import LabourerTitle
from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.user import User
from app.schemas.stats import AgeGroupFilter, GenderFilter, LabourStats
from app.services import stats_service
from app.services.stats_service import StatsFilters

router = APIRouter(prefix="/stats", tags=["Insights"])


@router.get("/labourers", response_model=LabourStats)
def labour_stats(
    project_id: Optional[uuid.UUID] = None,
    trade: Optional[LabourerTitle] = None,
    gender: Optional[GenderFilter] = None,
    age_group: Optional[AgeGroupFilter] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    user: User = Depends(require_permission("stats.view")),
    db: Session = Depends(get_db),
) -> LabourStats:
    """
    Labourers by trade, project, gender and age group, with days worked and pay.

    Args:
        project_id (Optional[uuid.UUID]): Only count this project.
        trade (Optional[LabourerTitle]): Only count labourers of this trade.
        gender (Optional[GenderFilter]): Only count labourers of this gender, or ``not_given``.
        age_group (Optional[AgeGroupFilter]): Only count labourers in this age group, or ``not_given``.
        date_from (Optional[date]): Only count works, payments and sign-ups on or after this date.
        date_to (Optional[date]): Only count works, payments and sign-ups on or before this date.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        LabourStats: Totals, chart bars, months and top labourers.
    """
    filters = StatsFilters(
        project_id=project_id,
        trade=trade.value if trade is not None else None,
        gender=gender,
        age_group=age_group,
        date_from=date_from,
        date_to=date_to,
    )
    return stats_service.labour_stats(db, user, filters)
