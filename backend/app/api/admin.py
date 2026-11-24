from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import AdminUser, DbSession
from app.models import User
from app.schemas.user import RoleUpdate, UserRead

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserRead])
async def list_users(_admin: AdminUser, session: DbSession):
    result = await session.scalars(select(User).order_by(User.id))
    return list(result)


@router.patch("/users/{user_id}/role", response_model=UserRead)
async def set_role(
    user_id: int, data: RoleUpdate, _admin: AdminUser, session: DbSession
):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.role = data.role
    await session.commit()
    return user
