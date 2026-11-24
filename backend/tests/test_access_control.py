import jwt

from app.core.config import settings

PLACE = {
    "name": "Укриття №1",
    "type": "shelter",
    "address": "вул. Руська, 10",
    "capacity": 100,
    "lat": 48.2915,
    "lon": 25.9403,
}

PROTECTED = [
    ("get", "/auth/me"),
    ("get", "/home/user"),
    ("get", "/home/admin"),
    ("get", "/admin/users"),
    ("post", "/places"),
    ("post", "/places/1/reports"),
    ("patch", "/reports/1"),
    ("patch", "/users/1"),
]

ADMIN_ONLY = [
    ("get", "/home/admin", None),
    ("get", "/admin/users", None),
    ("patch", "/admin/users/1/role", {"role": "admin"}),
    ("post", "/places", PLACE),
    ("patch", "/places/1", {"name": "X"}),
    ("delete", "/places/1", None),
]


# ---------- Анонімний доступ: 401 ----------


def test_anonymous_gets_401_on_protected_routes(client):
    for method, url in PROTECTED:
        response = getattr(client, method)(url)
        assert response.status_code == 401, f"{method.upper()} {url}"
        assert response.headers["www-authenticate"] == "Bearer"


def test_invalid_token_gets_401(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401


def test_token_signed_with_wrong_key_gets_401(client, user_a):
    forged = jwt.encode(
        {"sub": str(user_a["id"])},
        "another-secret-key-that-is-long-enough-32b",
        algorithm=settings.algorithm,
    )
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_public_routes_do_not_require_login(client):
    assert client.get("/health").status_code == 200
    response = client.get("/places/nearby", params={"lat": 48.29, "lon": 25.94})
    assert response.status_code == 200


# ---------- Вертикальне розмежування ролей: 403 ----------


def test_regular_user_gets_403_on_admin_routes(client, user_a, auth_headers):
    headers = auth_headers(user_a["email"])
    for method, url, body in ADMIN_ONLY:
        response = client.request(method.upper(), url, headers=headers, json=body)
        assert response.status_code == 403, f"{method.upper()} {url}"


def test_admin_can_use_admin_routes(client, admin, auth_headers):
    headers = auth_headers(admin["email"])
    assert client.get("/admin/users", headers=headers).status_code == 200
    assert client.get("/home/admin", headers=headers).status_code == 200
    created = client.post("/places", headers=headers, json=PLACE)
    assert created.status_code == 201


def test_admin_can_change_user_role(client, user_a, admin, auth_headers):
    headers = auth_headers(admin["email"])
    response = client.patch(
        f"/admin/users/{user_a['id']}/role", headers=headers, json={"role": "admin"}
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


# ---------- Горизонтальне розмежування (IDOR): 403 ----------


def test_user_cannot_edit_another_users_profile(client, user_a, user_b, auth_headers):
    response = client.patch(
        f"/users/{user_a['id']}",
        headers=auth_headers(user_b["email"]),
        json={"full_name": "Hacked"},
    )
    assert response.status_code == 403


def test_user_can_edit_own_profile(client, user_a, auth_headers):
    response = client.patch(
        f"/users/{user_a['id']}",
        headers=auth_headers(user_a["email"]),
        json={"full_name": "Alice Updated"},
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Alice Updated"


def test_admin_can_edit_any_profile(client, user_a, admin, auth_headers):
    response = client.patch(
        f"/users/{user_a['id']}",
        headers=auth_headers(admin["email"]),
        json={"full_name": "Set By Admin"},
    )
    assert response.status_code == 200


def _report_by_alice(client, make_place, auth_headers, user_a):
    place_id = make_place("Укриття", 48.29, 25.94)
    response = client.post(
        f"/places/{place_id}/reports",
        headers=auth_headers(user_a["email"]),
        json={"text": "Тут відчинено"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_user_cannot_edit_or_delete_foreign_report(
    client, make_place, user_a, user_b, auth_headers
):
    report_id = _report_by_alice(client, make_place, auth_headers, user_a)
    bob = auth_headers(user_b["email"])

    edit = client.patch(f"/reports/{report_id}", headers=bob, json={"text": "fake"})
    delete = client.delete(f"/reports/{report_id}", headers=bob)
    assert edit.status_code == 403
    assert delete.status_code == 403


def test_author_and_admin_can_manage_report(
    client, make_place, user_a, admin, auth_headers
):
    report_id = _report_by_alice(client, make_place, auth_headers, user_a)

    own = client.patch(
        f"/reports/{report_id}",
        headers=auth_headers(user_a["email"]),
        json={"text": "Оновлено автором"},
    )
    assert own.status_code == 200
    assert own.json()["text"] == "Оновлено автором"

    removed = client.delete(
        f"/reports/{report_id}", headers=auth_headers(admin["email"])
    )
    assert removed.status_code == 204
