"""Tests for registration, login, tokens and passwords."""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.constants.roles import Role
from app.services import auth_service
from tests.conftest import API, PASSWORD, auth_headers, create_user


def register_body(email: str, role: str) -> dict:
    """
    A valid registration body.

    Args:
        email (str): Email address to register with.
        role (str): Role value to register as.

    Returns:
        dict: Registration request body.
    """
    return {
        "first_name": "Amina",
        "last_name": "Otieno",
        "email": email,
        "phone_number": "254712345678",
        "role": role,
        "password": PASSWORD,
        "re_enter_password": PASSWORD,
    }


def test_register_and_login_returns_tokens_and_permissions(client: TestClient) -> None:
    """
    A new subcontractor can register, log in and gets their permission codes.

    Args:
        client (TestClient): Test HTTP client.
    """
    response = client.post(f"{API}/auth/register", json=register_body("a@example.com", "subcontractor"))
    assert response.status_code == 201, response.text
    assert "hashed_password" not in response.json()

    response = client.post(f"{API}/auth/login", json={"email": "a@example.com", "password": PASSWORD})
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["role"] == "subcontractor"
    assert "works.create" in body["permissions"]
    assert "projects.create" not in body["permissions"]


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    """
    Emails are unique.

    Args:
        client (TestClient): Test HTTP client.
    """
    client.post(f"{API}/auth/register", json=register_body("a@example.com", "subcontractor"))
    response = client.post(f"{API}/auth/register", json=register_body("A@example.com", "subcontractor"))
    assert response.status_code == 400


def test_register_blocks_super_admin(client: TestClient) -> None:
    """
    Super admins can only be created with the CLI script.

    Args:
        client (TestClient): Test HTTP client.
    """
    response = client.post(f"{API}/auth/register", json=register_body("x@example.com", "super-admin"))
    assert response.status_code == 400


def test_main_contractor_registration_limited_to_configured_emails(client: TestClient) -> None:
    """
    Only MAIN_CONTRACTOR_EMAILS may register as main contractor.

    Args:
        client (TestClient): Test HTTP client.
    """
    response = client.post(f"{API}/auth/register", json=register_body("x@example.com", "main-contractor"))
    assert response.status_code == 400
    response = client.post(
        f"{API}/auth/register", json=register_body("owner@example.com", "main-contractor")
    )
    assert response.status_code == 201


def test_register_validates_password_match(client: TestClient) -> None:
    """
    Both passwords must match.

    Args:
        client (TestClient): Test HTTP client.
    """
    body = register_body("a@example.com", "subcontractor")
    body["re_enter_password"] = "Different123"
    assert client.post(f"{API}/auth/register", json=body).status_code == 422


def test_login_with_wrong_password(client: TestClient, db: Session) -> None:
    """
    Wrong credentials give 401.

    Args:
        client (TestClient): Test HTTP client.
        db (Session): Database session.
    """
    create_user(db, Role.SUBCONTRACTOR, "a@example.com")
    response = client.post(f"{API}/auth/login", json={"email": "a@example.com", "password": "wrong-pass"})
    assert response.status_code == 401


def test_protected_endpoint_requires_token(client: TestClient) -> None:
    """
    No token, no access.

    Args:
        client (TestClient): Test HTTP client.
    """
    assert client.get(f"{API}/auth/me").status_code == 401


def test_refresh_rotates_token_and_logout_revokes(client: TestClient, db: Session) -> None:
    """
    A refresh token works once; after logout it cannot be used.

    Args:
        client (TestClient): Test HTTP client.
        db (Session): Database session.
    """
    create_user(db, Role.SUBCONTRACTOR, "a@example.com")
    login = client.post(f"{API}/auth/login", json={"email": "a@example.com", "password": PASSWORD})
    old_refresh = login.json()["refresh_token"]

    response = client.post(f"{API}/auth/refresh", json={"refresh_token": old_refresh})
    assert response.status_code == 200
    new_refresh = response.json()["refresh_token"]
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": old_refresh}).status_code == 401

    assert client.post(f"{API}/auth/logout", json={"refresh_token": new_refresh}).status_code == 200
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": new_refresh}).status_code == 401


def test_forgot_password_does_not_reveal_accounts(client: TestClient, db: Session) -> None:
    """
    Known and unknown emails get the same response.

    Args:
        client (TestClient): Test HTTP client.
        db (Session): Database session.
    """
    create_user(db, Role.SUBCONTRACTOR, "a@example.com")
    known = client.post(f"{API}/auth/forgot-password", json={"email": "a@example.com"})
    unknown = client.post(f"{API}/auth/forgot-password", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()


def test_reset_password_with_token(client: TestClient, db: Session) -> None:
    """
    A valid reset token sets a new password and cannot be reused.

    Args:
        client (TestClient): Test HTTP client.
        db (Session): Database session.
    """
    user = create_user(db, Role.SUBCONTRACTOR, "a@example.com")
    _, token = auth_service.create_password_reset(db, "a@example.com")
    body = {
        "user_id": str(user.id),
        "token": token,
        "new_password": "NewPassword1",
        "re_enter_password": "NewPassword1",
    }
    login = client.post(f"{API}/auth/login", json={"email": "a@example.com", "password": PASSWORD})
    old_tokens = login.json()

    assert client.post(f"{API}/auth/reset-password", json=body).status_code == 200
    assert client.post(f"{API}/auth/reset-password", json=body).status_code == 400
    response = client.post(
        f"{API}/auth/login", json={"email": "a@example.com", "password": "NewPassword1"}
    )
    assert response.status_code == 200

    # Anyone still logged in with the old password is logged out
    old_headers = {"Authorization": f"Bearer {old_tokens['access_token']}"}
    assert client.get(f"{API}/users/me", headers=old_headers).status_code == 401
    refresh = client.post(f"{API}/auth/refresh", json={"refresh_token": old_tokens["refresh_token"]})
    assert refresh.status_code == 401


def test_change_password(client: TestClient, db: Session) -> None:
    """
    The current password must be correct; old tokens stop working, new ones are returned.

    Args:
        client (TestClient): Test HTTP client.
        db (Session): Database session.
    """
    create_user(db, Role.SUBCONTRACTOR, "a@example.com")
    login = client.post(f"{API}/auth/login", json={"email": "a@example.com", "password": PASSWORD})
    old_refresh = login.json()["refresh_token"]
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    wrong = {"current_password": "wrong-pass", "new_password": "NewPassword1",
             "re_enter_password": "NewPassword1"}
    assert client.post(f"{API}/auth/change-password", json=wrong, headers=headers).status_code == 400
    right = dict(wrong, current_password=PASSWORD)
    response = client.post(f"{API}/auth/change-password", json=right, headers=headers)
    assert response.status_code == 200
    new_tokens = response.json()

    assert client.get(f"{API}/users/me", headers=headers).status_code == 401
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": old_refresh}).status_code == 401

    new_headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
    assert client.get(f"{API}/users/me", headers=new_headers).status_code == 200
    refresh = client.post(f"{API}/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]})
    assert refresh.status_code == 200


def test_profile_and_user_list(client: TestClient, db: Session) -> None:
    """
    Users can read and edit their profile; only some roles may list all users.

    Args:
        client (TestClient): Test HTTP client.
        db (Session): Database session.
    """
    create_user(db, Role.MAIN_CONTRACTOR, "owner@example.com")
    create_user(db, Role.SUBCONTRACTOR, "a@example.com")
    owner = auth_headers(client, "owner@example.com")
    sub = auth_headers(client, "a@example.com")

    response = client.patch(f"{API}/users/me", json={"first_name": "Wanjiru"}, headers=sub)
    assert response.status_code == 200
    assert client.get(f"{API}/users/me", headers=sub).json()["first_name"] == "Wanjiru"
    escalate = client.patch(f"{API}/users/me", json={"role": "main-contractor"}, headers=sub)
    assert escalate.status_code == 400

    assert client.get(f"{API}/users", headers=sub).status_code == 403
    subs = client.get(f"{API}/users", params={"role": "subcontractor"}, headers=owner).json()
    assert [user["email"] for user in subs] == ["a@example.com"]


def test_choices_are_public(client: TestClient) -> None:
    """
    Dropdown choices can be read without logging in and never offer super admin.

    Args:
        client (TestClient): Test HTTP client.
    """
    response = client.get(f"{API}/metadata/choices")
    assert response.status_code == 200
    body = response.json()
    assert body["labourer_titles"] and body["task_categories"]
    roles = [item["value"] for item in body["roles"]]
    assert Role.SUBCONTRACTOR.value in roles
    assert Role.SUPER_ADMIN.value not in roles
