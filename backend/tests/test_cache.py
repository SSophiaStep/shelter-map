import pytest
import redis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core import cache as cache_module
from app.core.config import settings

LAT, LON = 48.2915, 25.9403
PARAMS = {"lat": LAT, "lon": LON, "radius_m": 2000}


def _redis_available() -> bool:
    try:
        redis.Redis.from_url(settings.redis_url, socket_connect_timeout=0.3).ping()
        return True
    except redis.RedisError:
        return False


pytestmark = pytest.mark.skipif(not _redis_available(), reason="Redis недоступний")


@pytest.fixture
def cache_on(monkeypatch):
    monkeypatch.setattr(settings, "cache_enabled", True)
    sync = redis.Redis.from_url(settings.redis_url)
    for key in sync.scan_iter("nearby:*"):
        sync.delete(key)
    yield
    for key in sync.scan_iter("nearby:*"):
        sync.delete(key)


def test_cache_disabled_by_default_has_no_cache_header(client, make_place):
    make_place("Укриття", LAT, LON)
    response = client.get("/places/nearby", params=PARAMS)
    assert response.status_code == 200
    assert "x-cache" not in response.headers


def test_second_identical_request_is_served_from_cache(client, make_place, cache_on):
    make_place("Укриття", LAT, LON)
    first = client.get("/places/nearby", params=PARAMS)
    second = client.get("/places/nearby", params=PARAMS)
    assert first.headers["x-cache"] == "MISS"
    assert second.headers["x-cache"] == "HIT"
    assert first.json() == second.json()
    assert first.json()[0]["name"] == "Укриття"


def test_nearby_coordinates_share_one_cache_entry(client, make_place, cache_on):
    make_place("Укриття", LAT, LON)
    client.get("/places/nearby", params={**PARAMS, "lat": 48.2912, "lon": 25.9402})
    second = client.get(
        "/places/nearby", params={**PARAMS, "lat": 48.2914, "lon": 25.9404}
    )
    assert second.headers["x-cache"] == "HIT"


def test_cache_is_invalidated_after_admin_changes(
    client, make_place, admin, auth_headers, cache_on
):
    place_id = make_place("Укриття", LAT, LON)
    assert client.get("/places/nearby", params=PARAMS).json()[0]["id"] == place_id

    client.patch(
        f"/places/{place_id}",
        headers=auth_headers(admin["email"]),
        json={"is_available": False},
    )
    after = client.get("/places/nearby", params=PARAMS)
    assert after.headers["x-cache"] == "MISS"
    assert after.json() == []


def test_app_keeps_working_when_redis_is_down(
    client, make_place, cache_on, monkeypatch
):
    make_place("Укриття", LAT, LON)

    def broken_client():
        raise RedisConnectionError("redis is down")

    monkeypatch.setattr(cache_module, "get_client", broken_client)
    response = client.get("/places/nearby", params=PARAMS)
    assert response.status_code == 200
    assert response.headers["x-cache"] == "BYPASS"
    assert response.json()[0]["name"] == "Укриття"
