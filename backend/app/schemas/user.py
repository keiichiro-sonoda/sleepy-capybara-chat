from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict


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

    model_config = ConfigDict(from_attributes=True)


# Userスキーマを追加 (UserListと同じ内容)
class User(UserList):
    pass
