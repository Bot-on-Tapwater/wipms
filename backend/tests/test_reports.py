"""Tests for reports (JSON, printable HTML and PDF) and data isolation."""
from typing import Set

from tests.conftest import API, PHONE_B, Team


def paid_work_with_one_failure(team: Team, phones: Set[str]) -> str:
    """
    A work paid with one failed labourer payment.

    Args:
        team (Team): Project with one user per role and a funded wallet.
        phones (Set[str]): Phone numbers that should fail to receive payments.

    Returns:
        str: ID of the work.
    """
    team.deposit("20000")
    work_id = team.ready_work()
    phones.add(PHONE_B)
    team.request_and_approve_payment(work_id)
    return work_id


def test_payments_report_includes_failed_payments(
    team: Team, failing_phones: Set[str]
) -> None:
    """
    Successful and failed payments both appear and can be filtered.

    Args:
        team (Team): Project with one user per role and a funded wallet.
        failing_phones (Set[str]): Phone numbers that should fail to receive payments.
    """
    paid_work_with_one_failure(team, failing_phones)
    url = f"{API}/reports/payments"
    report = team.client.get(url, headers=team.mc_h).json()
    assert report["title"] == "Payments Report"
    assert len(report["rows"]) == 3
    summary = {item["label"]: item["value"] for item in report["summary"]}
    assert summary["Failed"] == "1"
    assert summary["Total paid"] == "KES 7,000.00"

    failed = team.client.get(url, params={"successful": "false"}, headers=team.mc_h).json()
    assert len(failed) and len(failed["rows"]) == 1
    status_column = failed["columns"].index("Status")
    assert failed["rows"][0][status_column] == "Failed"


def test_report_formats(team: Team, failing_phones: Set[str]) -> None:
    """
    Reports print as HTML and download as PDF.

    Args:
        team (Team): Project with one user per role and a funded wallet.
        failing_phones (Set[str]): Phone numbers that should fail to receive payments.
    """
    paid_work_with_one_failure(team, failing_phones)
    for name in ("payments", "labourers", "works", "projects"):
        html = team.client.get(f"{API}/reports/{name}", params={"format": "html"}, headers=team.mc_h)
        assert html.status_code == 200
        assert html.headers["content-type"].startswith("text/html")
        assert "Report" in html.text

        pdf = team.client.get(f"{API}/reports/{name}", params={"format": "pdf"}, headers=team.mc_h)
        assert pdf.status_code == 200, pdf.text
        assert pdf.headers["content-type"] == "application/pdf"
        assert pdf.content.startswith(b"%PDF")
        assert "attachment" in pdf.headers["content-disposition"]


def test_labourers_and_works_reports(team: Team, failing_phones: Set[str]) -> None:
    """
    Labourers report lists days and paid amounts; works report filters by status.

    Args:
        team (Team): Project with one user per role and a funded wallet.
        failing_phones (Set[str]): Phone numbers that should fail to receive payments.
    """
    paid_work_with_one_failure(team, failing_phones)
    labourers = team.client.get(f"{API}/reports/labourers", headers=team.mc_h).json()
    assert len(labourers["rows"]) == 2
    works = team.client.get(
        f"{API}/reports/works", params={"payment_status": "approved"}, headers=team.mc_h
    ).json()
    assert len(works["rows"]) == 1
    paid = team.client.get(
        f"{API}/reports/works", params={"payment_status": "paid"}, headers=team.mc_h
    ).json()
    assert paid["rows"] == []


def test_reports_only_show_accessible_data(
    team: Team, failing_phones: Set[str]
) -> None:
    """
    Outsiders and other subcontractors see nothing from this work.

    Args:
        team (Team): Project with one user per role and a funded wallet.
        failing_phones (Set[str]): Phone numbers that should fail to receive payments.
    """
    paid_work_with_one_failure(team, failing_phones)
    outsider = team.client.get(f"{API}/reports/payments", headers=team.outsider_h).json()
    assert outsider["rows"] == []
    forbidden = team.client.get(
        f"{API}/reports/payments", params={"project_id": team.project_id}, headers=team.outsider_h
    )
    assert forbidden.status_code == 403

    team.assign("subcontractors", team.outsider)
    other_sub = team.client.get(f"{API}/reports/payments", headers=team.outsider_h).json()
    assert other_sub["rows"] == []
    records = team.client.get(
        f"{API}/payments/records", params={"project_id": team.project_id}, headers=team.outsider_h
    ).json()
    assert records == []
    own = team.client.get(
        f"{API}/payments/records", params={"project_id": team.project_id}, headers=team.sub_h
    ).json()
    assert len(own) == 3


def test_email_report(team: Team) -> None:
    """
    Emailing a report returns a confirmation (email is logged in tests).

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    response = team.client.post(
        f"{API}/reports/email", json={"report_type": "projects"}, headers=team.mc_h
    )
    assert response.status_code == 200
    assert team.mc.email in response.json()["message"]


def test_projects_report_only_counts_own_works(team: Team) -> None:
    """
    A subcontractor's projects report leaves out amounts paid on others' works.

    Args:
        team (Team): Project with one user per role and a funded wallet.
    """
    team.deposit("20000")
    work_id = team.ready_work()
    team.request_and_approve_payment(work_id)
    team.assign("subcontractors", team.outsider)

    own = team.client.get(f"{API}/reports/projects", headers=team.sub_h).json()
    other = team.client.get(f"{API}/reports/projects", headers=team.outsider_h).json()
    paid_column = own["columns"].index("Total paid")
    assert own["rows"][0][paid_column] == "KES 9,000.00"
    assert other["rows"][0][paid_column] == "KES 0.00"
