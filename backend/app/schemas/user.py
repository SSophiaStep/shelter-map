from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool


class UserUpdate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)


class RoleUpdate(BaseModel):
    role: UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
