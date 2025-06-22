import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.token_limit import PeriodUnit, TokenLimit
from app.models.token_usage import TokenUsage
from app.schemas.chat import AVAILABLE_MODELS
from app.schemas.enums import AIModelId
from app.schemas.token_usage import TokenUsageByModel

logger = logging.getLogger(__name__)


class TokenUsageService:
    @staticmethod
    def get_model_token_ratio(model_id: AIModelId) -> float:
        """モデル名から入出力トークン比率を取得する"""
        for model in AVAILABLE_MODELS:
            if model.id == model_id:
                return model.effective_token_ratio
        # デフォルト値（見つからない場合は1.0）
        return 1.0

    @staticmethod
    def calculate_effective_tokens(
        model_id: AIModelId,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> int:
        """実質トークン数を計算する（入出力の比率を考慮）"""
        token_ratio = TokenUsageService.get_model_token_ratio(model_id)
        effective_tokens = prompt_tokens + int(completion_tokens * token_ratio)
        return effective_tokens

    @staticmethod
    async def record_token_usage(
        db: Session,
        user_id: int,
        model_id: AIModelId,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> TokenUsage:
        """トークン使用量を記録する"""
        total_tokens = prompt_tokens + completion_tokens
        effective_tokens = TokenUsageService.calculate_effective_tokens(
            model_id, prompt_tokens, completion_tokens
        )

        token_usage = TokenUsage(
            user_id=user_id,
            model_id=model_id.value,  # DB model_id is string
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            effective_tokens=effective_tokens,
        )
        db.add(token_usage)
        db.commit()
        db.refresh(token_usage)
        return token_usage

    @staticmethod
    def get_model_default_limit(
        model_id: AIModelId,
    ) -> tuple[int, PeriodUnit, int] | None:
        """モデルのデフォルトトークン制限を取得する"""
        for model in AVAILABLE_MODELS:
            if model.id == model_id:
                return (
                    model.default_limit_value,
                    model.default_limit_period_unit,
                    model.default_limit_period_value,
                )
        return None

    @staticmethod
    async def check_token_limit(
        db: Session, user_id: int, model_id: AIModelId
    ) -> tuple[bool, str]:
        """トークン制限をチェックする（実質トークン数ベース）"""
        now = datetime.now(UTC)

        # ユーザー固有の制限を確認
        user_limits = (
            db.query(TokenLimit)
            .filter(
                TokenLimit.user_id == user_id,
                TokenLimit.model_id == model_id,  # TokenLimit.model_id is Enum
            )
            .all()
        )

        # ユーザー固有の制限がない場合は、モデルのデフォルト制限を使用
        if not user_limits:
            default_limit = TokenUsageService.get_model_default_limit(model_id)
            if not default_limit:
                # デフォルト制限も見つからない場合は制限なしとして扱う
                return True, "No limit found"

            limit_value, period_unit, period_value = default_limit
            # 期間に応じた開始時刻を計算
            start_time = now
            if period_unit == PeriodUnit.MINUTE:
                start_time = now - timedelta(minutes=period_value)
            elif period_unit == PeriodUnit.HOUR:
                start_time = now - timedelta(hours=period_value)
            elif period_unit == PeriodUnit.DAY:
                start_time = now - timedelta(days=period_value)
            elif period_unit == PeriodUnit.MONTH:
                start_time = now - timedelta(days=period_value * 30)  # 簡易的な月計算

            # 期間内の使用量を集計（実質トークン数ベース）
            usage = (
                db.query(func.sum(TokenUsage.effective_tokens))
                .filter(
                    TokenUsage.user_id == user_id,
                    TokenUsage.model_id
                    == model_id.value,  # TokenUsage.model_id is string
                    TokenUsage.timestamp >= start_time,
                )
                .scalar()
            ) or 0

            if usage >= limit_value:
                return (
                    False,
                    f"Default token limit exceeded for {period_value} "
                    f"{period_unit.value}(s)",
                )
            return True, "OK"

        # ユーザー固有の制限をチェック
        for limit in user_limits:
            # 期間に応じた開始時刻を計算
            start_time = now
            if limit.period_unit == PeriodUnit.MINUTE:
                start_time = now - timedelta(minutes=limit.period_value)
            elif limit.period_unit == PeriodUnit.HOUR:
                start_time = now - timedelta(hours=limit.period_value)
            elif limit.period_unit == PeriodUnit.DAY:
                start_time = now - timedelta(days=limit.period_value)
            elif limit.period_unit == PeriodUnit.MONTH:
                start_time = now - timedelta(
                    days=limit.period_value * 30
                )  # 簡易的な月計算

            # 期間内の使用量を集計（実質トークン数ベース）
            usage = (
                db.query(func.sum(TokenUsage.effective_tokens))
                .filter(
                    TokenUsage.user_id == user_id,
                    TokenUsage.model_id
                    == model_id.value,  # TokenUsage.model_id is string
                    TokenUsage.timestamp >= start_time,
                )
                .scalar()
            ) or 0

            if usage >= limit.limit_value:
                return (
                    False,
                    f"Token limit exceeded for {limit.period_value} "
                    f"{limit.period_unit.value}(s)",
                )

        return True, "OK"

    @staticmethod
    async def get_usage_stats_by_model(
        db: Session, user_id: int, days: int = 30
    ) -> list[TokenUsageByModel]:
        """指定期間のモデルごとのトークン使用統計を取得する"""
        start_time = datetime.now(UTC) - timedelta(days=days)

        # モデルごとの集計クエリ
        query = (
            db.query(
                TokenUsage.model_id,
                func.sum(TokenUsage.prompt_tokens).label("total_prompt_tokens"),
                func.sum(TokenUsage.completion_tokens).label("total_completion_tokens"),
                func.sum(TokenUsage.total_tokens).label("total_tokens"),
                func.sum(TokenUsage.effective_tokens).label("effective_tokens"),
            )
            .filter(TokenUsage.user_id == user_id, TokenUsage.timestamp >= start_time)
            .group_by(TokenUsage.model_id)
        )

        results = query.all()

        # 結果を TokenUsageByModel のリストに変換
        stats: list[TokenUsageByModel] = []
        for row in results:
            stats.append(
                TokenUsageByModel(
                    model_name=row.model_id,
                    total_prompt_tokens=row.total_prompt_tokens or 0,
                    total_completion_tokens=row.total_completion_tokens or 0,
                    total_tokens=row.total_tokens or 0,
                    effective_tokens=row.effective_tokens or 0,
                )
            )

        return stats
