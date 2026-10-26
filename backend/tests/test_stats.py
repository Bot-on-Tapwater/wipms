"""Tests for labour insights and labourer gender and age."""
from typing import Dict, Set

from app.constants.roles import Role
from tests.conftest import API, PHONE_A, PHONE_B, Team, auth_headers, create_user

PHONE_C = "254701000003"
STATS = f"{API}/stats/labourers"


def new_labourer(team: Team, work_id: str, details: Dict[str, object]) -> str:
    """
    Register a new labourer straight onto a work and return the labourer id.

    Args:
        team (Team): Project with one user per role.
        work_id (str): ID of the work.
        details (Dict[str, object]): Labourer fields, including days_worked.

    Returns:
        str: ID of the new labourer.
    """
    response = team.client.post(f"{API}/works/{work_id}/labourers/new", json=details, headers=team.sub_h)
    assert response.status_code == 201, response.text
    return response.json()["labourer"]["id"]


def paid_mixed_crew(team: Team) -> str:
    """
    A paid work with two carpenters and one mason.

    Carpenter A: male, 30, 1,000 x 3 days. Carpenter B: no gender or age, 500 x 4 days.
    Mason C: female, 45, 600 x 2 days.

    Args:
        team (Team): Project with one user per role.

    Returns:
        str: ID of the work.
    """
    team.deposit("20000")
    work_id = team.create_work(cost_labor="10000")
    new_labourer(team, work_id, {
        "name": "Carpenter A", "title": "carpenters", "national_id_number": "11111111",
        "phone_number": PHONE_A, "daily_rate": "1000", "days_worked": 3, "gender": "male", "age": 30,
    })
    new_labourer(team, work_id, {
        "name": "Carpenter B", "title": "carpenters", "national_id_number": "22222222",
        "phone_number": PHONE_B, "daily_rate": "500", "days_worked": 4, "gender": "", "age": "",
    })
    new_labourer(team, work_id, {
        "name": "Mason C", "title": "masonry", "national_id_number": "33333333",
        "phone_number": PHONE_C, "daily_rate": "600", "days_worked": 2, "gender": "female", "age": 45,
    })
    team.approve_all(work_id)
    response = team.request_and_approve_payment(work_id)
    assert response.status_code == 200, response.text
    return work_id


def by_key(buckets: list) -> Dict[str, dict]:
    """
    Index chart bars by their key.

    Args:
        buckets (list): Chart bars from the response.

    Returns:
        Dict[str, dict]: Chart bars by key.
    """
    return {item["key"]: item for item in buckets}


def test_main_contractor_sees_trades_gender_and_age(team: Team, failing_phones: Set[str]) -> None:
    """
    Labourers, days and pay add up per trade, gender and age group.

    Args:
        team (Team): Project with one user per role.
        failing_phones (Set[str]): Phone numbers that should fail to receive payments.
    """
    paid_mixed_crew(team)
    stats = team.client.get(STATS, headers=team.mc_h).json()
    assert stats["scope"] == "mine"
    assert [project["name"] for project in stats["projects"]] == ["Riverside Apartments"]
    assert stats["totals"]["labourers"] == 3
    assert stats["totals"]["registered"] == 3
    assert stats["totals"]["days_worked"] == 9
    assert float(stats["totals"]["amount_paid"]) == 6200

    trades = by_key(stats["by_trade"])
    assert stats["by_trade"][0]["key"] == "carpenters"
    assert trades["carpenters"]["labourers"] == 2
    assert float(trades["carpenters"]["amount_paid"]) == 5000
    assert trades["masonry"]["days_worked"] == 2
    assert float(trades["masonry"]["amount_paid"]) == 1200

    genders = by_key(stats["by_gender"])
    assert [genders[key]["labourers"] for key in ("male", "female", "not_given")] == [1, 1, 1]
    ages = by_key(stats["by_age_group"])
    assert ages["25-34"]["labourers"] == 1
    assert ages["45-54"]["labourers"] == 1
    assert ages["not_given"]["labourers"] == 1

    project = stats["by_project"][0]
    assert project["labourers"] == 3
    assert {trade["key"] for trade in project["trades"]} == {"carpenters", "masonry"}
    assert stats["by_month"][-1]["days_worked"] == 9
    assert stats["top_labourers"][0]["name"] == "Carpenter B"


def test_filters_narrow_every_number(team: Team, failing_phones: Set[str]) -> None:
    """
    Trade, gender and age group filters only count matching labourers.

    Args:
        team (Team): Project with one user per role.
        failing_phones (Set[str]): Phone numbers that should fail to receive payments.
    """
    paid_mixed_crew(team)
    female = team.client.get(STATS, params={"gender": "female"}, headers=team.mc_h).json()
    assert female["totals"]["labourers"] == 1
    assert female["totals"]["registered"] == 1
    assert [trade["key"] for trade in female["by_trade"]] == ["masonry"]

    not_given = team.client.get(STATS, params={"age_group": "not_given"}, headers=team.mc_h).json()
    assert [person["name"] for person in not_given["top_labourers"]] == ["Carpenter B"]

    carpenters = team.client.get(
        STATS, params={"trade": "carpenters", "project_id": team.project_id}, headers=team.mc_h
    ).json()
    assert carpenters["totals"]["days_worked"] == 7
    assert float(carpenters["totals"]["amount_paid"]) == 5000

    response = team.client.get(STATS, params={"gender": "other"}, headers=team.mc_h)
    assert response.status_code == 422


def test_only_super_admin_and_main_contractor_see_insights(team: Team) -> None:
    """
    Supervisors and subcontractors cannot open insights.

    Args:
        team (Team): Project with one user per role.
    """
    for headers in (team.cs_h, team.con_h, team.sub_h):
        assert team.client.get(STATS, headers=headers).status_code == 403
    assert team.client.get(STATS, headers=team.mc_h).status_code == 200


def test_super_admin_sees_every_project(team: Team, failing_phones: Set[str]) -> None:
    """
    The super admin sees all projects; another main contractor only sees their own.

    Args:
        team (Team): Project with one user per role.
        failing_phones (Set[str]): Phone numbers that should fail to receive payments.
    """
    paid_mixed_crew(team)
    other = create_user(team.db, Role.MAIN_CONTRACTOR, "other@example.com", "254777777777")
    other_h = auth_headers(team.client, other.email)
    response = team.client.post(
        f"{API}/projects", json={"name": "Hill View", "location": "Nakuru"}, headers=other_h
    )
    assert response.status_code == 201, response.text

    create_user(team.db, Role.SUPER_ADMIN, "admin@example.com", "254766666666")
    admin_h = auth_headers(team.client, "admin@example.com")
    stats = team.client.get(STATS, headers=admin_h).json()
    assert stats["scope"] == "all"
    assert {project["name"] for project in stats["projects"]} == {"Riverside Apartments", "Hill View"}
    assert stats["totals"]["labourers"] == 3

    mine = team.client.get(STATS, headers=other_h).json()
    assert [project["name"] for project in mine["projects"]] == ["Hill View"]
    assert mine["totals"]["labourers"] == 0
    assert mine["totals"]["registered"] == 0
    response = team.client.get(STATS, params={"project_id": team.project_id}, headers=other_h)
    assert response.status_code == 403


def test_labourer_gender_and_age_are_optional(team: Team) -> None:
    """
    Gender and age can be given, left out, changed and cleared. Under 18 is refused.

    Args:
        team (Team): Project with one user per role.
    """
    details = {
        "name": "Jane Builder", "title": "painters", "national_id_number": "44444444",
        "phone_number": "254701000004", "daily_rate": "800",
    }
    young = team.client.post(f"{API}/labourers", json={**details, "age": 17}, headers=team.sub_h)
    assert young.status_code == 422

    created = team.client.post(
        f"{API}/labourers", json={**details, "gender": "female", "age": 30}, headers=team.sub_h
    )
    assert created.status_code == 201, created.text
    labourer = created.json()
    assert labourer["gender"] == "female"
    assert labourer["age"] == 30

    url = f"{API}/labourers/{labourer['id']}"
    renamed = team.client.patch(url, json={"name": "Jane B"}, headers=team.sub_h).json()
    assert renamed["gender"] == "female"
    assert renamed["age"] == 30

    cleared = team.client.patch(url, json={"gender": "", "age": None}, headers=team.sub_h).json()
    assert cleared["gender"] is None
    assert cleared["age"] is None
