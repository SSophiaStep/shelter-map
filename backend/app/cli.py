"""Створення адміністратора (через API це робити не можна).

Запуск з папки backend:
    python -m app.cli admin@example.com StrongPass123 --name "Admin"
"""

import argparse
import asyncio

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal, engine
from app.models import User, UserRole


async def create_admin(email: str, password: str, full_name: str) -> str:
    email = email.lower()
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == email))
        if user is None:
            session.add(
                User(
                    email=email,
                    full_name=full_name,
                    hashed_password=hash_password(password),
                    role=UserRole.ADMIN,
                )
            )
            result = "created"
        else:
            user.role = UserRole.ADMIN
            result = "promoted"
        await session.commit()
    await engine.dispose()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or promote an admin user")
    parser.add_argument("email")
    parser.add_argument("password")
    parser.add_argument("--name", default="Administrator")
    args = parser.parse_args()
    result = asyncio.run(create_admin(args.email, args.password, args.name))
    print(f"Admin {result}: {args.email.lower()}")


if __name__ == "__main__":
    main()
