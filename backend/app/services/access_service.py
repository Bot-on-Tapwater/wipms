"""Object level access rules: which projects and works a user may see.

Permissions (``require_permission``) answer *what* a user may do.
These helpers answer *on which* project or work they may do it.
"""
import uuid

from sqlalchemy.orm import Session

from app.constants.roles import Role
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.project import Project
from app.models.user import User
from app.models.work import Work
from app.services.permission_service import role_has_permission


def _contains_user(users: list, user: User) -> bool:
    """
    Return True if ``user`` is inside the list of users.

    Args:
        users (list): Users to search.
        user (User): The user to look for.

    Returns:
        bool: True if the user is in the list.
    """
    for member in users:
        if member.id == user.id:
            return True
    return False


def is_project_member(project: Project, user: User) -> bool:
    """
    True if the user created the project or is part of its team.

    Args:
        project (Project): The project.
        user (User): The user to check.

    Returns:
        bool: True if the user belongs to the project.
    """
    if project.created_by_id == user.id:
        return True
    if _contains_user(project.contractor_supervisors, user):
        return True
    if _contains_user(project.consultant_supervisors, user):
        return True
    return _contains_user(project.subcontractors, user)


def can_access_project(db: Session, project: Project, user: User) -> bool:
    """
    True if the user may see the project.

    Args:
        db (Session): Database session.
        project (Project): The project.
        user (User): The logged in user performing the action.

    Returns:
        bool: True if the user may see the project.
    """
    if role_has_permission(db, user.role, "projects.view_all"):
        return True
    return is_project_member(project, user)


def get_project_or_404(db: Session, project_id: uuid.UUID) -> Project:
    """
    Load a project or raise 404.

    Args:
        db (Session): Database session.
        project_id (uuid.UUID): ID of the project.

    Returns:
        Project: The project.
    """
    project = db.get(Project, project_id)
    if project is None:
        raise NotFoundError("Project not found")
    return project


def get_accessible_project(db: Session, project_id: uuid.UUID, user: User) -> Project:
    """
    Load a project the user is allowed to see, or raise 404/403.

    Args:
        db (Session): Database session.
        project_id (uuid.UUID): ID of the project.
        user (User): The logged in user performing the action.

    Returns:
        Project: The project.
    """
    project = get_project_or_404(db, project_id)
    if not can_access_project(db, project, user):
        raise ForbiddenError("You are not part of this project")
    return project


def can_access_work(db: Session, work: Work, user: User) -> bool:
    """
    True if the user may see the work.

    Rule from the old backend: a subcontractor only sees works assigned to them.

    Args:
        db (Session): Database session.
        work (Work): The work.
        user (User): The logged in user performing the action.

    Returns:
        bool: True if the user may see the work.
    """
    if not can_access_project(db, work.project, user):
        return False
    if user.role == Role.SUBCONTRACTOR.value:
        return work.assigned_subcontractor_id == user.id
    return True


def get_accessible_work(db: Session, work_id: uuid.UUID, user: User) -> Work:
    """
    Load a work the user is allowed to see, or raise 404/403.

    Args:
        db (Session): Database session.
        work_id (uuid.UUID): ID of the work.
        user (User): The logged in user performing the action.

    Returns:
        Work: The work.
    """
    work = db.get(Work, work_id)
    if work is None:
        raise NotFoundError("Work not found")
    if not can_access_work(db, work, user):
        raise ForbiddenError("You do not have access to this work")
    return work
