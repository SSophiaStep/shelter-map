"""Кеш результатів геопошуку в Redis.

Ключ будується із округленої геосітки (за замовчуванням 3 знаки, ~110 м), тому близькі
запити потрапляють в один запис. Версія в ключі дає миттєву інвалідацію: зміна даних
збільшує лічильник версії, і старі ключі просто перестають використовуватись (їх
прибирає TTL). Якщо Redis недоступний, застосунок працює напряму з БД (fail-open).
"""

import logging

import redis.asyncio as redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger("app.cache")

VERSION_KEY = "nearby:version"
_client: redis.Redis | None = None


def get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(
            settings.redis_url, socket_connect_timeout=0.2, socket_timeout=0.2
        )
    return _client


def reset_client() -> None:
    global _client
    _client = None


def snap(value: float) -> float:
    return round(value, settings.cache_grid_decimals)


async def nearby_lookup(
    lat: float,
    lon: float,
    radius_m: int,
    place_type: str | None,
    only_available: bool,
    limit: int,
) -> tuple[str | None, bytes | None]:
    """Повертає (ключ, значення з кешу). Ключ None означає, що Redis недоступний."""
    try:
        client = get_client()
        raw = await client.get(VERSION_KEY)
        version = raw.decode() if raw else "0"
        key = (
            f"nearby:{version}:{lat}:{lon}:{radius_m}:{place_type or 'any'}:"
            f"{int(only_available)}:{limit}"
        )
        return key, await client.get(key)
    except (RedisError, OSError) as exc:
        logger.warning("cache lookup failed, falling back to DB: %s", exc)
        return None, None


async def nearby_store(key: str, payload: bytes) -> None:
    try:
        await get_client().set(key, payload, ex=settings.cache_ttl_seconds)
    except (RedisError, OSError) as exc:
        logger.warning("cache store failed: %s", exc)


async def invalidate_nearby() -> None:
    """Викликається після зміни укриттів: усі старі ключі стають недійсними."""
    try:
        await get_client().incr(VERSION_KEY)
    except (RedisError, OSError) as exc:
        logger.warning("cache invalidation failed: %s", exc)
