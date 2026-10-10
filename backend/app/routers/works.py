"""Work endpoints: CRUD, subcontractor, labourers, comments, approvals, images.

Payment related work endpoints live in ``routers/payments.py``.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import check_permission, get_current_user, require_permission
from app.models.user import User
from app.models.work import Work, WorkImage, WorkLabourer
from app.schemas.common import MessageResponse
from app.schemas.work import (
    ApprovalChange,
    AssignLabourer,
    AssignSubcontractor,
    CommentCreate,
    CreateAndAssignLabourer,
    UpdateDaysWorked,
    WorkCreate,
    WorkImageRead,
    WorkLabourerRead,
    WorkRead,
    WorkUpdate,
)
from app.services import labourer_service, work_service
from app.services.access_service import get_accessible_project, get_accessible_work

router = APIRouter(prefix="/works", tags=["Works"])


def _image_to_schema(image: WorkImage) -> WorkImageRead:
    """
    Build the image response including the URL to download the file.

    Args:
        image (WorkImage): The stored image.

    Returns:
        WorkImageRead: The image with its download URL.
    """
    result = WorkImageRead.model_validate(image)
    result.file_url = f"/api/v1/works/{image.work_id}/images/{image.id}/file"
    return result


@router.get("", response_model=List[WorkRead])
def list_project_works(
    project_id: Optional[uuid.UUID] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Work]:
    """
    List works in a project, or in every project the user can see when
    ``project_id`` is left out. Subcontractors only see works assigned to them.

    Args:
        project_id (Optional[uuid.UUID]): ID of the project, or None for all visible projects.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        List[Work]: List of works.
    """
    if project_id is None:
        return work_service.list_works_for_user(db, user)
    project = get_accessible_project(db, project_id, user)
    return work_service.list_project_works(db, project, user)


@router.post("", response_model=WorkRead, status_code=status.HTTP_201_CREATED)
def create_work(
    data: WorkCreate,
    user: User = Depends(require_permission("works.create")),
    db: Session = Depends(get_db),
) -> Work:
    """
    Create a work under a project. Requires ``works.create``.

    Args:
        data (WorkCreate): Validated request body.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        Work: The work.
    """
    project = get_accessible_project(db, data.project_id, user)
    return work_service.create_work(db, project, data, user)


@router.get("/{work_id}", response_model=WorkRead)
def get_work(
    work_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Work:
    """
    Get one work, including all approvals and payment state.

    Args:
        work_id (uuid.UUID): ID of the work.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        Work: The work.
    """
    return get_accessible_work(db, work_id, user)


@router.patch("/{work_id}", response_model=WorkRead)
def update_work(
    work_id: uuid.UUID,
    data: WorkUpdate,
    user: User = Depends(require_permission("works.edit")),
    db: Session = Depends(get_db),
) -> Work:
    """
    Edit a work (not allowed once paid). Changing cost resets cost approval.

    Args:
        work_id (uuid.UUID): ID of the work.
        data (WorkUpdate): Validated request body.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        Work: The work.
    """
    work = get_accessible_work(db, work_id, user)
    return work_service.update_work(db, work, data)


@router.delete("/{work_id}", response_model=MessageResponse)
def delete_work(
    work_id: uuid.UUID,
    user: User = Depends(require_permission("works.delete")),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Delete a work that has no payment request. Requires ``works.delete``.

    Args:
        work_id (uuid.UUID): ID of the work.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        MessageResponse: A confirmation message.
    """
    work = get_accessible_work(db, work_id, user)
    work_service.delete_work(db, work)
    return MessageResponse(message="Work deleted successfully")


@router.put("/{work_id}/subcontractor", response_model=WorkRead)
def assign_subcontractor(
    work_id: uuid.UUID,
    data: AssignSubcontractor,
    user: User = Depends(require_permission("works.assign_subcontractor")),
    db: Session = Depends(get_db),
) -> Work:
    """
    Assign a project subcontractor to the work.

    Args:
        work_id (uuid.UUID): ID of the work.
        data (AssignSubcontractor): Validated request body.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        Work: The work.
    """
    work = get_accessible_work(db, work_id, user)
    return work_service.assign_subcontractor(db, work, data.subcontractor_id)


@router.delete("/{work_id}/subcontractor", response_model=WorkRead)
def unassign_subcontractor(
    work_id: uuid.UUID,
    user: User = Depends(require_permission("works.assign_subcontractor")),
    db: Session = Depends(get_db),
) -> Work:
    """
    Remove the subcontractor from the work.

    Args:
        work_id (uuid.UUID): ID of the work.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        Work: The work.
    """
    work = get_accessible_work(db, work_id, user)
    return work_service.unassign_subcontractor(db, work)


# ---------- Labourers on a work ----------


@router.get("/{work_id}/labourers", response_model=List[WorkLabourerRead])
def list_work_labourers(
    work_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[WorkLabourer]:
    """
    List labourers on the work with days worked and amount due.

    Args:
        work_id (uuid.UUID): ID of the work.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        List[WorkLabourer]: Labourers on the work with days worked.
    """
    work = get_accessible_work(db, work_id, user)
    return work.labourer_links


@router.post(
    "/{work_id}/labourers", response_model=WorkLabourerRead, status_code=status.HTTP_201_CREATED
)
def assign_labourer(
    work_id: uuid.UUID,
    data: AssignLabourer,
    user: User = Depends(require_permission("works.manage_labourers")),
    db: Session = Depends(get_db),
) -> WorkLabourer:
    """
    Assign an existing labourer to the work (resets attendance approval).

    Args:
        work_id (uuid.UUID): ID of the work.
        data (AssignLabourer): Validated request body.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        WorkLabourer: The link between the work and the labourer.
    """
    work = get_accessible_work(db, work_id, user)
    labourer = labourer_service.get_labourer_or_404(db, data.labourer_id)
    return work_service.assign_labourer(db, work, labourer, data.days_worked)


@router.post(
    "/{work_id}/labourers/new",
    response_model=WorkLabourerRead,
    status_code=status.HTTP_201_CREATED,
)
def create_and_assign_labourer(
    work_id: uuid.UUID,
    data: CreateAndAssignLabourer,
    user: User = Depends(require_permission("works.manage_labourers")),
    db: Session = Depends(get_db),
) -> WorkLabourer:
    """
    Register a new labourer and assign them to the work in one step.

    Args:
        work_id (uuid.UUID): ID of the work.
        data (CreateAndAssignLabourer): Validated request body.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        WorkLabourer: The link between the work and the labourer.
    """
    check_permission(db, user, "labourers.create")
    work = get_accessible_work(db, work_id, user)
    return work_service.create_and_assign_labourer(db, work, data, user)


@router.patch("/{work_id}/labourers/{labourer_id}", response_model=WorkLabourerRead)
def update_days_worked(
    work_id: uuid.UUID,
    labourer_id: uuid.UUID,
    data: UpdateDaysWorked,
    user: User = Depends(require_permission("works.manage_labourers")),
    db: Session = Depends(get_db),
) -> WorkLabourer:
    """
    Change the days a labourer worked on this work (resets attendance approval).

    Args:
        work_id (uuid.UUID): ID of the work.
        labourer_id (uuid.UUID): ID of the labourer.
        data (UpdateDaysWorked): Validated request body.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        WorkLabourer: The link between the work and the labourer.
    """
    work = get_accessible_work(db, work_id, user)
    return work_service.update_days_worked(db, work, labourer_id, data.days_worked)


@router.delete("/{work_id}/labourers/{labourer_id}", response_model=MessageResponse)
def unassign_labourer(
    work_id: uuid.UUID,
    labourer_id: uuid.UUID,
    user: User = Depends(require_permission("works.manage_labourers")),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Remove a labourer from the work (resets attendance approval).

    Args:
        work_id (uuid.UUID): ID of the work.
        labourer_id (uuid.UUID): ID of the labourer.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        MessageResponse: A confirmation message.
    """
    work = get_accessible_work(db, work_id, user)
    work_service.unassign_labourer(db, work, labourer_id)
    return MessageResponse(message="Labourer removed from work")


# ---------- Comments and approvals ----------


@router.post("/{work_id}/comments/contractor-supervisor", response_model=WorkRead)
def add_contractor_supervisor_comment(
    work_id: uuid.UUID,
    data: CommentCreate,
    user: User = Depends(require_permission("works.comment_as_contractor_supervisor")),
    db: Session = Depends(get_db),
) -> Work:
    """
    Set the contractor supervisor's comment on the work.

    Args:
        work_id (uuid.UUID): ID of the work.
        data (CommentCreate): Validated request body.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        Work: The work.
    """
    work = get_accessible_work(db, work_id, user)
    return work_service.add_comment(db, work, data.comment, as_consultant=False)


@router.post("/{work_id}/comments/consultant-supervisor", response_model=WorkRead)
def add_consultant_supervisor_comment(
    work_id: uuid.UUID,
    data: CommentCreate,
    user: User = Depends(require_permission("works.comment_as_consultant_supervisor")),
    db: Session = Depends(get_db),
) -> Work:
    """
    Set the consultant supervisor's comment on the work.

    Args:
        work_id (uuid.UUID): ID of the work.
        data (CommentCreate): Validated request body.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        Work: The work.
    """
    work = get_accessible_work(db, work_id, user)
    return work_service.add_comment(db, work, data.comment, as_consultant=True)


@router.post("/{work_id}/approvals", response_model=WorkRead)
def set_approval(
    work_id: uuid.UUID,
    data: ApprovalChange,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Work:
    """
    Approve (``approved: true``) or disapprove a work.

    ``approval_type`` and the permission each one needs:

    * ``consultant`` â€“ ``works.approve_as_consultant``
    * ``contractor_supervisor`` â€“ ``works.approve_as_contractor_supervisor``
    * ``attendance`` â€“ ``works.approve_attendance``
    * ``cost`` â€“ ``works.approve_cost``

    Args:
        work_id (uuid.UUID): ID of the work.
        data (ApprovalChange): Validated request body.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        Work: The work.
    """
    check_permission(db, user, work_service.APPROVALS[data.approval_type][1])
    work = get_accessible_work(db, work_id, user)
    return work_service.set_approval(db, work, data.approval_type, data.approved)


# ---------- Proof of work images ----------


@router.get("/{work_id}/images", response_model=List[WorkImageRead])
def list_images(
    work_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[WorkImageRead]:
    """
    List proof-of-work images of the work.

    Args:
        work_id (uuid.UUID): ID of the work.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        List[WorkImageRead]: List of images with download URLs.
    """
    work = get_accessible_work(db, work_id, user)
    images = []
    for image in work.images:
        images.append(_image_to_schema(image))
    return images


@router.post("/{work_id}/images", response_model=WorkImageRead, status_code=status.HTTP_201_CREATED)
def upload_image(
    work_id: uuid.UUID,
    file: UploadFile = File(...),
    description: str = Form(default="", max_length=255),
    user: User = Depends(require_permission("works.upload_images")),
    db: Session = Depends(get_db),
) -> WorkImageRead:
    """
    Upload a proof-of-work image (JPEG, PNG or WEBP).

    Args:
        work_id (uuid.UUID): ID of the work.
        file (UploadFile): Uploaded image file.
        description (str): Short description.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        WorkImageRead: The image with its download URL.
    """
    work = get_accessible_work(db, work_id, user)
    image = work_service.save_image(db, work, file, description, user)
    return _image_to_schema(image)


@router.get("/{work_id}/images/{image_id}/file", response_class=FileResponse)
def download_image(
    work_id: uuid.UUID,
    image_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    """
    Download an image file. Only people with access to the work can see it.

    Args:
        work_id (uuid.UUID): ID of the work.
        image_id (uuid.UUID): ID of the image.
        user (User): The logged in user performing the action.
        db (Session): Database session.

    Returns:
        FileResponse: The image file.
    """
    work = get_accessible_work(db, work_id, user)
    return FileResponse(work_service.get_image_path(work, image_id))
