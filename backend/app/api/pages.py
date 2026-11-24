from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, require_roles
from app.models import UserRole

router = APIRouter(prefix="/home", tags=["home pages"])


@router.get("/user")
async def user_home(user: CurrentUser):
    """Домашня сторінка-заглушка для будь-якого авторизованого користувача."""
    return {
        "page": "user_home",
        "message": f"Вітаємо, {user.full_name}! Тут буде персональна мапа укриттів.",
        "role": user.role,
    }


@router.get("/admin", dependencies=[Depends(require_roles(UserRole.ADMIN))])
async def admin_home(user: CurrentUser):
    """Домашня сторінка-заглушка адміністратора."""
    return {
        "page": "admin_home",
        "message": f"Панель адміністратора. Вітаємо, {user.full_name}!",
        "role": user.role,
    }
