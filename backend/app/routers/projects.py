"""Project endpoints: CRUD, team assignment and wallet."""
import uuid
from typing import List, Literal

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import check_permission, get_current_user, require_permission
from app.models.project import Project, WalletTransaction
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.project import (
    AssignUsers,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    WalletDeposit,
    WalletTransactionRead,
)
from app.services import project_service
from app.services.access_service import get_accessible_project

router = APIRouter(prefix="/projects", tags=["Projects"])

TeamType = Literal["contractor-supervisors", "consultant-supervisors", "subcontractors"]


def _assign_permission_for(team: str) -> str:
    """
    Return the permission code needed to change a project team.

    Args:
        team (str): Team name: contractor-supervisors, consultant-supervisors or subcontractors.

    Returns:
        str: The required permission code.
    """
    if team == "subcontractors":
        return "projects.assign_subcontractors"
    return "projects.assign_supervisors"


def _unassign_permission_for(team: str) -> str:
    """
    Return the permission code needed to remove someone from a team.

    Args:
        team (str): Team name: contractor-supervisors, consultant-supervisors or subcontractors.

    Returns:
        str: The required permission code.
    """
    if team == "subcontractors":
        return "projects.unassign_subcontractors"
    return "projects.assign_supervisors"


@router.get("", response_model=List[ProjectRead])
def list_projects(
    only_mine: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Project]:
    """
    List projects the user can see. ``only_mine=true`` limits to their own projects.

    Args:
        only_mine (bool): Only return projects the user is a member of, even if they can see all.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        List[Project]: List of projects.
    """
    return project_service.list_projects_for_user(db, user, only_mine)


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    data: ProjectCreate,
    user: User = Depends(require_permission("projects.create")),
    db: Session = Depends(get_db),
) -> Project:
    """
    Create a project. Requires ``projects.create``.

    Args:
        data (ProjectCreate): Validated request body.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        Project: The project.
    """
    return project_service.create_project(db, data, user)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Project:
    """
    Get one project the user is part of.

    Args:
        project_id (uuid.UUID): ID of the project.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        Project: The project.
    """
    return get_accessible_project(db, project_id, user)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    user: User = Depends(require_permission("projects.edit")),
    db: Session = Depends(get_db),
) -> Project:
    """
    Edit a project. Requires ``projects.edit``.

    Args:
        project_id (uuid.UUID): ID of the project.
        data (ProjectUpdate): Validated request body.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        Project: The project.
    """
    project = get_accessible_project(db, project_id, user)
    return project_service.update_project(db, project, data)


@router.delete("/{project_id}", response_model=MessageResponse)
def delete_project(
    project_id: uuid.UUID,
    user: User = Depends(require_permission("projects.delete")),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Delete a project with no payment records. Requires ``projects.delete``.

    Args:
        project_id (uuid.UUID): ID of the project.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        MessageResponse: A confirmation message.
    """
    project = get_accessible_project(db, project_id, user)
    project_service.delete_project(db, project)
    return MessageResponse(message="Project deleted successfully")


@router.post("/{project_id}/{team}", response_model=ProjectRead)
def assign_team_members(
    project_id: uuid.UUID,
    team: TeamType,
    data: AssignUsers,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Project:
    """
    Assign contractor supervisors, consultant supervisors or subcontractors.

    Requires ``projects.assign_supervisors`` (supervisors) or
    ``projects.assign_subcontractors`` (subcontractors).

    Args:
        project_id (uuid.UUID): ID of the project.
        team (TeamType): Team name: contractor-supervisors, consultant-supervisors or subcontractors.
        data (AssignUsers): Validated request body.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        Project: The project.
    """
    check_permission(db, user, _assign_permission_for(team))
    project = get_accessible_project(db, project_id, user)
    return project_service.assign_team_members(db, project, team, data.user_ids)


@router.delete("/{project_id}/{team}/{user_id}", response_model=ProjectRead)
def unassign_team_member(
    project_id: uuid.UUID,
    team: TeamType,
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Project:
    """
    Remove a user from a project team.

    Requires ``projects.assign_supervisors`` (supervisors) or
    ``projects.unassign_subcontractors`` (subcontractors).

    Args:
        project_id (uuid.UUID): ID of the project.
        team (TeamType): Team name: contractor-supervisors, consultant-supervisors or subcontractors.
        user_id (uuid.UUID): ID of the user.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        Project: The project.
    """
    check_permission(db, user, _unassign_permission_for(team))
    project = get_accessible_project(db, project_id, user)
    return project_service.unassign_team_member(db, project, team, user_id)


@router.post(
    "/{project_id}/wallet/deposits",
    response_model=WalletTransactionRead,
    status_code=status.HTTP_201_CREATED,
)
def deposit_to_wallet(
    project_id: uuid.UUID,
    data: WalletDeposit,
    user: User = Depends(require_permission("projects.fund_wallet")),
    db: Session = Depends(get_db),
) -> WalletTransaction:
    """
    Add funds to the project wallet (mocked). Requires ``projects.fund_wallet``.

    Args:
        project_id (uuid.UUID): ID of the project.
        data (WalletDeposit): Validated request body.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        WalletTransaction: The wallet transaction that was recorded.
    """
    project = get_accessible_project(db, project_id, user)
    return project_service.deposit_to_wallet(db, project, data.amount, data.reference, user)


@router.get("/{project_id}/wallet/transactions", response_model=List[WalletTransactionRead])
def list_wallet_transactions(
    project_id: uuid.UUID,
    user: User = Depends(require_permission("projects.view_wallet")),
    db: Session = Depends(get_db),
) -> List[WalletTransaction]:
    """
    List deposits and payouts of a project wallet. Requires ``projects.view_wallet``.

    Subcontractors do not have this by default: payouts of other
    subcontractors' works are listed here.

    Args:
        project_id (uuid.UUID): ID of the project.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        List[WalletTransaction]: List of wallet transactions, newest first.
    """
    project = get_accessible_project(db, project_id, user)
    return project_service.list_wallet_transactions(db, project)
