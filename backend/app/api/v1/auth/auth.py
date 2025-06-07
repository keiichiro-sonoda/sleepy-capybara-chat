from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

from app.core.config import get_settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
)
from app.core.deps import get_current_active_admin
from app.core.token import set_verification_token, verify_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import Token, UserCreate, User as UserSchema
from app.schemas.user import UserList
from app.schemas.email import ResendConfirmationRequest
from app.services.email import send_verification_email

router = APIRouter()
settings = get_settings()


@router.post("/register", response_model=UserSchema)
async def register(user: UserCreate, db: Session = Depends(get_db)) -> User:
    # 既存ユーザーチェック
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        if db_user.is_verified:
            # 既に確認済みのユーザーの場合はエラー
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        else:
            # 未確認のユーザーの場合は、確認メールを再送信
            try:
                # パスワードも更新する（ユーザーが忘れている可能性があるため）
                db_user.hashed_password = get_password_hash(user.password)

                # 新しい確認トークンを生成
                token = set_verification_token(db, db_user)

                # 確認メール送信
                await send_verification_email(user.email, token)

                db.commit()

                return db_user

            except Exception as e:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"User registration failed: {str(e)}",
                )

    try:
        # 新規ユーザー作成
        # トランザクション開始
        # ユーザー作成（is_verified=False）
        hashed_password = get_password_hash(user.password)
        db_user = User(
            email=user.email, hashed_password=hashed_password, is_verified=False
        )
        db.add(db_user)
        db.flush()  # コミットせずにDBに反映（IDを取得するため）

        # 確認トークン生成・保存
        token = set_verification_token(db, db_user)

        # 確認メール送信
        await send_verification_email(user.email, token)

        # すべて成功したらコミット
        db.commit()

        return db_user

    except Exception as e:
        # エラーが発生した場合はロールバック
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User registration failed: {str(e)}",
        )


@router.post("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)) -> dict[str, str]:
    user = verify_token(db, token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    # ユーザー確認状態を更新
    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires_at = None
    db.commit()

    return {"message": "Email verified successfully"}


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> Token:
    # ユーザー検証
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # メール確認チェック
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@router.post("/resend-confirmation")
async def resend_confirmation(
    request: ResendConfirmationRequest, db: Session = Depends(get_db)
) -> dict[str, str]:
    """
    Resend confirmation email to users who have an expired token or did not receive the original email.
    Returns a success message regardless of whether the email exists for security reasons.
    """
    user = db.query(User).filter(User.email == request.email).first()

    if user and not user.is_verified:
        # レート制限チェック：最後のトークン生成から60秒以内は再送信を拒否
        if user.verification_token_expires_at:
            # verification_token_expires_atは24時間後なので、23時間前（1時間前のつもり）をチェック
            # 実際には最後のトークン生成時刻を別途保存するか、より短い間隔でチェックする
            time_since_last_token = datetime.now(timezone.utc) - (
                user.verification_token_expires_at - timedelta(hours=24)
            )
            if time_since_last_token < timedelta(minutes=1):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Please wait at least 1 minute before requesting another confirmation email.",
                )

        try:
            token = set_verification_token(db, user)

            await send_verification_email(user.email, token)

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to resend confirmation email: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to resend confirmation email",
            )

    return {
        "message": "If your email is registered and not verified, a new confirmation email has been sent."
    }


# パスワードリセット関連エンドポイントも追加


@router.get("/me", response_model=UserSchema)
async def read_users_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    # 自分自身の削除または管理者による削除を許可
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}


@router.delete("/me")
async def delete_me(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict[str, str]:
    db.delete(current_user)
    db.commit()

    return {"message": "Your account has been deleted successfully"}


@router.post("/users/{user_id}/admin")
async def set_admin(
    user_id: int,
    is_admin: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> dict[str, str]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user.is_admin = is_admin
    db.commit()

    return {"message": f"Admin status updated to {is_admin} for user {user_id}"}


@router.get("/users", response_model=list[UserList])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> list[User]:
    """
    管理者用ユーザー一覧取得API
    - 管理者のみがアクセス可能
    - ページネーション対応
    - 機密情報（パスワードハッシュなど）は除外
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users
