import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def boom_route():
    async def boom():
        raise RuntimeError("secret internal detail")

    app.add_api_route("/__boom", boom)
    yield
    app.router.routes.pop()


def test_unhandled_error_hides_stacktrace(boom_route):
    # raise_server_exceptions=False: дивимось на відповідь так, як її бачить клієнт
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/__boom")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "Traceback" not in response.text
    assert "secret internal detail" not in response.text


def test_every_response_names_the_serving_instance(client):
    response = client.get("/live")
    assert response.status_code == 200
    assert response.headers["x-served-by"]
    assert response.json()["instance"] == response.headers["x-served-by"]


def test_health_reports_environment(client):
    body = client.get("/health").json()
    assert body["db"] == "connected"
    assert body["env"] in {"sandbox", "production"}


def test_metrics_endpoint_exposes_request_counters(client):
    client.get("/live")
    text = client.get("/metrics").text
    assert "http_requests_total" in text
    assert "http_request_duration_seconds" in text
