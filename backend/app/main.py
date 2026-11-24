import logging

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text

from app.api import admin, auth, pages, places, reports, users
from app.api.deps import DbSession
from app.core.config import settings
from app.core.middleware import INSTANCE_ID, MetricsMiddleware, ServedByMiddleware

logger = logging.getLogger("app")

# DEBUG вимкнений у production (див. Settings): детальні помилки лише в sandbox
app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(ServedByMiddleware)
if settings.metrics_enabled:
    app.add_middleware(MetricsMiddleware)

app.include_router(auth.router)
app.include_router(pages.router)
app.include_router(admin.router)
app.include_router(users.router)
app.include_router(places.router)
app.include_router(reports.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    """Користувач бачить лише загальне повідомлення, стектрейс іде в лог."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/live", tags=["system"])
async def live() -> dict:
    """Легка перевірка процесу (без БД): для healthcheck контейнера й Nginx."""
    return {"status": "ok", "instance": INSTANCE_ID}


@app.get("/health", tags=["system"])
async def health(session: DbSession) -> dict:
    await session.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "db": "connected",
        "env": settings.app_env,
        "instance": INSTANCE_ID,
    }


if settings.metrics_enabled:

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
# hello
