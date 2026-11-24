import asyncio

import pytest
from fastapi.testclient import TestClient
from geoalchemy2.elements import WKTElement
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core import cache as cache_module
from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.models import Place, PlaceType, User, UserRole

_BASE_URL = make_url(settings.database_url)
TEST_DB_NAME = f"{_BASE_URL.database}_test"
TEST_URL = _BASE_URL.set(database=TEST_DB_NAME)

PASSWORD = "StrongPass123"


def _engine(url, **kwargs):
    # NullPool: кожне з'єднання створюється в поточному event loop
    return create_async_engine(url, poolclass=NullPool, **kwargs)


async def _prepare_database() -> None:
    admin_engine = _engine(_BASE_URL, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        exists = await conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": TEST_DB_NAME}
        )
        if not exists:
            await conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    await admin_engine.dispose()

    engine = _engine(TEST_URL)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


async def _truncate() -> None:
    engine = _engine(TEST_URL)
    async with engine.begin() as conn:
        await conn.execute(
            text("TRUNCATE reports, places, users RESTART IDENTITY CASCADE")
        )
    await engine.dispose()


async def _insert(*objects):
    engine = _engine(TEST_URL)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        session.add_all(objects)
        await session.commit()
        ids = [obj.id for obj in objects]
    await engine.dispose()
    return ids


@pytest.fixture(scope="session", autouse=True)
def _database():
    asyncio.run(_prepare_database())


@pytest.fixture(autouse=True)
def _clean_tables(_database):
    asyncio.run(_truncate())


@pytest.fixture(autouse=True)
def _fresh_cache_client():
    # Кожен TestClient має власний event loop, тож клієнт Redis створюємо наново
    cache_module.reset_client()
    yield
    cache_module.reset_client()


@pytest.fixture
def client():
    engine = _engine(TEST_URL)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def make_user():
    """Створює користувача напряму в БД (так, як це робить CLI для адміна)."""

    def _make(
        email: str, role: UserRole = UserRole.USER, full_name: str = "Test User"
    ) -> int:
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(PASSWORD),
            role=role,
        )
        return asyncio.run(_insert(user))[0]

    return _make


@pytest.fixture
def make_place():
    def _make(
        name: str,
        lat: float,
        lon: float,
        type_: PlaceType = PlaceType.SHELTER,
        is_available: bool = True,
    ) -> int:
        place = Place(
            name=name,
            type=type_,
            address="вул. Тестова, 1",
            capacity=50,
            is_available=is_available,
            location=WKTElement(f"POINT({lon} {lat})", srid=4326),
        )
        return asyncio.run(_insert(place))[0]

    return _make


@pytest.fixture
def auth_headers(client):
    def _headers(email: str, password: str = PASSWORD) -> dict[str, str]:
        response = client.post(
            "/auth/login", data={"username": email, "password": password}
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _headers


@pytest.fixture
def user_a(make_user):
    return {"id": make_user("alice@example.com"), "email": "alice@example.com"}


@pytest.fixture
def user_b(make_user):
    return {"id": make_user("bob@example.com"), "email": "bob@example.com"}


@pytest.fixture
def admin(make_user):
    return {
        "id": make_user("admin@example.com", UserRole.ADMIN, "Admin"),
        "email": "admin@example.com",
    }
