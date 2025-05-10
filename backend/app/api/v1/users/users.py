from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.services.token_usage import TokenUsageService
from app.schemas.token_usage import TokenUsageByModel
from app.schemas.user import User

router = APIRouter()


@router.get("/me/token-usage/by-model", response_model=list[TokenUsageByModel])
async def get_my_token_usage_by_model(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TokenUsageByModel]:
    """
    自分自身のモデルごとのトークン使用量を取得する
    """
    # 上記と同様の注意点
    if not hasattr(current_user, "id"):
        raise HTTPException(
            status_code=500, detail="User object does not have an ID attribute."
        )

    usage = await TokenUsageService.get_usage_stats_by_model(
        db=db, user_id=current_user.id, days=days
    )
    return usage
