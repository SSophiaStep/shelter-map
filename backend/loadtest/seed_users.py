"""Створює тестових користувачів для навантажувального тесту.

Запуск з папки backend:  python loadtest/seed_users.py
Усі користувачі мають пароль LoadTest123 (хеш обчислюється один раз).
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.models import User, UserRole  # noqa: E402

COUNT = 100
PASSWORD = "LoadTest123"


async def main() -> None:
    hashed = hash_password(PASSWORD)
    async with SessionLocal() as session:
        existing = set(await session.scalars(select(User.email)))
        new = [
            User(
                email=f"load{i}@example.com",
                full_name=f"Load User {i}",
                hashed_password=hashed,
                role=UserRole.USER,
            )
            for i in range(COUNT)
            if f"load{i}@example.com" not in existing
        ]
        session.add_all(new)
        await session.commit()
    await engine.dispose()
    print(f"created {len(new)} users (total target {COUNT})")


if __name__ == "__main__":
    asyncio.run(main())
