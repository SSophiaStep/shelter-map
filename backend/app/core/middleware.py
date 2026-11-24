import os
import socket
import time

from prometheus_client import Counter, Gauge, Histogram
from starlette.datastructures import MutableHeaders

# Унікальний ідентифікатор екземпляра: у Docker це hostname контейнера
INSTANCE_ID = os.getenv("INSTANCE_ID") or socket.gethostname()

REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
IN_FLIGHT = Gauge("http_requests_in_flight", "Requests being processed")


class ServedByMiddleware:
    """Додає заголовок X-Served-By, щоб бачити, яка репліка обробила запит."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_header(message):
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)["X-Served-By"] = INSTANCE_ID
            await send(message)

        await self.app(scope, receive, send_with_header)


class MetricsMiddleware:
    """Prometheus-метрики: лічильник запитів, затримка, кількість активних."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        status_code = 500
        start = time.perf_counter()

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        IN_FLIGHT.inc()
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            IN_FLIGHT.dec()
            route = scope.get("route")
            path = getattr(route, "path", "unmatched")
            method = scope["method"]
            if path != "/metrics":
                REQUESTS.labels(method, path, str(status_code)).inc()
                LATENCY.labels(method, path).observe(time.perf_counter() - start)
