from app.models import PlaceType

# Чернівці, центр
LAT, LON = 48.2915, 25.9403


def _names(response):
    return [item["name"] for item in response.json()]


def test_nearby_returns_closest_first_and_skips_far_places(client, make_place):
    make_place("Далеке", 48.2915, 25.9703)  # ~2.2 км
    make_place("Найближче", 48.2916, 25.9404)
    make_place("Трохи далі", 48.2950, 25.9403)
    make_place("Інше місто", 50.4501, 30.5234)  # Київ

    response = client.get(
        "/places/nearby", params={"lat": LAT, "lon": LON, "radius_m": 5000}
    )
    assert response.status_code == 200
    assert _names(response) == ["Найближче", "Трохи далі", "Далеке"]
    distances = [item["distance_m"] for item in response.json()]
    assert distances == sorted(distances)
    assert response.json()[0]["lat"] == 48.2916


def test_nearby_filters_by_type_and_availability(client, make_place):
    make_place("Укриття", 48.2916, 25.9404, PlaceType.SHELTER)
    make_place("Пункт обігріву", 48.2917, 25.9405, PlaceType.HEATING)
    make_place("Зачинене", 48.2918, 25.9406, is_available=False)

    base = {"lat": LAT, "lon": LON}
    heating = client.get("/places/nearby", params={**base, "type": "heating"})
    assert _names(heating) == ["Пункт обігріву"]

    available = client.get("/places/nearby", params=base)
    assert "Зачинене" not in _names(available)

    everything = client.get("/places/nearby", params={**base, "only_available": False})
    assert "Зачинене" in _names(everything)


def test_nearby_validates_coordinates(client):
    assert (
        client.get("/places/nearby", params={"lat": 100, "lon": 0}).status_code == 422
    )
    assert client.get("/places/nearby").status_code == 422


def test_admin_place_crud(client, admin, auth_headers):
    headers = auth_headers(admin["email"])
    payload = {
        "name": "Метро-укриття",
        "type": "shelter",
        "address": "вул. Головна, 1",
        "capacity": 300,
        "lat": LAT,
        "lon": LON,
    }
    created = client.post("/places", headers=headers, json=payload)
    assert created.status_code == 201
    place = created.json()
    assert place["lat"] == LAT and place["lon"] == LON

    updated = client.patch(
        f"/places/{place['id']}",
        headers=headers,
        json={"capacity": 500, "is_available": False},
    )
    assert updated.status_code == 200
    assert updated.json()["capacity"] == 500
    assert updated.json()["is_available"] is False

    assert client.get(f"/places/{place['id']}").status_code == 200
    assert client.delete(f"/places/{place['id']}", headers=headers).status_code == 204
    assert client.get(f"/places/{place['id']}").status_code == 404


def test_update_requires_both_coordinates(client, admin, make_place, auth_headers):
    place_id = make_place("Укриття", LAT, LON)
    response = client.patch(
        f"/places/{place_id}",
        headers=auth_headers(admin["email"]),
        json={"lat": 48.0},
    )
    assert response.status_code == 422


def test_reports_are_public_to_read_and_tied_to_place(
    client, make_place, user_a, auth_headers
):
    place_id = make_place("Укриття", LAT, LON)
    headers = auth_headers(user_a["email"])
    created = client.post(
        f"/places/{place_id}/reports", headers=headers, json={"text": "Переповнено"}
    )
    assert created.status_code == 201
    assert created.json()["author_id"] == user_a["id"]

    listing = client.get(f"/places/{place_id}/reports")
    assert listing.status_code == 200
    assert [r["text"] for r in listing.json()] == ["Переповнено"]


def test_report_for_missing_place_is_404(client, user_a, auth_headers):
    response = client.post(
        "/places/9999/reports",
        headers=auth_headers(user_a["email"]),
        json={"text": "x"},
    )
    assert response.status_code == 404
