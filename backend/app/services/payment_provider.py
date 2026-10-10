"""Payment providers.

The platform is moving from M-Pesa (Daraja) to a bank API that is not
available yet, so payments are **mocked** for now.

To add the bank later:
1. Create a class ``BankPaymentProvider(PaymentProvider)`` implementing ``send``.
2. Return it from ``get_payment_provider`` when ``PAYMENT_PROVIDER=bank``.
Nothing else in the code base needs to change.
"""
import random
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict

from app.core.config import settings
from app.core.database import utc_now


@dataclass
class PaymentResult:
    """Outcome of sending one payment."""

    successful: bool
    reference: str
    message: str
    raw_response: Dict[str, Any] = field(default_factory=dict)


class PaymentProvider:
    """Interface every payment provider must implement."""

    name = "base"

    def send(self, phone_number: str, amount: Decimal, remarks: str) -> PaymentResult:
        """
        Send ``amount`` to ``phone_number``. Must never raise for a failed payment.

        Args:
            phone_number (str): Recipient phone number in the format 254XXXXXXXXX.
            amount (Decimal): Amount in KES.
            remarks (str): Short note sent with the payment.

        Returns:
            PaymentResult: Whether the payment succeeded, with the provider reference.
        """
        raise NotImplementedError


class MockPaymentProvider(PaymentProvider):
    """
    Fake provider: no money moves. Succeeds unless a failure is simulated.

    Set ``MOCK_PAYMENT_FAILURE_RATE`` (0 to 1) to simulate random failures,
    which is useful for testing the failed payments report and retries.
    """

    name = "mock"

    def send(self, phone_number: str, amount: Decimal, remarks: str) -> PaymentResult:
        """
        Pretend to send a payment and return a fake response.

        Args:
            phone_number (str): Recipient phone number in the format 254XXXXXXXXX.
            amount (Decimal): Amount in KES.
            remarks (str): Short note sent with the payment.

        Returns:
            PaymentResult: Whether the payment succeeded, with the provider reference.
        """
        reference = f"MOCK-{uuid.uuid4().hex[:16].upper()}"
        failed = random.random() < settings.MOCK_PAYMENT_FAILURE_RATE
        if amount <= 0:
            failed = True
        message = "Payment sent successfully (mock)"
        if failed:
            message = "Payment failed (simulated by mock provider)"
        raw_response = {
            "provider": self.name,
            "reference": reference,
            "phone_number": phone_number,
            "amount": str(amount),
            "remarks": remarks,
            "status": "FAILED" if failed else "SUCCESS",
            "timestamp": utc_now().isoformat(),
        }
        return PaymentResult(
            successful=not failed,
            reference=reference,
            message=message,
            raw_response=raw_response,
        )


def get_payment_provider() -> PaymentProvider:
    """
    Return the payment provider selected by the ``PAYMENT_PROVIDER`` setting.

    Returns:
        PaymentProvider: The configured payment provider.
    """
    if settings.PAYMENT_PROVIDER == "mock":
        return MockPaymentProvider()
    raise ValueError(f"Unknown PAYMENT_PROVIDER '{settings.PAYMENT_PROVIDER}'")
