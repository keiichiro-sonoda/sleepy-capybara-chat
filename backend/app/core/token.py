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


# 同様にパスワードリセットトークン関数も実装
