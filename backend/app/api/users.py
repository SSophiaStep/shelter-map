from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.models import User, UserRole
from app.schemas.user import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/{user_id}", response_model=UserRead)
async def update_profile(
    user_id: int, data: UserUpdate, current: CurrentUser, session: DbSession
):
    """Змінювати профіль може лише власник або адмін (захист від IDOR)."""
    if current.id != user_id and current.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your profile")
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.full_name = data.full_name
    await session.commit()
    return user
