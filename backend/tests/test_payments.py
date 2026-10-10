"""Tests for the payment flow (mocked provider).

Standard work used below: labour estimate 10,000, no overhead, retention 10%.
Labourer A: 1,000 x 3 days = 3,000. Labourer B: 500 x 4 days = 2,000.
Subcontractor is paid 10,000 - 5,000 - 1,000 retention = 4,000.
"""
from decimal import Decimal
from typing import Optional, Set

from app.constants.roles import Role
from tests.conftest import API, PHONE_A, PHONE_B, Team, auth_headers, create_user


def records(team: Team, work_id: str, successful: Optional[bool] = None) -> list:
    """
    Payment records of a work.

    Args:
        team (Team): Project with one user per role and a funded wallet.
        work_id (str): ID of the work.
        successful (Optional[bool]): True for successful payments only, False for failed only, None for both.

    Returns:
        list: Payment records as returned by the API.
    """
    params = {"work_id": work_id}
    if successful is not None:
        params["successful"] = str(successful).lower()
    response = team.client.get(f"{API}/payments/records", params=params, headers=team.mc_h)
    assert response.status_code == 200, response.text
    return response.json()


def first_labourer_id(team: Team, work_id: str) -> str:
    """
    ID of the first labourer on a work.

    Args:
        team (Team): Project with one user per role and a funded wallet.
        work_id (str): ID of the work.

    Returns:
        str: ID of the labourer.
    """
    response = team.client.get(f"{API}/works/{work_id}/labourers", headers=team.mc_h)
    assert response.status_code == 200, response.text
    return response.json()[0]["labourer"]["id"]


def test_payment_summary_breakdown(team: Team) -> None:
    """
    The summary shows who gets what before approving.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    work_id = team.ready_work()
    summary = team.client.get(f"{API}/works/{work_id}/payment-summary", headers=team.mc_h).json()
    assert Decimal(summary["total_labour_due"]) == Decimal("5000")
    assert Decimal(summary["retention_money"]) == Decimal("1000")
    assert Decimal(summary["subcontractor_amount"]) == Decimal("4000")


def test_full_payment_flow(team: Team, failing_phones: Set[str]) -> None:
    """
    Both approvals pay labourers and subcontractor and debit the wallet.

    Args:
        team (Team): Project with one user per role and a funded wallet.
        failing_phones (Set[str]): Phone numbers that should fail to receive payments.
    """
    team.deposit("20000")
    work_id = team.ready_work()

    response = team.request_and_approve_payment(work_id)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["payments_made"] == 3 and body["payments_failed"] == 0
    assert body["work"]["payment_status"] == "paid"
    assert Decimal(body["work"]["total_labourers_paid_out"]) == Decimal("5000")
    assert body["work"]["is_completed"] is False  # retention still outstanding

    paid = records(team, work_id, successful=True)
    amounts = sorted(Decimal(item["amount_paid"]) for item in paid)
    assert amounts == [Decimal("2000"), Decimal("3000"), Decimal("4000")]
    assert team.wallet_balance() == Decimal("11000")

    again = team.client.post(
        f"{API}/works/{work_id}/payment-approvals",
        json={"approval_type": "main_contractor"},
        headers=team.mc_h,
    )
    assert "already been processed" in again.json()["message"]
    assert len(records(team, work_id)) == 3  # nobody paid twice


def test_paid_work_is_locked(team: Team, failing_phones: Set[str]) -> None:
    """
    After payment the work, its labourers and approvals cannot change.

    Args:
        team (Team): Project with one user per role and a funded wallet.
        failing_phones (Set[str]): Phone numbers that should fail to receive payments.
    """
    team.deposit("20000")
    work_id = team.ready_work()
    team.request_and_approve_payment(work_id)
    edit = team.client.patch(f"{API}/works/{work_id}", json={"cost_labor": "1"}, headers=team.sub_h)
    assert edit.status_code == 400
    delete = team.client.delete(f"{API}/works/{work_id}", headers=team.mc_h)
    assert delete.status_code == 400


def test_approval_needs_payment_request(team: Team) -> None:
    """
    Approving before the subcontractor requests payment fails.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    work_id = team.ready_work()
    response = team.client.post(
        f"{API}/works/{work_id}/payment-approvals",
        json={"approval_type": "main_contractor"},
        headers=team.mc_h,
    )
    assert response.status_code == 400


def test_approval_type_needs_matching_permission(team: Team) -> None:
    """
    The contractor supervisor cannot give the main contractor approval.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    team.deposit("20000")
    work_id = team.ready_work()
    team.client.post(f"{API}/works/{work_id}/payment-request", headers=team.sub_h)
    response = team.client.post(
        f"{API}/works/{work_id}/payment-approvals",
        json={"approval_type": "main_contractor"},
        headers=team.cs_h,
    )
    assert response.status_code == 403


def test_missing_cost_approval_blocks_payment(team: Team) -> None:
    """
    Payment cannot be approved until the main contractor approved the cost.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    work_id = team.create_work()
    team.client.post(f"{API}/works/{work_id}/payment-request", headers=team.sub_h)
    response = team.client.post(
        f"{API}/works/{work_id}/payment-approvals",
        json={"approval_type": "contractor_supervisor"},
        headers=team.cs_h,
    )
    assert response.status_code == 400
    assert "Cost not approved" in response.json()["detail"]


def test_insufficient_wallet_funds(team: Team, failing_phones: Set[str]) -> None:
    """
    Payment fails without paying anyone and approvals are reset.

    Args:
        team (Team): Project with one user per role and a funded wallet.
        failing_phones (Set[str]): Phone numbers that should fail to receive payments.
    """
    team.deposit("5000")
    work_id = team.ready_work()
    response = team.request_and_approve_payment(work_id)
    assert response.status_code == 400
    assert "Insufficient funds" in response.json()["detail"]
    assert records(team, work_id) == []
    work = team.client.get(f"{API}/works/{work_id}", headers=team.mc_h).json()
    assert work["payment_requested"] is False
    assert work["payment_status"] == "pending"
    assert team.wallet_balance() == Decimal("5000")


def test_labour_cost_above_estimate(team: Team, failing_phones: Set[str]) -> None:
    """
    Labourers owed more than the labour estimate blocks payment.

    Args:
        team (Team): Project with one user per role and a funded wallet.
        failing_phones (Set[str]): Phone numbers that should fail to receive payments.
    """
    team.deposit("50000")
    work_id = team.create_work(cost_labor="2000")
    team.add_labourer(work_id, "11111111", PHONE_A, "1000", 3)
    team.approve_all(work_id)
    response = team.request_and_approve_payment(work_id)
    assert response.status_code == 400
    assert "exceeds original estimate" in response.json()["detail"]
    assert records(team, work_id) == []


def test_failed_payment_is_recorded_and_retried(team: Team, failing_phones: Set[str]) -> None:
    """
    A failed labourer payment keeps the work 'approved' until a retry succeeds.

    Args:
        team (Team): Project with one user per role and a funded wallet.
        failing_phones (Set[str]): Phone numbers that should fail to receive payments.
    """
    team.deposit("20000")
    work_id = team.ready_work()
    failing_phones.add(PHONE_B)

    response = team.request_and_approve_payment(work_id)
    body = response.json()
    assert body["payments_made"] == 2 and body["payments_failed"] == 1
    assert body["work"]["payment_status"] == "approved"
    failed = records(team, work_id, successful=False)
    assert len(failed) == 1 and failed[0]["recipient_phone"] == PHONE_B
    assert failed[0]["failure_reason"] == "Simulated failure"

    # Subcontractor still gets 4,000 (failed labour money is NOT added to them)
    sub_payment = [item for item in records(team, work_id, True) if item["payment_type"] == "subcontractor"]
    assert Decimal(sub_payment[0]["amount_paid"]) == Decimal("4000")
    assert team.wallet_balance() == Decimal("13000")

    # Approving again does not pay anyone twice
    again = team.client.post(
        f"{API}/works/{work_id}/payment-approvals",
        json={"approval_type": "main_contractor"},
        headers=team.mc_h,
    )
    assert again.status_code == 400

    failing_phones.clear()
    retry = team.client.post(f"{API}/works/{work_id}/payments/retry", headers=team.mc_h)
    assert retry.status_code == 200, retry.text
    assert retry.json()["work"]["payment_status"] == "paid"
    assert team.wallet_balance() == Decimal("11000")
    assert len(records(team, work_id, successful=True)) == 3

    no_more = team.client.post(f"{API}/works/{work_id}/payments/retry", headers=team.mc_h)
    assert no_more.status_code == 400


def test_retention_flow(team: Team, failing_phones: Set[str]) -> None:
    """
    Retention is requested after payment and released by the main contractor.

    Args:
        team (Team): Project with one user per role and a funded wallet.
        failing_phones (Set[str]): Phone numbers that should fail to receive payments.
    """
    team.deposit("20000")
    work_id = team.ready_work()

    early = team.client.post(f"{API}/works/{work_id}/retention-request", headers=team.sub_h)
    assert early.status_code == 400

    team.request_and_approve_payment(work_id)
    request = team.client.post(f"{API}/works/{work_id}/retention-request", headers=team.sub_h)
    assert request.status_code == 200
    assert request.json()["retention_payment_requested"] is True

    denied = team.client.post(f"{API}/works/{work_id}/retention-approval", headers=team.cs_h)
    assert denied.status_code == 403

    response = team.client.post(f"{API}/works/{work_id}/retention-approval", headers=team.mc_h)
    assert response.status_code == 200, response.text
    work = response.json()["work"]
    assert work["retention_paid"] is True
    assert work["is_completed"] is True
    assert team.wallet_balance() == Decimal("10000")

    project = team.client.get(f"{API}/projects/{team.project_id}", headers=team.mc_h).json()
    assert project["is_completed"] is True


def test_payment_records_scope(team: Team) -> None:
    """
    Without project access, records cannot be listed.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    response = team.client.get(
        f"{API}/payments/records", params={"project_id": team.project_id}, headers=team.outsider_h
    )
    assert response.status_code == 403


def test_payment_records_of_all_my_projects(team: Team, failing_phones: Set[str]) -> None:
    """
    Without a project or work, users get the records of the projects they are on.

    Args:
        team (Team): Project with one user per role and a funded wallet.
        failing_phones (Set[str]): Phone numbers that should fail to receive payments.
    """
    team.deposit("20000")
    team.request_and_approve_payment(team.ready_work())

    for headers in (team.mc_h, team.cs_h, team.sub_h):
        response = team.client.get(f"{API}/payments/records", headers=headers)
        assert response.status_code == 200, response.text
        assert len(response.json()) == 3
    outsider = team.client.get(f"{API}/payments/records", headers=team.outsider_h)
    assert outsider.status_code == 200
    assert outsider.json() == []


def test_retention_never_pays_more_than_the_work_cost(team: Team, failing_phones: Set[str]) -> None:
    """
    When labour takes up most of the cost, retention is capped at what is left.

    Labour estimate 10,000 and labourers owed 9,500: the subcontractor gets
    nothing now and only 500 of the 1,000 retention, so 10,000 is paid in total.

    Args:
        team (Team): Project with one user per role and a funded wallet.
        failing_phones (Set[str]): Phone numbers that should fail to receive payments.
    """
    team.deposit("20000")
    work_id = team.create_work(cost_labor="10000")
    team.add_labourer(work_id, "11111111", PHONE_A, "950", 10)
    team.approve_all(work_id)
    response = team.request_and_approve_payment(work_id)
    assert response.status_code == 200, response.text
    assert response.json()["work"]["payment_status"] == "paid"

    team.client.post(f"{API}/works/{work_id}/retention-request", headers=team.sub_h)
    response = team.client.post(f"{API}/works/{work_id}/retention-approval", headers=team.mc_h)
    assert response.status_code == 200, response.text
    assert response.json()["work"]["retention_paid"] is True
    retention = [item for item in records(team, work_id, True) if item["payment_type"] == "retention"]
    assert Decimal(retention[0]["amount_paid"]) == Decimal("500")
    assert team.wallet_balance() == Decimal("10000")


def test_changing_amounts_withdraws_the_payment_request(team: Team) -> None:
    """
    Changing cost, days or subcontractor means payment must be requested again.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    work_id = team.ready_work()
    labourer_id = first_labourer_id(team, work_id)
    url = f"{API}/works/{work_id}"
    changes = [
        ("patch", url, {"cost_labor": "11000"}),
        ("patch", f"{url}/labourers/{labourer_id}", {"days_worked": 5}),
        ("delete", f"{url}/subcontractor", None),
    ]
    for method, change_url, body in changes:
        team.client.post(f"{url}/payment-request", headers=team.mc_h)
        approval = team.client.post(
            f"{url}/payment-approvals",
            json={"approval_type": "contractor_supervisor"},
            headers=team.cs_h,
        )
        assert approval.json()["work"]["contractor_supervisor_payment_approval"] is True
        if method == "patch":
            response = team.client.patch(change_url, json=body, headers=team.mc_h)
        else:
            response = team.client.delete(change_url, headers=team.mc_h)
        assert response.status_code == 200, response.text
        work = team.client.get(url, headers=team.mc_h).json()
        assert work["payment_requested"] is False
        assert work["contractor_supervisor_payment_approval"] is False
        team.approve_all(work_id)


def test_partly_failed_work_is_locked(team: Team, failing_phones: Set[str]) -> None:
    """
    While failed payments wait for a retry, the work's amounts cannot change.

    Args:
        team (Team): Project with one user per role and a funded wallet.
        failing_phones (Set[str]): Phone numbers that should fail to receive payments.
    """
    team.deposit("20000")
    work_id = team.ready_work()
    failing_phones.add(PHONE_B)
    response = team.request_and_approve_payment(work_id)
    assert response.json()["work"]["payment_status"] == "approved"
    labourer_id = first_labourer_id(team, work_id)

    url = f"{API}/works/{work_id}"
    edit = team.client.patch(url, json={"cost_labor": "20000"}, headers=team.sub_h)
    assert edit.status_code == 400
    days = team.client.patch(f"{url}/labourers/{labourer_id}", json={"days_worked": 9}, headers=team.sub_h)
    assert days.status_code == 400
    remove = team.client.delete(f"{url}/labourers/{labourer_id}", headers=team.sub_h)
    assert remove.status_code == 400


def test_labourer_pay_change_withdraws_approvals(team: Team) -> None:
    """
    A new daily rate changes what is owed, so unpaid works need fresh approvals.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    work_id = team.ready_work()
    labourer_id = first_labourer_id(team, work_id)
    team.client.post(f"{API}/works/{work_id}/payment-request", headers=team.sub_h)

    name_only = team.client.patch(
        f"{API}/labourers/{labourer_id}", json={"name": "New Name"}, headers=team.sub_h
    )
    assert name_only.status_code == 200
    work = team.client.get(f"{API}/works/{work_id}", headers=team.sub_h).json()
    assert work["payment_requested"] is True and work["attendance_approval"] is True

    response = team.client.patch(
        f"{API}/labourers/{labourer_id}", json={"daily_rate": "1200"}, headers=team.sub_h
    )
    assert response.status_code == 200, response.text
    work = team.client.get(f"{API}/works/{work_id}", headers=team.sub_h).json()
    assert work["payment_requested"] is False
    assert work["attendance_approval"] is False


def test_payment_summary_needs_permission(team: Team) -> None:
    """
    The payment summary follows the ``payments.view`` permission.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    work_id = team.ready_work()
    url = f"{API}/works/{work_id}/payment-summary"
    assert team.client.get(url, headers=team.sub_h).status_code == 200
    create_user(team.db, Role.SUPER_ADMIN, "admin@example.com", "254766666666")
    admin_h = auth_headers(team.client, "admin@example.com")
    revoke = team.client.post(
        f"{API}/permissions/roles/subcontractor/revoke", json={"code": "payments.view"}, headers=admin_h
    )
    assert revoke.status_code == 200
    assert team.client.get(url, headers=team.sub_h).status_code == 403
