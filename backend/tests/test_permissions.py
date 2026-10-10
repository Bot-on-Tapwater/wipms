"""Tests for the permission model and changing permissions."""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.constants.permissions import PERMISSIONS
from app.constants.roles import Role
from tests.conftest import API, auth_headers, create_user


def test_my_permissions_lists_role_codes(client: TestClient, db: Session) -> None:
    """
    The frontend reads the logged in user's permissions from /permissions/me.

    Args:
        client (TestClient): Test HTTP client.
        db (Session): Database session.
    """
    create_user(db, Role.CONSULTANTS_SUPERVISOR, "c@example.com")
    response = client.get(f"{API}/permissions/me", headers=auth_headers(client, "c@example.com"))
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "consultants-supervisor"
    assert "works.approve_as_consultant" in body["permissions"]
    assert "payments.approve_as_main_contractor" not in body["permissions"]


def test_super_admin_has_every_permission(client: TestClient, db: Session) -> None:
    """
    Super admin gets the whole catalogue.

    Args:
        client (TestClient): Test HTTP client.
        db (Session): Database session.
    """
    create_user(db, Role.SUPER_ADMIN, "admin@example.com")
    response = client.get(f"{API}/permissions/me", headers=auth_headers(client, "admin@example.com"))
    assert set(response.json()["permissions"]) == set(PERMISSIONS)


def test_only_permission_managers_can_change_permissions(client: TestClient, db: Session) -> None:
    """
    Changing permissions needs ``permissions.manage``.

    Args:
        client (TestClient): Test HTTP client.
        db (Session): Database session.
    """
    create_user(db, Role.MAIN_CONTRACTOR, "owner@example.com")
    headers = auth_headers(client, "owner@example.com")
    response = client.post(
        f"{API}/permissions/roles/subcontractor/grant", json={"code": "reports.view"}, headers=headers
    )
    assert response.status_code == 403
    assert client.get(f"{API}/permissions/roles", headers=headers).status_code == 403


def test_revoking_a_permission_takes_effect_immediately(client: TestClient, db: Session) -> None:
    """
    Revoke then grant a permission and check access changes accordingly.

    Args:
        client (TestClient): Test HTTP client.
        db (Session): Database session.
    """
    create_user(db, Role.SUPER_ADMIN, "admin@example.com")
    create_user(db, Role.SUBCONTRACTOR, "sub@example.com")
    admin = auth_headers(client, "admin@example.com")
    sub = auth_headers(client, "sub@example.com")
    assert client.get(f"{API}/reports/projects", headers=sub).status_code == 200

    response = client.post(
        f"{API}/permissions/roles/subcontractor/revoke", json={"code": "reports.view"}, headers=admin
    )
    assert response.status_code == 200
    assert "reports.view" not in response.json()["permissions"]
    denied = client.get(f"{API}/reports/projects", headers=sub)
    assert denied.status_code == 403
    assert "reports.view" in denied.json()["detail"]

    client.post(
        f"{API}/permissions/roles/subcontractor/grant", json={"code": "reports.view"}, headers=admin
    )
    assert client.get(f"{API}/reports/projects", headers=sub).status_code == 200


def test_grant_rejects_unknown_role_and_code(client: TestClient, db: Session) -> None:
    """
    Unknown roles and permission codes are rejected.

    Args:
        client (TestClient): Test HTTP client.
        db (Session): Database session.
    """
    create_user(db, Role.SUPER_ADMIN, "admin@example.com")
    admin = auth_headers(client, "admin@example.com")
    bad_role = client.post(
        f"{API}/permissions/roles/plumber/grant", json={"code": "reports.view"}, headers=admin
    )
    assert bad_role.status_code in (400, 404, 422)
    bad_code = client.post(
        f"{API}/permissions/roles/subcontractor/grant", json={"code": "nope.nothing"}, headers=admin
    )
    assert bad_code.status_code in (400, 404)
