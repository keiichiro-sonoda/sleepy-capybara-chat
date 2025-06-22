from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.models.user import User


def seed_admin_user(db: Session) -> None:
    """
    初期管理者ユーザーを作成するシード関数
    """
    settings = get_settings()
    admin_email = settings.ADMIN_EMAIL
    admin_password = settings.ADMIN_PASSWORD

    # 既存の管理者ユーザーが存在するか確認
    existing_admin = db.query(User).filter(User.email == admin_email).first()
    if existing_admin:
        print(f"Admin user {admin_email} already exists")
        return

    # 管理者ユーザーを作成
    admin_user = User(
        email=admin_email,
        hashed_password=get_password_hash(admin_password),
        is_admin=True,
        is_verified=True,  # 管理者は自動的にメール確認済みとする
        is_active=True,
    )
    db.add(admin_user)
    db.commit()
    print(f"Admin user {admin_email} created successfully")
