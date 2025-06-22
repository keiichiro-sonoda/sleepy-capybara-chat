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
from app.core.token import (
    set_verification_token,
    verify_token,
    set_reset_token,
    verify_reset_token,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    Token,
    UserCreate,
    User as UserSchema,
    PasswordResetRequest,
    PasswordResetConfirm,
)
from app.schemas.user import UserList
from app.schemas.email import ResendConfirmationRequest
from app.services.email import send_verification_email, send_password_reset_email

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
    """確認メールを再送信する。

    セキュリティ対策：
    - メールアドレスが存在するかどうかに関わらず、常に同じ成功メッセージを返す
    - これにより攻撃者がシステムに登録されているメールアドレスを特定できなくなる
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

    try:
        # ユーザーを削除（cascade設定により関連データも自動削除される）
        db.delete(user)
        db.commit()
        logger.info(f"User {user_id} and all related data deleted successfully")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user",
        )

    return {"message": "User deleted successfully"}


@router.delete("/me")
async def delete_me(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict[str, str]:
    try:
        # ユーザーを削除（cascade設定により関連データも自動削除される）
        db.delete(current_user)
        db.commit()
        logger.info(f"User {current_user.id} and all related data deleted successfully")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete your account",
        )

    return {"message": "Your account has been deleted successfully"}


@router.post("/users/{user_id}/active")
async def set_user_active(
    user_id: int,
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> dict[str, str]:
    """管理者が他のユーザーの有効・無効状態を切り替える"""
    is_active = request.get("is_active")
    if is_active is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="is_active field is required",
        )

    # 自分自身を無効化することを防止
    if current_user.id == user_id and not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user.is_active = is_active
    db.commit()

    logger.info(
        f"User {user_id} active status updated to {is_active} by admin {current_user.id}"
    )
    return {"message": f"User active status updated to {is_active} for user {user_id}"}


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


# ------------------------------
# パスワードリセット機能
# ------------------------------


@router.post("/password-reset/request")
async def password_reset_request(
    request: PasswordResetRequest, db: Session = Depends(get_db)
) -> dict[str, str]:
    """指定されたメールアドレス宛にパスワードリセットメールを送信する。

    セキュリティ対策：
    - メールアドレスが存在するかどうかに関わらず、常に同じ成功メッセージを返す
    - これにより攻撃者が「このメールアドレスは登録されているか？」を判別できなくなる
    - もしメールが存在しない場合に「そのメールアドレスは登録されていません」と返すと、
      攻撃者が有効なメールアドレスのリストを作成できてしまう（ユーザー列挙攻撃）
    - レート制限：同一ユーザーからの連続要求を60秒間制限
    """

    user = db.query(User).filter(User.email == request.email).first()

    if user:
        # レート制限チェック：最後のトークン生成から60秒以内は再送信を拒否
        if user.reset_token_expires_at:
            try:
                # reset_token_expires_atは1時間後なので、59分前をチェック
                expires_at = datetime.fromisoformat(user.reset_token_expires_at)
                token_generated_at = expires_at - timedelta(hours=1)
                time_since_last_token = datetime.now(timezone.utc) - token_generated_at

                if time_since_last_token < timedelta(minutes=1):
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Please wait at least 1 minute before requesting another password reset email.",
                    )
            except ValueError:
                # 無効な日付形式の場合は続行
                pass

        # トークンを生成してメール送信
        # 新しいトークンを生成すると古いトークンは自動的に無効化される
        token = set_reset_token(db, user)
        try:
            await send_password_reset_email(user.email, token)
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
            # メール送信エラー時も同一の成功メッセージを返す（セキュリティ対策）
            pass

    # 重要：メールアドレスが存在するかどうかを攻撃者に教えないため、
    # 常に同じメッセージを返す
    return {
        "message": "If your email is registered, a password reset link has been sent."
    }


@router.post("/password-reset/confirm")
async def password_reset_confirm(
    request: PasswordResetConfirm, db: Session = Depends(get_db)
) -> dict[str, str]:
    """トークンを検証し、パスワードをリセットする。"""

    user = verify_reset_token(db, request.token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    # 新しいパスワードをハッシュ化して保存
    user.hashed_password = get_password_hash(request.new_password)
    # トークンを無効化
    user.reset_token = None
    user.reset_token_expires_at = None
    db.commit()

    return {"message": "Password reset successful"}


@router.get("/password-reset/verify-token")
async def verify_password_reset_token(
    token: str, db: Session = Depends(get_db)
) -> dict[str, str]:
    """パスワードリセットトークンの有効性を検証する（パスワード変更は行わない）"""

    user = verify_reset_token(db, token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    return {"message": "Token is valid", "email": user.email}
