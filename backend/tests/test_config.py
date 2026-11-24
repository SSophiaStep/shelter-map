import pytest
from dotenv import dotenv_values
from pydantic import ValidationError

from app.core.config import BASE_DIR, Settings

STRONG_KEY = "k" * 40
SANDBOX_DB = "postgresql+asyncpg://u:p@localhost:5432/shelter_sandbox"
PRODUCTION_DB = "postgresql+asyncpg://u:p@localhost:5432/shelter_production"


def make_settings(**overrides) -> Settings:
    values = {
        "database_url": SANDBOX_DB,
        "secret_key": STRONG_KEY,
        "app_env": "sandbox",
        **overrides,
    }
    return Settings(_env_file=None, **values)


def test_sandbox_allows_debug():
    assert make_settings(debug=True).debug is True


def test_production_always_disables_debug():
    cfg = make_settings(app_env="production", database_url=PRODUCTION_DB, debug=True)
    assert cfg.debug is False


def test_production_rejects_weak_secret_key():
    with pytest.raises(ValidationError):
        make_settings(
            app_env="production", database_url=PRODUCTION_DB, secret_key="short"
        )
    with pytest.raises(ValidationError):
        make_settings(
            app_env="production",
            database_url=PRODUCTION_DB,
            secret_key="change-me-" + "x" * 40,
        )


def test_environments_cannot_use_each_others_database():
    with pytest.raises(ValidationError):
        make_settings(app_env="production", database_url=SANDBOX_DB)
    with pytest.raises(ValidationError):
        make_settings(app_env="sandbox", database_url=PRODUCTION_DB)


def test_env_templates_use_separate_databases_and_safe_modes():
    sandbox = dotenv_values(BASE_DIR / ".env.sandbox.example")
    production = dotenv_values(BASE_DIR / ".env.production.example")
    assert sandbox["DATABASE_URL"] != production["DATABASE_URL"]
    assert sandbox["SECRET_KEY"] != production["SECRET_KEY"]
    assert production["DEBUG"].lower() == "false"
    assert production["APP_ENV"] == "production"
    assert sandbox["APP_ENV"] == "sandbox"
