import logging
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.token_usage import TokenUsage
from app.models.token_limit import TokenLimit, LimitType

logger = logging.getLogger(__name__)


class TokenUsageService:
    @staticmethod
    async def record_token_usage(
        db: Session,
        user_id: int,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> TokenUsage:
        """トークン使用量を記録する"""
        total_tokens = prompt_tokens + completion_tokens
        token_usage = TokenUsage(
            user_id=user_id,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )
        db.add(token_usage)
        db.commit()
        db.refresh(token_usage)
        return token_usage

    @staticmethod
    async def check_token_limit(
        db: Session, user_id: int, model_name: str
    ) -> tuple[bool, str]:
        """トークン制限をチェックする"""
        now = datetime.utcnow()

        # 制限設定を取得（ユーザー固有 -> モデル固有 -> グローバルの順）
        limits = (
            db.query(TokenLimit)
            .filter(
                (TokenLimit.user_id == user_id) | (TokenLimit.user_id.is_(None)),
                (TokenLimit.model_name == model_name) | (TokenLimit.model_name.is_(None)),
            )
            .all()
        )

        for limit in limits:
            # 期間に応じた使用量を集計
            start_time = now
            if limit.limit_type == LimitType.TOKENS_PER_MINUTE:
                start_time = now - timedelta(minutes=1)
            elif limit.limit_type == LimitType.TOKENS_PER_HOUR:
                start_time = now - timedelta(hours=1)
            elif limit.limit_type == LimitType.TOKENS_PER_DAY:
                start_time = now - timedelta(days=1)
            elif limit.limit_type == LimitType.TOKENS_PER_MONTH:
                start_time = now - timedelta(days=30)

            # 期間内の使用量を集計
            usage = (
                db.query(func.sum(TokenUsage.total_tokens))
                .filter(
                    TokenUsage.user_id == user_id,
                    TokenUsage.model_name == model_name,
                    TokenUsage.created_at >= start_time,
                )
                .scalar()
            ) or 0

            # 制限を超えている場合
            if usage >= limit.limit_value:
                return False, f"Token limit exceeded: {limit.limit_type.value}"

        return True, "OK"

    @staticmethod
    async def get_usage_stats(
        db: Session, user_id: int, model_name: str = None, days: int = 30
    ) -> dict:
        """指定期間のトークン使用統計を取得する"""
        start_time = datetime.utcnow() - timedelta(days=days)
        query = db.query(
            func.sum(TokenUsage.prompt_tokens).label("total_prompt_tokens"),
            func.sum(TokenUsage.completion_tokens).label("total_completion_tokens"),
            func.sum(TokenUsage.total_tokens).label("total_tokens"),
        ).filter(TokenUsage.user_id == user_id, TokenUsage.created_at >= start_time)

        if model_name:
            query = query.filter(TokenUsage.model_name == model_name)

        result = query.first()
        return {
            "total_prompt_tokens": result.total_prompt_tokens or 0,
            "total_completion_tokens": result.total_completion_tokens or 0,
            "total_tokens": result.total_tokens or 0,
        } 
