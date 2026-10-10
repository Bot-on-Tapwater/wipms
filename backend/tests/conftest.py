"""Shared test fixtures.

Tests use an in-memory SQLite database (PostgreSQL is used in Docker), the
mock payment provider and disabled email.
"""
import os
import tempfile
import uuid
from decimal import Decimal
from typing import Dict, Generator, Set

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["EMAIL_ENABLED"] = "false"
os.environ["MOCK_PAYMENT_FAILURE_RATE"] = "0"
os.environ["MAIN_CONTRACTOR_EMAILS"] = "owner@example.com"
os.environ["MEDIA_DIR"] = tempfile.mkdtemp(prefix="ijenga-test-media-")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from httpx import Response  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402,F401
from app.constants.roles import Role  # noqa: E402
from app.core import security  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import payment_service  # noqa: E402
from app.services.payment_provider import MockPaymentProvider, PaymentResult  # noqa: E402
from app.services.permission_service import seed_permissions  # noqa: E402

PASSWORD = "Password123"
API = "/api/v1"
PHONE_A = "254701000001"
PHONE_B = "254701000002"

engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def override_get_db() -> Generator[Session, None, None]:
    """
    Use the test database inside the API.

    Yields:
        Session: A session on the test database.
    """
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Fewer bcrypt rounds keep the tests fast (production uses the default).
security.pwd_context.update(bcrypt__rounds=4)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    """
    A fresh database with permissions seeded, for every test.

    Yields:
        Session: A session on a fresh in-memory test database.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    seed_permissions(session)
    yield session
    session.close()


@pytest.fixture()
def client(db: Session) -> TestClient:
    """
    HTTP client for the app.

    Args:
        db (Session): Database session.

    Returns:
        TestClient: The test client.
    """
    return TestClient(app)


def create_user(db: Session, role: Role, email: str, phone: str = "254700000000") -> User:
    """
    Insert a user directly (bypasses registration rules).

    Args:
        db (Session): Database session.
        role (Role): Role value, e.g. ``subcontractor``.
        email (str): Email address.
        phone (str): Phone number in the format 254XXXXXXXXX.

    Returns:
        User: The user.
    """
    first_name = email.split("@")[0].capitalize()
    user = User(
        first_name=first_name,
        last_name="Test",
        email=email,
        phone_number=phone,
        role=role.value,
        hashed_password=hash_password(PASSWORD),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_headers(client: TestClient, email: str) -> Dict[str, str]:
    """
    Log in and return the Authorization header.

    Args:
        client (TestClient): Test HTTP client.
        email (str): Email address.

    Returns:
        Dict[str, str]: Authorization header for the user.
    """
    response = client.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


class Team:
    """A project with one user per role, each with login headers."""

    def __init__(self, client: TestClient, db: Session) -> None:
        """
        Create the users, the project, assign the team and fund the wallet.

        Args:
            client (TestClient): Test HTTP client.
            db (Session): Database session.
        """
        self.client = client
        self.db = db
        self.mc = create_user(db, Role.MAIN_CONTRACTOR, "owner@example.com", "254711111111")
        self.cs = create_user(db, Role.CONTRACTORS_SUPERVISOR, "cs@example.com", "254722222222")
        self.con = create_user(
            db, Role.CONSULTANTS_SUPERVISOR, "consultant@example.com", "254733333333"
        )
        self.sub = create_user(db, Role.SUBCONTRACTOR, "sub@example.com", "254744444444")
        self.outsider = create_user(
            db, Role.SUBCONTRACTOR, "outsider@example.com", "254755555555"
        )
        self.mc_h = auth_headers(client, self.mc.email)
        self.cs_h = auth_headers(client, self.cs.email)
        self.con_h = auth_headers(client, self.con.email)
        self.sub_h = auth_headers(client, self.sub.email)
        self.outsider_h = auth_headers(client, self.outsider.email)

        response = client.post(
            f"{API}/projects",
            json={"name": "Riverside Apartments", "location": "Nairobi"},
            headers=self.mc_h,
        )
        assert response.status_code == 201, response.text
        self.project_id = response.json()["id"]
        self.assign("contractor-supervisors", self.cs)
        self.assign("consultant-supervisors", self.con)
        self.assign("subcontractors", self.sub)

    def assign(self, team: str, user: User) -> None:
        """
        Add a user to one of the project teams.

        Args:
            team (str): Team name: contractor-supervisors, consultant-supervisors or subcontractors.
            user (User): The logged in user performing the action.
        """
        response = self.client.post(
            f"{API}/projects/{self.project_id}/{team}",
            json={"user_ids": [str(user.id)]},
            headers=self.mc_h,
        )
        assert response.status_code == 200, response.text

    def deposit(self, amount: str) -> None:
        """
        Add money to the project wallet.

        Args:
            amount (str): Amount in KES.
        """
        response = self.client.post(
            f"{API}/projects/{self.project_id}/wallet/deposits",
            json={"amount": amount, "reference": "test deposit"},
            headers=self.mc_h,
        )
        assert response.status_code == 201, response.text

    def create_work(self, cost_labor: str = "10000", cost_overhead: str = "0") -> str:
        """
        Create a work as the subcontractor (auto assigned) and return its id.

        Args:
            cost_labor (str): Labour cost estimate in KES.
            cost_overhead (str): Overhead cost in KES.

        Returns:
            str: ID of the new work.
        """
        response = self.client.post(
            f"{API}/works",
            json={
                "project_id": self.project_id,
                "title": "Ground floor walling",
                "category": "bricklaying",
                "cost_labor": cost_labor,
                "cost_overhead": cost_overhead,
            },
            headers=self.sub_h,
        )
        assert response.status_code == 201, response.text
        return response.json()["id"]

    def add_labourer(
        self, work_id: str, national_id: str, phone: str, daily_rate: str, days: int
    ) -> str:
        """
        Register a new labourer straight onto a work and return the labourer id.

        Args:
            work_id (str): ID of the work.
            national_id (str): National ID number of the new labourer.
            phone (str): Phone number in the format 254XXXXXXXXX.
            daily_rate (str): Daily rate in KES.
            days (int): Days worked.

        Returns:
            str: ID of the new labourer.
        """
        response = self.client.post(
            f"{API}/works/{work_id}/labourers/new",
            json={
                "name": f"Labourer {national_id}",
                "title": "carpenters",
                "national_id_number": national_id,
                "phone_number": phone,
                "daily_rate": daily_rate,
                "days_worked": days,
            },
            headers=self.sub_h,
        )
        assert response.status_code == 201, response.text
        return response.json()["labourer"]["id"]

    def ready_work(self) -> str:
        """
        Create the standard payment test work and give every work approval.

        Labour estimate 10,000, no overhead, 10% retention (1,000).
        Labourer A: 1,000 x 3 days = 3,000. Labourer B: 500 x 4 days = 2,000.
        The subcontractor is paid 10,000 - 5,000 - 1,000 = 4,000.

        Returns:
            str: ID of the work.
        """
        work_id = self.create_work(cost_labor="10000")
        self.add_labourer(work_id, "11111111", PHONE_A, "1000", 3)
        self.add_labourer(work_id, "22222222", PHONE_B, "500", 4)
        self.approve_all(work_id)
        return work_id

    def approve_all(self, work_id: str) -> None:
        """
        Give every work approval needed before payment.

        Args:
            work_id (str): ID of the work.
        """
        approvals = [
            ("consultant", self.con_h),
            ("contractor_supervisor", self.cs_h),
            ("attendance", self.cs_h),
            ("cost", self.mc_h),
        ]
        for approval_type, headers in approvals:
            response = self.client.post(
                f"{API}/works/{work_id}/approvals",
                json={"approval_type": approval_type, "approved": True},
                headers=headers,
            )
            assert response.status_code == 200, response.text

    def request_and_approve_payment(self, work_id: str) -> Response:
        """
        Request payment and give both payment approvals. Returns the last response.

        Args:
            work_id (str): ID of the work.

        Returns:
            Response: The last approval response.
        """
        response = self.client.post(f"{API}/works/{work_id}/payment-request", headers=self.sub_h)
        assert response.status_code == 200, response.text
        response = self.client.post(
            f"{API}/works/{work_id}/payment-approvals",
            json={"approval_type": "contractor_supervisor"},
            headers=self.cs_h,
        )
        assert response.status_code == 200, response.text
        return self.client.post(
            f"{API}/works/{work_id}/payment-approvals",
            json={"approval_type": "main_contractor"},
            headers=self.mc_h,
        )

    def wallet_balance(self) -> Decimal:
        """
        Current project wallet balance.

        Returns:
            Decimal: Wallet balance in KES.
        """
        response = self.client.get(f"{API}/projects/{self.project_id}", headers=self.mc_h)
        return Decimal(response.json()["wallet_balance"])


@pytest.fixture()
def team(client: TestClient, db: Session) -> Team:
    """
    A ready project with main contractor, supervisors and a subcontractor.

    Args:
        client (TestClient): Test HTTP client.
        db (Session): Database session.

    Returns:
        Team: The ready team.
    """
    return Team(client, db)


class ScriptedProvider(MockPaymentProvider):
    """Mock provider that fails payments to chosen phone numbers."""

    def __init__(self, failing_phones: Set[str]) -> None:
        """
        Remember which phone numbers should fail.

        Args:
            failing_phones (Set[str]): Phone numbers that should fail to receive payments.
        """
        self.failing_phones = failing_phones

    def send(self, phone_number: str, amount: Decimal, remarks: str) -> PaymentResult:
        """
        Fail on purpose for listed numbers, otherwise succeed.

        Args:
            phone_number (str): Recipient phone number in the format 254XXXXXXXXX.
            amount (Decimal): Amount in KES.
            remarks (str): Short note sent with the payment.

        Returns:
            PaymentResult: Whether the payment succeeded, with the provider reference.
        """
        if phone_number in self.failing_phones:
            return PaymentResult(False, f"FAIL-{uuid.uuid4().hex[:12]}", "Simulated failure")
        return PaymentResult(True, f"OK-{uuid.uuid4().hex[:12]}", "OK")


@pytest.fixture()
def failing_phones(monkeypatch: pytest.MonkeyPatch) -> Set[str]:
    """
    Phone numbers added to this set will fail to receive payments.

    Args:
        monkeypatch (pytest.MonkeyPatch): Pytest helper used to replace the payment provider.

    Returns:
        Set[str]: The (initially empty) set of failing phone numbers.
    """
    phones: Set[str] = set()
    provider = ScriptedProvider(phones)

    def get_provider() -> ScriptedProvider:
        """
        Return the scripted provider.

        Returns:
            ScriptedProvider: The scripted provider.
        """
        return provider

    monkeypatch.setattr(payment_service, "get_payment_provider", get_provider)
    return phones
