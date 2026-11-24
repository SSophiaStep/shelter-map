from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_session
from app.models import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

DbSession = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], session: DbSession
) -> User:
    """Автентифікація: без токена OAuth2PasswordBearer сам віддає 401."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_error
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    """Авторизація (RBAC): пропускає лише вказані ролі, інакше 403."""

    async def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return checker


AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
