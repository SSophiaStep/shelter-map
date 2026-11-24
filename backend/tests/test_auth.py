from app.models import UserRole
from tests.conftest import PASSWORD


def _register(client, email="new@example.com", **extra):
    payload = {"email": email, "full_name": "New User", "password": PASSWORD, **extra}
    return client.post("/auth/register", json=payload)


# ---------- Реєстрація ----------


def test_register_creates_regular_user_without_leaking_password(client):
    response = _register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@example.com"
    assert body["role"] == UserRole.USER
    assert "password" not in body and "hashed_password" not in body


def test_register_cannot_escalate_to_admin(client):
    response = _register(client, role="admin", is_active=True)
    assert response.status_code == 201
    assert response.json()["role"] == "user"


def test_register_duplicate_email_is_conflict(client):
    assert _register(client).status_code == 201
    assert _register(client, email="NEW@example.com").status_code == 409


def test_register_validates_input(client):
    assert _register(client, email="not-an-email").status_code == 422
    short = client.post(
        "/auth/register",
        json={"email": "a@example.com", "full_name": "A", "password": "short"},
    )
    assert short.status_code == 422


# ---------- Успішна автентифікація та помилки входу ----------


def test_login_success_and_access_to_me(client, user_a, auth_headers):
    response = client.get("/auth/me", headers=auth_headers(user_a["email"]))
    assert response.status_code == 200
    assert response.json()["email"] == user_a["email"]


def test_login_returns_bearer_token(client, user_a):
    response = client.post(
        "/auth/login", data={"username": user_a["email"], "password": PASSWORD}
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_login_wrong_password_is_401(client, user_a):
    response = client.post(
        "/auth/login", data={"username": user_a["email"], "password": "wrong-pass-1"}
    )
    assert response.status_code == 401


def test_login_unknown_email_is_401(client):
    response = client.post(
        "/auth/login", data={"username": "ghost@example.com", "password": PASSWORD}
    )
    assert response.status_code == 401


def test_registered_user_can_login(client):
    _register(client)
    response = client.post(
        "/auth/login", data={"username": "new@example.com", "password": PASSWORD}
    )
    assert response.status_code == 200


# ---------- Домашні сторінки ----------


def test_user_and_admin_have_different_home_pages(client, user_a, admin, auth_headers):
    user_page = client.get("/home/user", headers=auth_headers(user_a["email"]))
    admin_page = client.get("/home/admin", headers=auth_headers(admin["email"]))
    assert user_page.status_code == 200
    assert user_page.json()["page"] == "user_home"
    assert admin_page.status_code == 200
    assert admin_page.json()["page"] == "admin_home"
