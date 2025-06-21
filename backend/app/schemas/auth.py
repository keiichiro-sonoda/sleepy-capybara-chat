from pydantic import BaseModel, EmailStr
from pydantic.config import ConfigDict


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    is_verified: bool
    model_config = ConfigDict(from_attributes=True)


# ------------------------------
# パスワードリセット関連スキーマ
# ------------------------------


class PasswordResetRequest(BaseModel):
    """メールアドレスを受け取り、パスワードリセットメールを送信するリクエストスキーマ"""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """パスワードリセットトークンと新しいパスワードを受け取るスキーマ"""

    token: str
    new_password: str
