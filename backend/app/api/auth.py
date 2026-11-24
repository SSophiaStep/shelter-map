from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.core.security import (
    DUMMY_HASH,
    create_access_token,
    hash_password_async,
    verify_password_async,
)
from app.models import User, UserRole
from app.schemas.user import Token, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, session: DbSession):
    """Публічна реєстрація. Роль завжди USER: адміна через API створити не можна."""
    email = data.email.lower()
    if await session.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(
        email=email,
        full_name=data.full_name,
        hashed_password=await hash_password_async(data.password),
        role=UserRole.USER,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Email already registered"
        ) from None
    await session.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], session: DbSession
):
    user = await session.scalar(select(User).where(User.email == form.username.lower()))
    # Хеш перевіряємо завжди, навіть коли користувача немає (однаковий час відповіді)
    password_ok = await verify_password_async(
        form.password, user.hashed_password if user else DUMMY_HASH
    )
    if user is None or not password_ok or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser):
    return user
