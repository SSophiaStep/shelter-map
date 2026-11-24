from datetime import UTC, datetime, timedelta

import anyio
import jwt
from anyio import to_thread
from pwdlib import PasswordHash

from app.core.config import settings

# Argon2id: сучасний стандарт зберігання паролів (сіль і параметри всередині хешу)
_password_hash = PasswordHash.recommended()

# Хеш-заглушка: перевіряємо її, коли користувача не знайдено, щоб час відповіді
# не показував, чи існує такий email (захист від user enumeration).
DUMMY_HASH = _password_hash.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return _password_hash.verify(password, hashed_password)


_hash_limiter: anyio.CapacityLimiter | None = None


def _limiter() -> anyio.CapacityLimiter:
    """Обмежує кількість одночасних Argon2-обчислень (CPU і ~64 МБ пам'яті кожне)."""
    global _hash_limiter
    if _hash_limiter is None:
        _hash_limiter = anyio.CapacityLimiter(settings.password_hash_concurrency)
    return _hash_limiter


async def hash_password_async(password: str) -> str:
    """Argon2 у пулі потоків: event loop залишається вільним для інших запитів."""
    return await to_thread.run_sync(hash_password, password, limiter=_limiter())


async def verify_password_async(password: str, hashed_password: str) -> bool:
    return await to_thread.run_sync(
        verify_password, password, hashed_password, limiter=_limiter()
    )


def create_access_token(user_id: int, expires_minutes: int | None = None) -> str:
    minutes = (
        settings.access_token_expire_minutes
        if expires_minutes is None
        else expires_minutes
    )
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(UTC) + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> int | None:
    """Повертає id користувача або None, якщо токен недійсний чи прострочений."""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None
