from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.token_limit import TokenLimit as TokenLimitModel
from app.models.token_usage import TokenUsage
from app.schemas.chat import AVAILABLE_MODELS
from app.schemas.enums import PeriodUnit
from app.schemas.token_usage import TokenUsageByModel
from app.schemas.user import User
from app.services.token_usage import TokenUsageService

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


@router.get("/me/token-limits-summary")
async def get_my_token_limits_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    自分自身のトークン制限と使用量の詳細を取得する
    """
    if not hasattr(current_user, "id"):
        raise HTTPException(
            status_code=500, detail="User object does not have an ID attribute."
        )

    # ユーザー固有の制限を取得
    user_limits = (
        db.query(TokenLimitModel)
        .filter(TokenLimitModel.user_id == current_user.id)
        .all()
    )

    # 現在の時刻
    now = datetime.now(ZoneInfo("UTC"))

    # 結果を格納するリスト
    limit_summaries = []

    # 利用可能なモデルをid→modelのマップに変換
    available_models = {model.id: model for model in AVAILABLE_MODELS}

    # モデルごとに制限情報を整理
    processed_models = set()

    # ユーザー固有の制限を処理
    for limit in user_limits:
        processed_models.add(limit.model_id)

        # 期間に応じた開始時刻を計算
        start_time = now
        if limit.period_unit == PeriodUnit.MINUTE:
            start_time = now - timedelta(minutes=limit.period_value)
        elif limit.period_unit == PeriodUnit.HOUR:
            start_time = now - timedelta(hours=limit.period_value)
        elif limit.period_unit == PeriodUnit.DAY:
            start_time = now - timedelta(days=limit.period_value)
        elif limit.period_unit == PeriodUnit.MONTH:
            start_time = now - timedelta(days=limit.period_value * 30)

        # 期間内の使用量を取得
        usage = (
            db.query(func.sum(TokenUsage.effective_tokens))
            .filter(
                TokenUsage.user_id == current_user.id,
                TokenUsage.model_id == limit.model_id.value,
                TokenUsage.timestamp >= start_time,
            )
            .scalar()
        ) or 0

        # 制限情報を構築
        model = available_models.get(limit.model_id)
        model_name = model.name if model else limit.model_id.value

        limit_summaries.append(
            {
                "model_id": limit.model_id.value,
                "model_name": model_name,
                "limit_value": limit.limit_value,
                "period_unit": limit.period_unit.value,
                "period_value": limit.period_value,
                "current_usage": int(usage),
                "remaining": max(0, limit.limit_value - int(usage)),
                "usage_percentage": min(
                    100, round((usage / limit.limit_value) * 100, 1)
                ),
                "is_custom_limit": True,
                "period_description": (
                    f"{limit.period_value} {limit.period_unit.value}"
                    f"{'s' if limit.period_value > 1 else ''}"
                ),
            }
        )

    # デフォルト制限のあるモデルで、ユーザー固有の制限がないものを処理
    for model in AVAILABLE_MODELS:
        if model.id not in processed_models:
            # デフォルト制限の期間を計算
            start_time = now
            if model.default_limit_period_unit == PeriodUnit.MINUTE:
                start_time = now - timedelta(minutes=model.default_limit_period_value)
            elif model.default_limit_period_unit == PeriodUnit.HOUR:
                start_time = now - timedelta(hours=model.default_limit_period_value)
            elif model.default_limit_period_unit == PeriodUnit.DAY:
                start_time = now - timedelta(days=model.default_limit_period_value)
            elif model.default_limit_period_unit == PeriodUnit.MONTH:
                start_time = now - timedelta(days=model.default_limit_period_value * 30)

            # 期間内の使用量を取得
            usage = (
                db.query(func.sum(TokenUsage.effective_tokens))
                .filter(
                    TokenUsage.user_id == current_user.id,
                    TokenUsage.model_id == model.id.value,
                    TokenUsage.timestamp >= start_time,
                )
                .scalar()
            ) or 0

            limit_summaries.append(
                {
                    "model_id": model.id.value,
                    "model_name": model.name,
                    "limit_value": model.default_limit_value,
                    "period_unit": model.default_limit_period_unit.value,
                    "period_value": model.default_limit_period_value,
                    "current_usage": int(usage),
                    "remaining": max(0, model.default_limit_value - int(usage)),
                    "usage_percentage": min(
                        100, round((usage / model.default_limit_value) * 100, 1)
                    ),
                    "is_custom_limit": False,
                    "period_description": (
                        f"{model.default_limit_period_value} "
                        f"{model.default_limit_period_unit.value}"
                        f"{'s' if model.default_limit_period_value > 1 else ''}"
                    ),
                }
            )

    return {"limits": limit_summaries, "total_models": len(limit_summaries)}
