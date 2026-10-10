"""Tests for building and sending emails."""
from email.message import EmailMessage
from typing import List

import pytest

from app.services import email_service


class FakeSMTP:
    """Stands in for ``smtplib.SMTP`` and keeps the messages it was asked to send."""

    sent: List[EmailMessage] = []

    def __init__(self, host: str, port: int, timeout: int) -> None:
        """
        Accept the same arguments as ``smtplib.SMTP``.

        Args:
            host (str): SMTP server address.
            port (int): SMTP server port.
            timeout (int): Connection timeout in seconds.
        """

    def __enter__(self) -> "FakeSMTP":
        """
        Start the ``with`` block.

        Returns:
            FakeSMTP: This fake server.
        """
        return self

    def __exit__(self, *args: object) -> None:
        """End the ``with`` block."""

    def starttls(self) -> None:
        """Pretend to switch the connection to TLS."""

    def login(self, user: str, password: str) -> None:
        """
        Pretend to log in to the SMTP server.

        Args:
            user (str): SMTP username.
            password (str): SMTP password.
        """

    def send_message(self, message: EmailMessage) -> None:
        """
        Keep the message so the test can check it.

        Args:
            message (EmailMessage): The email being sent.
        """
        FakeSMTP.sent.append(message)


def test_send_email_with_attachment(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Empty addresses are skipped and the HTML body and attachment are sent.

    Args:
        monkeypatch (pytest.MonkeyPatch): Pytest helper used to replace the SMTP server.
    """
    FakeSMTP.sent = []
    monkeypatch.setattr(email_service.settings, "EMAIL_ENABLED", True)
    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)

    email_service.send_email_now(
        ["owner@example.com", "", "cs@example.com"],
        "Payments Report",
        "<p>Report attached</p>",
        [("payments-report.pdf", b"%PDF-1.4 test", "pdf")],
    )

    assert len(FakeSMTP.sent) == 1
    message = FakeSMTP.sent[0]
    assert message["To"] == "owner@example.com, cs@example.com"
    assert message["Subject"] == "Payments Report"
    assert "<p>Report attached</p>" in message.get_body(preferencelist=("html",)).get_content()
    attachments = list(message.iter_attachments())
    assert [attachment.get_filename() for attachment in attachments] == ["payments-report.pdf"]
    assert attachments[0].get_content() == b"%PDF-1.4 test"


def test_disabled_email_is_not_sent(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    With ``EMAIL_ENABLED`` false nothing is sent to the SMTP server.

    Args:
        monkeypatch (pytest.MonkeyPatch): Pytest helper used to replace the SMTP server.
    """
    FakeSMTP.sent = []
    monkeypatch.setattr(email_service.settings, "EMAIL_ENABLED", False)
    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)

    email_service.send_email_now(["owner@example.com"], "Subject", "<p>Body</p>")

    assert FakeSMTP.sent == []
