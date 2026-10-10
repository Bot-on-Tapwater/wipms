"""Tests for projects, teams, wallet, works, approvals and labourers."""
from decimal import Decimal

from tests.conftest import API, Team


def test_only_main_contractor_creates_projects(team: Team) -> None:
    """
    Project creation needs ``projects.create``.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    body = {"name": "Other", "location": "Mombasa"}
    assert team.client.post(f"{API}/projects", json=body, headers=team.sub_h).status_code == 403
    assert team.client.post(f"{API}/projects", json=body, headers=team.mc_h).status_code == 201


def test_project_visibility(team: Team) -> None:
    """
    Members see the project; outsiders do not.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    url = f"{API}/projects/{team.project_id}"
    assert team.client.get(url, headers=team.sub_h).status_code == 200
    assert team.client.get(url, headers=team.con_h).status_code == 200
    assert team.client.get(url, headers=team.outsider_h).status_code == 403
    listed = team.client.get(f"{API}/projects", headers=team.outsider_h).json()
    assert listed == []


def test_team_assignment_checks_role(team: Team) -> None:
    """
    A subcontractor cannot be added as contractor supervisor.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    response = team.client.post(
        f"{API}/projects/{team.project_id}/contractor-supervisors",
        json={"user_ids": [str(team.outsider.id)]},
        headers=team.mc_h,
    )
    assert response.status_code == 400


def test_wallet_deposit_and_transactions(team: Team) -> None:
    """
    Deposits increase the wallet and are logged.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    team.deposit("5000")
    team.deposit("2500.50")
    assert team.wallet_balance() == Decimal("7500.50")
    transactions = team.client.get(
        f"{API}/projects/{team.project_id}/wallet/transactions", headers=team.mc_h
    ).json()
    assert len(transactions) == 2
    response = team.client.post(
        f"{API}/projects/{team.project_id}/wallet/deposits",
        json={"amount": "100"},
        headers=team.sub_h,
    )
    assert response.status_code == 403


def test_subcontractor_work_is_auto_assigned(team: Team) -> None:
    """
    A work created by a subcontractor is assigned to them.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    work_id = team.create_work()
    work = team.client.get(f"{API}/works/{work_id}", headers=team.sub_h).json()
    assert work["assigned_subcontractor"]["id"] == str(team.sub.id)
    assert Decimal(work["total_cost"]) == Decimal("10000")
    assert Decimal(work["retention_money"]) == Decimal("1000.00")


def test_assign_and_unassign_subcontractor(team: Team) -> None:
    """
    The main contractor can change the subcontractor of a work, but only to a
    subcontractor of the project.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    work_id = team.create_work()
    url = f"{API}/works/{work_id}/subcontractor"

    # Check if the subcontractor can be removed and assigned again
    response = team.client.delete(url, headers=team.mc_h)
    assert response.status_code == 200, response.text
    assert response.json()["assigned_subcontractor"] is None
    body = {"subcontractor_id": str(team.sub.id)}
    assert team.client.put(url, json=body, headers=team.sub_h).status_code == 403
    response = team.client.put(url, json=body, headers=team.mc_h)
    assert response.status_code == 200, response.text
    assert response.json()["assigned_subcontractor"]["id"] == str(team.sub.id)

    # Check if users outside the project or with another role are rejected
    outsider = {"subcontractor_id": str(team.outsider.id)}
    response = team.client.put(url, json=outsider, headers=team.mc_h)
    assert response.status_code == 400
    assert "first be assigned to the project" in response.json()["detail"]
    supervisor = {"subcontractor_id": str(team.cs.id)}
    response = team.client.put(url, json=supervisor, headers=team.mc_h)
    assert response.status_code == 400
    assert "not a subcontractor" in response.json()["detail"]


def test_outsider_cannot_create_work_in_project(team: Team) -> None:
    """
    Only project members may add works.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    response = team.client.post(
        f"{API}/works",
        json={"project_id": team.project_id, "title": "x", "category": "bricklaying", "cost_labor": "1"},
        headers=team.outsider_h,
    )
    assert response.status_code == 403


def test_approvals_need_the_right_role(team: Team) -> None:
    """
    Each approval type is limited to its role.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    work_id = team.create_work()
    url = f"{API}/works/{work_id}/approvals"
    cost = {"approval_type": "cost", "approved": True}
    assert team.client.post(url, json=cost, headers=team.con_h).status_code == 403
    assert team.client.post(url, json=cost, headers=team.mc_h).status_code == 200
    consultant = {"approval_type": "consultant", "approved": True}
    assert team.client.post(url, json=consultant, headers=team.sub_h).status_code == 403
    assert team.client.post(url, json=consultant, headers=team.con_h).status_code == 200


def test_cost_change_resets_cost_approval(team: Team) -> None:
    """
    Editing the cost means the main contractor must approve it again.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    work_id = team.create_work()
    team.approve_all(work_id)
    response = team.client.patch(
        f"{API}/works/{work_id}", json={"cost_labor": "12000"}, headers=team.sub_h
    )
    assert response.status_code == 200
    assert response.json()["cost_approval"] is False
    assert response.json()["consultant_approval"] is True


def test_labourer_change_resets_attendance_approval(team: Team) -> None:
    """
    Changing labourers or days means attendance must be approved again.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    work_id = team.create_work()
    labourer_id = team.add_labourer(work_id, "12345678", "254701000001", "1000", 2)
    team.approve_all(work_id)
    response = team.client.patch(
        f"{API}/works/{work_id}/labourers/{labourer_id}",
        json={"days_worked": 3},
        headers=team.sub_h,
    )
    assert response.status_code == 200
    assert Decimal(response.json()["amount_due"]) == Decimal("3000")
    work = team.client.get(f"{API}/works/{work_id}", headers=team.sub_h).json()
    assert work["attendance_approval"] is False


def test_subcontractor_only_sees_own_works(team: Team) -> None:
    """
    Another subcontractor on the project cannot see the work.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    work_id = team.create_work()
    team.assign("subcontractors", team.outsider)
    assert team.client.get(f"{API}/works/{work_id}", headers=team.outsider_h).status_code == 403
    listed = team.client.get(
        f"{API}/works", params={"project_id": team.project_id}, headers=team.outsider_h
    ).json()
    assert listed == []


def test_works_listed_across_projects(team: Team) -> None:
    """
    Without project_id the list holds works from every visible project.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    work_id = team.create_work()
    for headers in (team.mc_h, team.sub_h):
        listed = team.client.get(f"{API}/works", headers=headers).json()
        assert [work["id"] for work in listed] == [work_id]
    assert team.client.get(f"{API}/works", headers=team.outsider_h).json() == []


def test_comments_by_supervisors(team: Team) -> None:
    """
    Each supervisor writes in their own comment field.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    work_id = team.create_work()
    response = team.client.post(
        f"{API}/works/{work_id}/comments/consultant-supervisor",
        json={"comment": "Check plumb lines"},
        headers=team.con_h,
    )
    assert response.status_code == 200
    assert response.json()["consultant_supervisor_comments"] == "Check plumb lines"
    response = team.client.post(
        f"{API}/works/{work_id}/comments/contractor-supervisor",
        json={"comment": "Hi"},
        headers=team.con_h,
    )
    assert response.status_code == 403


def test_image_upload_and_download(team: Team) -> None:
    """
    Images are stored and only served to authorised users.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    work_id = team.create_work()
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    response = team.client.post(
        f"{API}/works/{work_id}/images",
        files={"file": ("site.png", png, "image/png")},
        data={"description": "Wall"},
        headers=team.sub_h,
    )
    assert response.status_code == 201, response.text
    file_url = response.json()["file_url"]
    assert team.client.get(file_url, headers=team.sub_h).content == png
    assert team.client.get(file_url).status_code == 401
    bad = team.client.post(
        f"{API}/works/{work_id}/images",
        files={"file": ("run.exe", b"MZ", "application/x-msdownload")},
        headers=team.sub_h,
    )
    assert bad.status_code == 400


def test_labourer_autocomplete_by_name_and_id(team: Team) -> None:
    """
    Search matches part of the name or the start of the ID number.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    work_id = team.create_work()
    team.add_labourer(work_id, "30111222", "254701000001", "800", 1)
    team.add_labourer(work_id, "40999888", "254701000002", "900", 1)
    url = f"{API}/labourers/search"

    by_id = team.client.get(url, params={"q": "301"}, headers=team.sub_h).json()
    assert [item["national_id_number"] for item in by_id] == ["30111222"]

    by_name = team.client.get(url, params={"q": "labourer 409"}, headers=team.sub_h).json()
    assert len(by_name) == 1 and by_name[0]["national_id_number"] == "40999888"

    wildcard = team.client.get(url, params={"q": "%%"}, headers=team.sub_h).json()
    assert wildcard == []
    assert team.client.get(url, params={"q": "a"}, headers=team.sub_h).status_code == 422


def test_existing_labourer_reused_and_duplicate_id_rejected(team: Team) -> None:
    """
    National ID numbers are unique; existing labourers are assigned, not re-created.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    first = team.create_work()
    labourer_id = team.add_labourer(first, "30111222", "254701000001", "800", 1)
    second = team.create_work()
    duplicate = team.client.post(
        f"{API}/works/{second}/labourers/new",
        json={"name": "Someone Else", "title": "painters", "national_id_number": "30111222",
              "phone_number": "254701000009", "daily_rate": "500", "days_worked": 1},
        headers=team.sub_h,
    )
    assert duplicate.status_code == 400
    response = team.client.post(
        f"{API}/works/{second}/labourers",
        json={"labourer_id": labourer_id, "days_worked": 2},
        headers=team.sub_h,
    )
    assert response.status_code == 201


def test_wallet_transactions_hidden_from_subcontractors(team: Team) -> None:
    """
    Subcontractors cannot see the deposits and payouts of the project wallet.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    team.deposit("5000")
    url = f"{API}/projects/{team.project_id}/wallet/transactions"
    assert team.client.get(url, headers=team.sub_h).status_code == 403
    assert team.client.get(url, headers=team.cs_h).status_code == 200
    assert team.client.get(url, headers=team.con_h).status_code == 200


def test_image_description_length_is_limited(team: Team) -> None:
    """
    Image descriptions longer than the database column are rejected.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    work_id = team.create_work()
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    response = team.client.post(
        f"{API}/works/{work_id}/images",
        files={"file": ("site.png", png, "image/png")},
        data={"description": "x" * 256},
        headers=team.sub_h,
    )
    assert response.status_code == 422


def test_labourer_create_and_edit(team: Team) -> None:
    """
    Labourers are registered and only edited by whoever registered them.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    body = {"name": "Otieno Juma", "title": "carpenters", "national_id_number": "55555555",
            "phone_number": "254701000005", "daily_rate": "700"}
    response = team.client.post(f"{API}/labourers", json=body, headers=team.sub_h)
    assert response.status_code == 201, response.text
    labourer_id = response.json()["id"]

    edit = team.client.patch(
        f"{API}/labourers/{labourer_id}", json={"daily_rate": "750"}, headers=team.sub_h
    )
    assert edit.status_code == 200
    assert Decimal(edit.json()["daily_rate"]) == Decimal("750")
    other = team.client.patch(
        f"{API}/labourers/{labourer_id}", json={"daily_rate": "1"}, headers=team.cs_h
    )
    assert other.status_code == 403
    found = team.client.get(f"{API}/labourers/{labourer_id}", headers=team.con_h)
    assert found.json()["name"] == "Otieno Juma"
