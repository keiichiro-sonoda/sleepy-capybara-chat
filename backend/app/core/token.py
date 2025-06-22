import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.user import User


def generate_verification_token() -> str:
    return secrets.token_urlsafe(32)


def set_verification_token(db: Session, user: User) -> str:
    token = generate_verification_token()
    expires = datetime.now(timezone.utc) + timedelta(days=1)

    user.verification_token = token
    user.verification_token_expires_at = expires
    db.commit()

    return token


def verify_token(db: Session, token: str) -> User | None:
    user = (
        db.query(User)
        .filter(
            User.verification_token == token,
            User.verification_token_expires_at > datetime.now(timezone.utc),
        )
        .first()
    )

    return user


# パスワードリセットトークン関連のユーティリティ


def generate_reset_token() -> str:
    """Generates a secure random token for password reset"""
    return secrets.token_urlsafe(32)


def set_reset_token(db: Session, user: User, hours: int = 1) -> str:
    """Generate a password reset token, persist it on the user record and return it.

    The token is valid for the specified number of `hours` (default: 1 hour).
    """
    from datetime import timezone  # 遅延インポートで循環参照を防止

    token = generate_reset_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)

    # `reset_token_expires_at` は文字列カラムとして定義されているため ISO 形式で保存する
    user.reset_token = token
    user.reset_token_expires_at = expires_at.isoformat()
    db.commit()

    return token


def verify_reset_token(db: Session, token: str) -> User | None:
    """Verify that the given reset token exists and has not expired.

    Returns the associated `User` instance if the token is valid, otherwise `None`.
    """
    user = db.query(User).filter(User.reset_token == token).first()
    if not user or not user.reset_token_expires_at:
        return None

    try:
        expires_at = datetime.fromisoformat(user.reset_token_expires_at)
    except ValueError:
        # 無効な日付形式
        return None

    if expires_at <= datetime.now(timezone.utc):
        # トークンが期限切れ
        return None

    return user
