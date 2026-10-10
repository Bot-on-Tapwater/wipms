"""Sending notification emails.

Emails are sent with FastAPI ``BackgroundTasks`` so requests are not slowed
down. When ``EMAIL_ENABLED`` is false (local development and tests) emails
are only written to the log.
"""
import logging
import smtplib
from email.message import EmailMessage
from typing import List, Optional, Tuple

from fastapi import BackgroundTasks

from app.core.config import settings
from app.core.templates import render_template

logger = logging.getLogger(__name__)

# (filename, content bytes, mime subtype) e.g. ("report.pdf", b"...", "pdf")
Attachment = Tuple[str, bytes, str]


def build_message(
    recipients: List[str],
    subject: str,
    html_body: str,
    attachments: Optional[List[Attachment]] = None,
) -> EmailMessage:
    """
    Build the email with a plain text fallback, the HTML body and any attachments.

    Args:
        recipients (List[str]): Email addresses to send to.
        subject (str): Email subject.
        html_body (str): Rendered HTML body.
        attachments (Optional[List[Attachment]]): Optional files to attach as (filename, bytes, mime subtype).

    Returns:
        EmailMessage: The email, ready to send.
    """
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.DEFAULT_FROM_EMAIL
    message["To"] = ", ".join(recipients)
    message.set_content("This email requires an HTML capable email client.")
    message.add_alternative(html_body, subtype="html")
    if attachments:
        for filename, content, subtype in attachments:
            message.add_attachment(
                content, maintype="application", subtype=subtype, filename=filename
            )
    return message


def send_email_now(
    recipients: List[str],
    subject: str,
    html_body: str,
    attachments: Optional[List[Attachment]] = None,
) -> None:
    """
    Send an email immediately using SMTP settings from the environment.

    Args:
        recipients (List[str]): Email addresses to send to.
        subject (str): Email subject.
        html_body (str): Rendered HTML body.
        attachments (Optional[List[Attachment]]): Optional files to attach as (filename, bytes, mime subtype).
    """
    clean_recipients = []
    for recipient in recipients:
        if recipient:
            clean_recipients.append(recipient)
    if not clean_recipients:
        return

    if not settings.EMAIL_ENABLED:
        logger.info("Email disabled. Would send '%s' to %s", subject, clean_recipients)
        return

    message = build_message(clean_recipients, subject, html_body, attachments)
    try:
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=30) as server:
            if settings.EMAIL_USE_TLS:
                server.starttls()
            if settings.EMAIL_HOST_USER:
                server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.send_message(message)
    except (smtplib.SMTPException, OSError):
        logger.exception("Failed to send email '%s'", subject)


def queue_email(
    background_tasks: BackgroundTasks,
    recipients: List[str],
    subject: str,
    template_name: str,
    context: dict,
    attachments: Optional[List[Attachment]] = None,
) -> None:
    """
    Render an email template and send it in the background.

    Args:
        background_tasks (BackgroundTasks): FastAPI background tasks used to send emails after the response.
        recipients (List[str]): Email addresses to send to.
        subject (str): Email subject.
        template_name (str): Template file name inside ``templates/email``.
        context (dict): Values available inside the template.
        attachments (Optional[List[Attachment]]): Optional files to attach as (filename, bytes, mime subtype).
    """
    html_body = render_template(f"email/{template_name}", context)
    background_tasks.add_task(send_email_now, recipients, subject, html_body, attachments)
