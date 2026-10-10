"""Email notifications sent during the work and payment flow."""
from typing import List

from fastapi import BackgroundTasks

from app.core.config import settings
from app.models.user import User
from app.models.work import Work
from app.services.email_service import queue_email


def work_url(work: Work) -> str:
    """
    Link to the work's page on the frontend.

    Args:
        work (Work): The work.

    Returns:
        str: The work's frontend URL.
    """
    return f"{settings.FRONTEND_URL}/projects/{work.project_id}/works/{work.id}"


def notify_users(
    background_tasks: BackgroundTasks,
    users: List[User],
    subject: str,
    message: str,
    work: Work,
) -> None:
    """
    Send the same notification email to each user (one email per person).

    Args:
        background_tasks (BackgroundTasks): FastAPI background tasks used to send emails after the response.
        users (List[User]): Users to notify.
        subject (str): Email subject.
        message (str): Text of the message.
        work (Work): The work.
    """
    for user in users:
        if user is None or not user.email:
            continue
        queue_email(
            background_tasks,
            [user.email],
            subject,
            "notification.html",
            {
                "recipient_name": user.first_name,
                "message": message,
                "work": work,
                "work_url": work_url(work),
            },
        )


def main_contractor_of(work: Work) -> List[User]:
    """
    Return the main contractor (project creator) as a list.

    Args:
        work (Work): The work.

    Returns:
        List[User]: List of users.
    """
    if work.project.created_by is None:
        return []
    return [work.project.created_by]


def contractor_supervisors_of(work: Work) -> List[User]:
    """
    Return the contractor supervisors of the work's project.

    Args:
        work (Work): The work.

    Returns:
        List[User]: List of users.
    """
    return list(work.project.contractor_supervisors)


def subcontractor_of(work: Work) -> List[User]:
    """
    Return the assigned subcontractor as a list (may be empty).

    Args:
        work (Work): The work.

    Returns:
        List[User]: List of users.
    """
    if work.assigned_subcontractor is None:
        return []
    return [work.assigned_subcontractor]
