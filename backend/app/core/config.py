import os
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

BASE_DIR = Path(__file__).resolve().parents[2]  # папка backend/

# Яке середовище запускаємо: sandbox (за замовчуванням) або production.
# Налаштування читаються з .env, а потім перекриваються файлом .env.<APP_ENV>.
# Змінні оточення процесу (наприклад, у Docker) мають найвищий пріоритет.
APP_ENV = os.getenv("APP_ENV", "sandbox")

MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    app_name: str = "Shelter Map"
    app_env: Literal["sandbox", "production"] = "sandbox"
    debug: bool = False
    sql_echo: bool = False

    database_url: str
    db_pool_size: int = 10
    db_max_overflow: int = 10
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    password_hash_concurrency: int = 4

    cache_enabled: bool = False
    cache_ttl_seconds: int = 60
    cache_grid_decimals: int = 3

    metrics_enabled: bool = True

    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env", BASE_DIR / f".env.{APP_ENV}"),
        extra="ignore",
    )

    @model_validator(mode="after")
    def _enforce_environment_rules(self) -> "Settings":
        db_name = make_url(self.database_url).database or ""
        if self.app_env == "production":
            # Режим налагодження у production вимкнений завжди
            self.debug = False
            if (
                len(self.secret_key) < MIN_SECRET_LENGTH
                or "change-me" in self.secret_key
            ):
                raise ValueError(
                    "SECRET_KEY у production має бути випадковим рядком "
                    f"від {MIN_SECRET_LENGTH} символів"
                )
            if "sandbox" in db_name:
                raise ValueError("production не може працювати з sandbox-базою")
        elif "production" in db_name:
            raise ValueError("sandbox не може працювати з production-базою")
        return self


settings = Settings()
