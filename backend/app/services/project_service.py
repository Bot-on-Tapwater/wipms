"""Business logic for projects, project teams and the project wallet."""
import uuid
from decimal import Decimal
from typing import List

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.constants.choices import WalletTransactionType
from app.constants.roles import Role
from app.core.exceptions import AppError, NotFoundError
from app.models.project import (
    Project,
    WalletTransaction,
    project_consultant_supervisors,
    project_contractor_supervisors,
    project_subcontractors,
)
from app.models.payment import PaymentRecord
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.permission_service import role_has_permission

# Which list on the project each team type uses, and which role users need.
TEAM_TYPES = {
    "contractor-supervisors": ("contractor_supervisors", Role.CONTRACTORS_SUPERVISOR.value),
    "consultant-supervisors": ("consultant_supervisors", Role.CONSULTANTS_SUPERVISOR.value),
    "subcontractors": ("subcontractors", Role.SUBCONTRACTOR.value),
}


def create_project(db: Session, data: ProjectCreate, user: User) -> Project:
    """
    Create a project owned by the given user (the main contractor).

    Args:
        db (Session): Database session.
        data (ProjectCreate): Validated request body.
        user (User): The logged in user performing the action.

    Returns:
        Project: The project.
    """
    project = Project(
        name=data.name,
        location=data.location,
        description=data.description,
        created_by_id=user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project: Project, data: ProjectUpdate) -> Project:
    """
    Update the editable fields of a project.

    Args:
        db (Session): Database session.
        project (Project): The project.
        data (ProjectUpdate): Validated request body.

    Returns:
        Project: The project.
    """
    if data.name is not None:
        project.name = data.name
    if data.location is not None:
        project.location = data.location
    if data.description is not None:
        project.description = data.description
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: Project) -> None:
    """
    Delete a project. Not allowed once any payment has been made on it.

    Args:
        db (Session): Database session.
        project (Project): The project.
    """
    has_payments = db.scalar(
        select(PaymentRecord.id).where(PaymentRecord.project_id == project.id).limit(1)
    )
    if has_payments is not None:
        raise AppError("Projects with payment records cannot be deleted")
    db.delete(project)
    db.commit()


def list_projects_for_user(db: Session, user: User, only_mine: bool = False) -> List[Project]:
    """
    Return the projects a user can see.

    Users with ``projects.view_all`` see everything unless ``only_mine`` is
    True. Everyone else sees projects they created, supervise or subcontract on.

    Args:
        db (Session): Database session.
        user (User): The logged in user performing the action.
        only_mine (bool): Only return projects the user is a member of, even if they can see all.

    Returns:
        List[Project]: List of projects.
    """
    statement = select(Project).order_by(Project.created_at.desc())
    if only_mine or not role_has_permission(db, user.role, "projects.view_all"):
        cs_ids = select(project_contractor_supervisors.c.project_id).where(
            project_contractor_supervisors.c.user_id == user.id
        )
        con_ids = select(project_consultant_supervisors.c.project_id).where(
            project_consultant_supervisors.c.user_id == user.id
        )
        sub_ids = select(project_subcontractors.c.project_id).where(
            project_subcontractors.c.user_id == user.id
        )
        statement = statement.where(
            or_(
                Project.created_by_id == user.id,
                Project.id.in_(cs_ids),
                Project.id.in_(con_ids),
                Project.id.in_(sub_ids),
            )
        )
    return list(db.scalars(statement).all())


def _get_team_list(project: Project, team: str) -> list:
    """
    Return the project's member list for a team type.

    Args:
        project (Project): The project.
        team (str): Team name: contractor-supervisors, consultant-supervisors or subcontractors.

    Returns:
        list: The project's member list for that team.
    """
    if team not in TEAM_TYPES:
        raise NotFoundError(f"Unknown team type '{team}'")
    attribute = TEAM_TYPES[team][0]
    return getattr(project, attribute)


def assign_team_members(
    db: Session, project: Project, team: str, user_ids: List[uuid.UUID]
) -> Project:
    """
    Add users to a project team. Each user must have the matching role.

    Args:
        db (Session): Database session.
        project (Project): The project.
        team (str): Team name: contractor-supervisors, consultant-supervisors or subcontractors.
        user_ids (List[uuid.UUID]): IDs of the users to add.

    Returns:
        Project: The project.
    """
    members = _get_team_list(project, team)
    required_role = TEAM_TYPES[team][1]
    for user_id in user_ids:
        member = db.get(User, user_id)
        if member is None or not member.is_active:
            raise NotFoundError(f"User {user_id} not found")
        if member.role != required_role:
            raise AppError(f"{member.full_name} is not a {required_role}")
        already_member = False
        for existing in members:
            if existing.id == member.id:
                already_member = True
        if not already_member:
            members.append(member)
    db.commit()
    db.refresh(project)
    return project


def unassign_team_member(db: Session, project: Project, team: str, user_id: uuid.UUID) -> Project:
    """
    Remove one user from a project team.

    Args:
        db (Session): Database session.
        project (Project): The project.
        team (str): Team name: contractor-supervisors, consultant-supervisors or subcontractors.
        user_id (uuid.UUID): ID of the user.

    Returns:
        Project: The project.
    """
    members = _get_team_list(project, team)
    for member in list(members):
        if member.id == user_id:
            members.remove(member)
            db.commit()
            db.refresh(project)
            return project
    raise NotFoundError("User is not assigned to this project in that role")


def lock_project(db: Session, project: Project) -> Project:
    """
    Reload the project with a row lock (PostgreSQL) before its wallet changes.

    Two payouts or deposits on the same project at the same moment would
    otherwise both read the old balance and one change would be lost.
    ``populate_existing`` makes sure the fresh balance replaces any copy
    already loaded in this session.

    Args:
        db (Session): Database session.
        project (Project): The project.

    Returns:
        Project: The project, locked until the transaction ends.
    """
    statement = (
        select(Project)
        .where(Project.id == project.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return db.scalars(statement).one()


def deposit_to_wallet(
    db: Session, project: Project, amount: Decimal, reference: str, user: User
) -> WalletTransaction:
    """
    Add funds to a project wallet (mocked: no real money moves).

    Args:
        db (Session): Database session.
        project (Project): The project.
        amount (Decimal): Amount in KES.
        reference (str): Free text reference for the transaction.
        user (User): The logged in user performing the action.

    Returns:
        WalletTransaction: The wallet transaction that was recorded.
    """
    project = lock_project(db, project)
    project.wallet_balance = Decimal(project.wallet_balance) + amount
    transaction = WalletTransaction(
        project_id=project.id,
        transaction_type=WalletTransactionType.DEPOSIT.value,
        amount=amount,
        balance_after=project.wallet_balance,
        reference=reference or "Manual deposit",
        created_by_id=user.id,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def debit_wallet(
    db: Session, project: Project, amount: Decimal, reference: str, user: User
) -> None:
    """
    Take a payout from the project wallet. Does not commit.

    Args:
        db (Session): Database session.
        project (Project): The project.
        amount (Decimal): Amount in KES.
        reference (str): Free text reference for the transaction.
        user (User): The logged in user whose approval triggered the payout.
    """
    project.wallet_balance = Decimal(project.wallet_balance) - amount
    db.add(
        WalletTransaction(
            project_id=project.id,
            transaction_type=WalletTransactionType.PAYOUT.value,
            amount=amount,
            balance_after=project.wallet_balance,
            reference=reference,
            created_by_id=user.id,
        )
    )


def list_wallet_transactions(db: Session, project: Project) -> List[WalletTransaction]:
    """
    Return a project's wallet history, newest first.

    Args:
        db (Session): Database session.
        project (Project): The project.

    Returns:
        List[WalletTransaction]: List of wallet transactions, newest first.
    """
    statement = (
        select(WalletTransaction)
        .where(WalletTransaction.project_id == project.id)
        .order_by(WalletTransaction.created_at.desc())
    )
    return list(db.scalars(statement).all())


def refresh_project_completion(project: Project) -> None:
    """
    A project is completed when it has works and all of them are completed.

    Args:
        project (Project): The project.
    """
    if not project.works:
        project.is_completed = False
        return
    completed = True
    for work in project.works:
        if not work.is_completed:
            completed = False
    project.is_completed = completed
