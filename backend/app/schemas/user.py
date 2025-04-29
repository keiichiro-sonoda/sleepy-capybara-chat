from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    is_active: bool
    is_admin: bool
    is_verified: bool
    created_at: datetime


class UserList(UserBase):
    id: int

    class Config:
        from_attributes = True


# Userスキーマを追加 (UserListと同じ内容)
class User(UserList):
    pass
