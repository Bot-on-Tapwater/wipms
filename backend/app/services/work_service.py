"""Business logic for works: CRUD, labourers, comments, approvals and images."""
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.choices import PaymentStatus
from app.constants.roles import Role
from app.core.config import settings
from app.core.exceptions import AppError, NotFoundError
from app.models.labourer import Labourer
from app.models.project import Project
from app.models.user import User
from app.models.work import Work, WorkImage, WorkLabourer
from app.schemas.work import CreateAndAssignLabourer, WorkCreate, WorkUpdate
from app.services import labourer_service
from app.services.project_service import list_projects_for_user, refresh_project_completion

# approval type -> (Work attribute, permission code)
APPROVALS: Dict[str, Tuple[str, str]] = {
    "consultant": ("consultant_approval", "works.approve_as_consultant"),
    "contractor_supervisor": (
        "contractor_supervisor_approval",
        "works.approve_as_contractor_supervisor",
    ),
    "attendance": ("attendance_approval", "works.approve_attendance"),
    "cost": ("cost_approval", "works.approve_cost"),
}

ALLOWED_IMAGE_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def ensure_not_paid(work: Work) -> None:
    """
    Block changes once payouts have started, so records stay consistent.

    A work is locked when it is fully paid, and also when it was paid with
    some failed payments (status ``approved``): those are retried with the
    original amounts.

    Args:
        work (Work): The work.

    Raises:
        AppError(400): if payments for the work have already been sent.
    """
    if work.payment_status != PaymentStatus.PENDING.value:
        raise AppError("Payment for this work has already been processed; it can no longer be changed")


def _check_subcontractor_on_project(db: Session, project: Project, user_id: uuid.UUID) -> User:
    """
    Return the user if they are a subcontractor assigned to the project.

    Args:
        db (Session): Database session.
        project (Project): The project.
        user_id (uuid.UUID): ID of the subcontractor.

    Returns:
        User: The user.
    """
    subcontractor = db.get(User, user_id)
    if subcontractor is None or subcontractor.role != Role.SUBCONTRACTOR.value:
        raise AppError("Selected user is not a subcontractor")
    found = False
    for member in project.subcontractors:
        if member.id == subcontractor.id:
            found = True
    if not found:
        raise AppError("Subcontractor must first be assigned to the project")
    return subcontractor


def create_work(db: Session, project: Project, data: WorkCreate, user: User) -> Work:
    """
    Create a work under a project.

    If a subcontractor creates the work they become its assigned
    subcontractor (old behaviour). Others may pick a project subcontractor.

    Args:
        db (Session): Database session.
        project (Project): The project.
        data (WorkCreate): Validated request body.
        user (User): The logged in user performing the action.

    Returns:
        Work: The work.
    """
    assigned_id: Optional[uuid.UUID] = None
    # A subcontractor creating a work is assigned to it
    if user.role == Role.SUBCONTRACTOR.value:
        assigned_id = user.id
    elif data.assigned_subcontractor_id is not None:
        assigned_id = _check_subcontractor_on_project(
            db, project, data.assigned_subcontractor_id
        ).id
    work = Work(
        project_id=project.id,
        title=data.title,
        description=data.description,
        category=data.category.value,
        cost_labor=data.cost_labor,
        cost_overhead=data.cost_overhead,
        assigned_subcontractor_id=assigned_id,
        created_by_id=user.id,
    )
    # Save the work and update the project's completed status
    db.add(work)
    db.flush()
    db.refresh(project)
    refresh_project_completion(project)
    db.commit()
    db.refresh(work)
    return work


def update_work(db: Session, work: Work, data: WorkUpdate) -> Work:
    """
    Edit a work. Changing the cost resets the main contractor's cost approval.

    Args:
        db (Session): Database session.
        work (Work): The work.
        data (WorkUpdate): Validated request body.

    Returns:
        Work: The work.
    """
    ensure_not_paid(work)
    if data.title is not None:
        work.title = data.title
    if data.description is not None:
        work.description = data.description
    if data.category is not None:
        work.category = data.category.value
    cost_changed = False
    if data.cost_labor is not None and data.cost_labor != work.cost_labor:
        work.cost_labor = data.cost_labor
        cost_changed = True
    if data.cost_overhead is not None and data.cost_overhead != work.cost_overhead:
        work.cost_overhead = data.cost_overhead
        cost_changed = True
    if cost_changed:
        work.cost_approval = False
        work.reset_payment_request()
    db.commit()
    db.refresh(work)
    return work


def delete_work(db: Session, work: Work) -> None:
    """
    Delete a work that has not been paid or requested for payment.

    Args:
        db (Session): Database session.
        work (Work): The work.
    """
    ensure_not_paid(work)
    if work.payment_requested:
        raise AppError("Cannot delete a work after payment has been requested")
    project = work.project
    db.delete(work)
    db.flush()
    db.refresh(project)
    refresh_project_completion(project)
    db.commit()


def list_project_works(db: Session, project: Project, user: User) -> List[Work]:
    """
    List works in a project. Subcontractors only see works assigned to them.

    Args:
        db (Session): Database session.
        project (Project): The project.
        user (User): The logged in user performing the action.

    Returns:
        List[Work]: List of works.
    """
    statement = select(Work).where(Work.project_id == project.id).order_by(Work.created_at)
    if user.role == Role.SUBCONTRACTOR.value:
        statement = statement.where(Work.assigned_subcontractor_id == user.id)
    return list(db.scalars(statement).all())


def list_works_for_user(db: Session, user: User) -> List[Work]:
    """
    List works in every project the user can see, newest first.

    Subcontractors only see works assigned to them.

    Args:
        db (Session): Database session.
        user (User): The logged in user performing the action.

    Returns:
        List[Work]: List of works.
    """
    project_ids = []
    for project in list_projects_for_user(db, user):
        project_ids.append(project.id)
    statement = select(Work).where(Work.project_id.in_(project_ids)).order_by(Work.created_at.desc())
    if user.role == Role.SUBCONTRACTOR.value:
        statement = statement.where(Work.assigned_subcontractor_id == user.id)
    return list(db.scalars(statement).all())


def assign_subcontractor(db: Session, work: Work, subcontractor_id: uuid.UUID) -> Work:
    """
    Assign a project subcontractor to the work.

    Args:
        db (Session): Database session.
        work (Work): The work.
        subcontractor_id (uuid.UUID): ID of the subcontractor.

    Returns:
        Work: The work.
    """
    ensure_not_paid(work)
    _check_subcontractor_on_project(db, work.project, subcontractor_id)
    if work.assigned_subcontractor_id != subcontractor_id:
        work.assigned_subcontractor_id = subcontractor_id
        work.reset_payment_request()
    db.commit()
    db.refresh(work)
    return work


def unassign_subcontractor(db: Session, work: Work) -> Work:
    """
    Remove the assigned subcontractor from the work.

    Args:
        db (Session): Database session.
        work (Work): The work.

    Returns:
        Work: The work.
    """
    ensure_not_paid(work)
    if work.assigned_subcontractor_id is not None:
        work.assigned_subcontractor_id = None
        work.reset_payment_request()
    db.commit()
    db.refresh(work)
    return work


def _find_link(work: Work, labourer_id: uuid.UUID) -> Optional[WorkLabourer]:
    """
    Return the work-labourer link for a labourer, if any.

    Args:
        work (Work): The work.
        labourer_id (uuid.UUID): ID of the labourer.

    Returns:
        Optional[WorkLabourer]: The link, or None if the labourer is not on the work.
    """
    for link in work.labourer_links:
        if link.labourer_id == labourer_id:
            return link
    return None


def assign_labourer(db: Session, work: Work, labourer: Labourer, days_worked: int) -> WorkLabourer:
    """
    Assign a labourer to a work. Changing attendance resets attendance approval.

    Args:
        db (Session): Database session.
        work (Work): The work.
        labourer (Labourer): The labourer.
        days_worked (int): Number of days the labourer worked on the work.

    Returns:
        WorkLabourer: The link between the work and the labourer.
    """
    ensure_not_paid(work)
    if _find_link(work, labourer.id) is not None:
        raise AppError("Labourer is already assigned to this work")
    link = WorkLabourer(work_id=work.id, labourer_id=labourer.id, days_worked=days_worked)
    db.add(link)
    work.attendance_approval = False
    work.reset_payment_request()
    db.commit()
    db.refresh(link)
    return link


def create_and_assign_labourer(
    db: Session, work: Work, data: CreateAndAssignLabourer, user: User
) -> WorkLabourer:
    """
    Register a new labourer and assign them to the work in one step.

    Args:
        db (Session): Database session.
        work (Work): The work.
        data (CreateAndAssignLabourer): Validated request body.
        user (User): The logged in user performing the action.

    Returns:
        WorkLabourer: The link between the work and the labourer.
    """
    ensure_not_paid(work)
    labourer = labourer_service.create_labourer(db, data, user)
    return assign_labourer(db, work, labourer, data.days_worked)


def update_days_worked(db: Session, work: Work, labourer_id: uuid.UUID, days: int) -> WorkLabourer:
    """
    Change how many days a labourer worked. Resets attendance approval.

    Args:
        db (Session): Database session.
        work (Work): The work.
        labourer_id (uuid.UUID): ID of the labourer.
        days (int): Days worked.

    Returns:
        WorkLabourer: The link between the work and the labourer.
    """
    ensure_not_paid(work)
    link = _find_link(work, labourer_id)
    if link is None:
        raise NotFoundError("Labourer is not assigned to this work")
    if link.days_worked != days:
        link.days_worked = days
        work.attendance_approval = False
        work.reset_payment_request()
    db.commit()
    db.refresh(link)
    return link


def unassign_labourer(db: Session, work: Work, labourer_id: uuid.UUID) -> None:
    """
    Remove a labourer from a work. Resets attendance approval.

    Args:
        db (Session): Database session.
        work (Work): The work.
        labourer_id (uuid.UUID): ID of the labourer.
    """
    ensure_not_paid(work)
    link = _find_link(work, labourer_id)
    if link is None:
        raise NotFoundError("Labourer is not assigned to this work")
    db.delete(link)
    work.attendance_approval = False
    work.reset_payment_request()
    db.commit()


def add_comment(db: Session, work: Work, comment: str, as_consultant: bool) -> Work:
    """
    Set the contractor supervisor's or consultant supervisor's comment.

    Args:
        db (Session): Database session.
        work (Work): The work.
        comment (str): Comment text.
        as_consultant (bool): True to save the consultant supervisor comment, False for the
            contractor supervisor one.

    Returns:
        Work: The work.
    """
    if as_consultant:
        work.consultant_supervisor_comments = comment
    else:
        work.contractor_supervisor_comments = comment
    db.commit()
    db.refresh(work)
    return work


def set_approval(db: Session, work: Work, approval_type: str, approved: bool) -> Work:
    """
    Approve or disapprove a work for one approval type.

    Args:
        db (Session): Database session.
        work (Work): The work.
        approval_type (str): Which approval to give.
        approved (bool): True to approve, False to remove the approval.

    Returns:
        Work: The work.
    """
    ensure_not_paid(work)
    attribute = APPROVALS[approval_type][0]
    setattr(work, attribute, approved)
    db.commit()
    db.refresh(work)
    return work


def save_image(db: Session, work: Work, upload: UploadFile, description: str, user: User) -> WorkImage:
    """
    Store an uploaded proof-of-work image on disk and in the database.

    Args:
        db (Session): Database session.
        work (Work): The work.
        upload (UploadFile): Uploaded image file.
        description (str): Short description.
        user (User): The logged in user performing the action.

    Returns:
        WorkImage: The saved image record.
    """
    # Check if the file type and size are allowed
    extension = ALLOWED_IMAGE_TYPES.get(upload.content_type or "")
    if extension is None:
        raise AppError("Only JPEG, PNG and WEBP images are allowed")
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = upload.file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise AppError(f"Image is larger than {settings.MAX_UPLOAD_SIZE_MB} MB")
    if not content:
        raise AppError("Uploaded file is empty")

    # Save the file under MEDIA_DIR/works/<work id>/
    image_id = uuid.uuid4()
    relative_path = Path("works") / str(work.id) / f"{image_id}.{extension}"
    full_path = Path(settings.MEDIA_DIR) / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(content)

    image = WorkImage(
        id=image_id,
        work_id=work.id,
        file_path=relative_path.as_posix(),
        description=description,
        created_by_id=user.id,
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


def get_image_path(work: Work, image_id: uuid.UUID) -> Path:
    """
    Return the file path on disk of one of the work's images.

    Args:
        work (Work): The work.
        image_id (uuid.UUID): ID of the image.

    Returns:
        Path: Path of the image file.
    """
    for image in work.images:
        if image.id == image_id:
            path = Path(settings.MEDIA_DIR) / image.file_path
            if not path.is_file():
                raise NotFoundError("Image file is missing")
            return path
    raise NotFoundError("Image not found")
