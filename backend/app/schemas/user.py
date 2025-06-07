from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict
from app.schemas.token_limit import TokenLimit, TokenLimitWithModelName


class UserBase(BaseModel):
    email: EmailStr
    is_active: bool
    is_admin: bool
    is_verified: bool
    created_at: datetime


class UserList(BaseModel):
    id: int
    email: EmailStr
    is_verified: bool
    is_admin: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# Userスキーマを追加 (UserListと同じ内容)
class User(UserList):
    pass


class UserWithTokenLimits(User):
    token_limits: list[TokenLimitWithModelName] = []

    model_config = ConfigDict(from_attributes=True)
