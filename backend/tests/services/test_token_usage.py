from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models.token_limit import TokenLimit
from app.models.token_usage import TokenUsage
from app.models.user import User
from app.schemas.chat import AIModel
from app.schemas.enums import AIModelId, MetricType, PeriodUnit
from app.services.token_usage import TokenUsageService


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_model_config() -> AIModel:
    """Mock model configuration for testing."""
    return AIModel(
        id=AIModelId.QWEN3_8B,
        name="Test Model",
        provider="test",
        effective_token_ratio=2.0,
        default_limit_value=1000,
        default_limit_period_unit=PeriodUnit.DAY,
        default_limit_period_value=1,
    )


def create_token_usage(
    db: Session,
    user_id: int,
    model_id: str = "qwen3:8b",
    prompt_tokens: int = 100,
    completion_tokens: int = 50,
    effective_tokens: int = 200,
    timestamp: datetime | None = None,
) -> TokenUsage:
    """Factory function to create TokenUsage records."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    usage = TokenUsage(
        user_id=user_id,
        model_id=model_id,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        effective_tokens=effective_tokens,
        timestamp=timestamp,
    )
    db.add(usage)
    db.commit()
    db.refresh(usage)
    return usage


def create_token_limit(
    db: Session,
    user_id: int,
    model_id: AIModelId = AIModelId.QWEN3_8B,
    limit_value: int = 1000,
    period_unit: PeriodUnit = PeriodUnit.DAY,
    period_value: int = 1,
) -> TokenLimit:
    """Factory function to create TokenLimit records."""
    limit = TokenLimit(
        user_id=user_id,
        model_id=model_id,
        metric_type=MetricType.TOKENS,
        limit_value=limit_value,
        period_unit=period_unit,
        period_value=period_value,
    )
    db.add(limit)
    db.commit()
    db.refresh(limit)
    return limit


class TestTokenLimitRollingWindows:
    """Test rolling window calculations for different time periods."""

    @pytest.mark.asyncio
    async def test_daily_rolling_window(self, db: Session, test_user: User) -> None:
        """Test daily rolling window calculation."""
        now = datetime.now(timezone.utc)

        create_token_usage(
            db, test_user.id, effective_tokens=300, timestamp=now - timedelta(hours=12)
        )
        create_token_usage(
            db, test_user.id, effective_tokens=400, timestamp=now - timedelta(hours=6)
        )

        create_token_usage(
            db, test_user.id, effective_tokens=500, timestamp=now - timedelta(days=2)
        )

        create_token_limit(
            db,
            test_user.id,
            limit_value=1000,
            period_unit=PeriodUnit.DAY,
            period_value=1,
        )

        is_allowed, reason = await TokenUsageService.check_token_limit(
            db, test_user.id, AIModelId.QWEN3_8B
        )
        assert is_allowed is True
        assert reason == "OK"

    @pytest.mark.asyncio
    async def test_hourly_rolling_window(self, db: Session, test_user: User) -> None:
        """Test hourly rolling window calculation."""
        now = datetime.now(timezone.utc)

        create_token_usage(
            db,
            test_user.id,
            effective_tokens=600,
            timestamp=now - timedelta(minutes=30),
        )

        create_token_usage(
            db, test_user.id, effective_tokens=400, timestamp=now - timedelta(hours=2)
        )

        create_token_limit(
            db,
            test_user.id,
            limit_value=500,
            period_unit=PeriodUnit.HOUR,
            period_value=1,
        )

        is_allowed, reason = await TokenUsageService.check_token_limit(
            db, test_user.id, AIModelId.QWEN3_8B
        )
        assert is_allowed is False
        assert "Token limit exceeded for 1 hour(s)" in reason

    @pytest.mark.asyncio
    async def test_monthly_rolling_window(self, db: Session, test_user: User) -> None:
        """Test monthly rolling window calculation (30-day approximation)."""
        now = datetime.now(timezone.utc)

        create_token_usage(
            db, test_user.id, effective_tokens=5000, timestamp=now - timedelta(days=15)
        )
        create_token_usage(
            db, test_user.id, effective_tokens=3000, timestamp=now - timedelta(days=25)
        )

        create_token_usage(
            db, test_user.id, effective_tokens=2000, timestamp=now - timedelta(days=35)
        )

        create_token_limit(
            db,
            test_user.id,
            limit_value=10000,
            period_unit=PeriodUnit.MONTH,
            period_value=1,
        )

        is_allowed, reason = await TokenUsageService.check_token_limit(
            db, test_user.id, AIModelId.QWEN3_8B
        )
        assert is_allowed is True
        assert reason == "OK"

    @pytest.mark.asyncio
    async def test_minute_rolling_window(self, db: Session, test_user: User) -> None:
        """Test minute rolling window calculation."""
        now = datetime.now(timezone.utc)

        create_token_usage(
            db,
            test_user.id,
            effective_tokens=150,
            timestamp=now - timedelta(seconds=30),
        )

        create_token_usage(
            db, test_user.id, effective_tokens=100, timestamp=now - timedelta(minutes=2)
        )

        create_token_limit(
            db,
            test_user.id,
            limit_value=200,
            period_unit=PeriodUnit.MINUTE,
            period_value=1,
        )

        is_allowed, reason = await TokenUsageService.check_token_limit(
            db, test_user.id, AIModelId.QWEN3_8B
        )
        assert is_allowed is True
        assert reason == "OK"

    @pytest.mark.asyncio
    async def test_multi_period_rolling_window(
        self, db: Session, test_user: User
    ) -> None:
        """Test rolling window with multiple period values."""
        now = datetime.now(timezone.utc)

        create_token_usage(
            db, test_user.id, effective_tokens=800, timestamp=now - timedelta(days=2)
        )
        create_token_usage(
            db, test_user.id, effective_tokens=600, timestamp=now - timedelta(days=5)
        )

        create_token_usage(
            db, test_user.id, effective_tokens=300, timestamp=now - timedelta(days=8)
        )

        create_token_limit(
            db,
            test_user.id,
            limit_value=2000,
            period_unit=PeriodUnit.DAY,
            period_value=7,
        )

        is_allowed, reason = await TokenUsageService.check_token_limit(
            db, test_user.id, AIModelId.QWEN3_8B
        )
        assert is_allowed is True
        assert reason == "OK"


class TestTokenLimitBreaches:
    """Test token limit breach scenarios."""

    @pytest.mark.asyncio
    async def test_limit_breach_returns_false_with_message(
        self, db: Session, test_user: User
    ) -> None:
        """Test that exceeding limits returns False with proper message."""
        now = datetime.now(timezone.utc)

        create_token_usage(
            db, test_user.id, effective_tokens=1200, timestamp=now - timedelta(hours=1)
        )

        create_token_limit(
            db,
            test_user.id,
            limit_value=1000,
            period_unit=PeriodUnit.DAY,
            period_value=1,
        )

        is_allowed, reason = await TokenUsageService.check_token_limit(
            db, test_user.id, AIModelId.QWEN3_8B
        )

        assert is_allowed is False
        assert "Token limit exceeded for 1 day(s)" in reason

    @pytest.mark.asyncio
    async def test_exact_limit_boundary(self, db: Session, test_user: User) -> None:
        """Test behavior at exact limit boundary."""
        now = datetime.now(timezone.utc)

        create_token_usage(
            db, test_user.id, effective_tokens=1000, timestamp=now - timedelta(hours=1)
        )

        create_token_limit(
            db,
            test_user.id,
            limit_value=1000,
            period_unit=PeriodUnit.DAY,
            period_value=1,
        )

        is_allowed, reason = await TokenUsageService.check_token_limit(
            db, test_user.id, AIModelId.QWEN3_8B
        )

        assert is_allowed is False
        assert "Token limit exceeded" in reason

    @pytest.mark.asyncio
    async def test_multiple_period_limits(self, db: Session, test_user: User) -> None:
        """Test user with multiple period limits for same model."""
        now = datetime.now(timezone.utc)

        create_token_usage(
            db,
            test_user.id,
            effective_tokens=800,
            timestamp=now - timedelta(minutes=30),
        )

        create_token_limit(
            db,
            test_user.id,
            limit_value=1000,
            period_unit=PeriodUnit.DAY,
            period_value=1,
        )
        create_token_limit(
            db,
            test_user.id,
            limit_value=500,
            period_unit=PeriodUnit.HOUR,
            period_value=1,
        )

        is_allowed, reason = await TokenUsageService.check_token_limit(
            db, test_user.id, AIModelId.QWEN3_8B
        )

        assert is_allowed is False
        assert "hour(s)" in reason

    @pytest.mark.asyncio
    async def test_cumulative_usage_exceeds_limit(
        self, db: Session, test_user: User
    ) -> None:
        """Test that cumulative usage across multiple records exceeds limit."""
        now = datetime.now(timezone.utc)

        create_token_usage(
            db, test_user.id, effective_tokens=400, timestamp=now - timedelta(hours=2)
        )
        create_token_usage(
            db, test_user.id, effective_tokens=300, timestamp=now - timedelta(hours=4)
        )
        create_token_usage(
            db, test_user.id, effective_tokens=350, timestamp=now - timedelta(hours=6)
        )

        create_token_limit(
            db,
            test_user.id,
            limit_value=1000,
            period_unit=PeriodUnit.DAY,
            period_value=1,
        )

        is_allowed, reason = await TokenUsageService.check_token_limit(
            db, test_user.id, AIModelId.QWEN3_8B
        )

        assert is_allowed is False
        assert "Token limit exceeded for 1 day(s)" in reason


class TestUserModelSeparation:
    """Test that limits are properly separated per user and per model."""

    @pytest.mark.asyncio
    async def test_per_user_limit_isolation(self, db: Session) -> None:
        """Test that users have separate token limits."""
        user1 = User(email="user1@test.com", hashed_password="hash", is_active=True)
        user2 = User(email="user2@test.com", hashed_password="hash", is_active=True)
        db.add_all([user1, user2])
        db.commit()
        db.refresh(user1)
        db.refresh(user2)

        now = datetime.now(timezone.utc)

        create_token_usage(
            db, user1.id, effective_tokens=1200, timestamp=now - timedelta(hours=1)
        )
        create_token_limit(db, user1.id, limit_value=1000)

        create_token_usage(
            db, user2.id, effective_tokens=500, timestamp=now - timedelta(hours=1)
        )
        create_token_limit(db, user2.id, limit_value=1000)

        is_allowed, _ = await TokenUsageService.check_token_limit(
            db, user1.id, AIModelId.QWEN3_8B
        )
        assert is_allowed is False

        is_allowed, _ = await TokenUsageService.check_token_limit(
            db, user2.id, AIModelId.QWEN3_8B
        )
        assert is_allowed is True

    @pytest.mark.asyncio
    async def test_per_model_limit_isolation(
        self, db: Session, test_user: User
    ) -> None:
        """Test that models have separate token limits."""
        now = datetime.now(timezone.utc)

        create_token_usage(
            db,
            test_user.id,
            model_id="qwen3:8b",
            effective_tokens=1200,
            timestamp=now - timedelta(hours=1),
        )

        create_token_usage(
            db,
            test_user.id,
            model_id="gpt-4.1-nano",
            effective_tokens=500,
            timestamp=now - timedelta(hours=1),
        )

        create_token_limit(
            db, test_user.id, model_id=AIModelId.QWEN3_8B, limit_value=1000
        )
        create_token_limit(
            db, test_user.id, model_id=AIModelId.GPT_4_1_NANO, limit_value=1000
        )

        is_allowed, _ = await TokenUsageService.check_token_limit(
            db, test_user.id, AIModelId.QWEN3_8B
        )
        assert is_allowed is False

        is_allowed, _ = await TokenUsageService.check_token_limit(
            db, test_user.id, AIModelId.GPT_4_1_NANO
        )
        assert is_allowed is True

    @pytest.mark.asyncio
    async def test_cross_user_usage_isolation(self, db: Session) -> None:
        """Test that one user's usage doesn't affect another user's limits."""
        user1 = User(email="user1@test.com", hashed_password="hash", is_active=True)
        user2 = User(email="user2@test.com", hashed_password="hash", is_active=True)
        db.add_all([user1, user2])
        db.commit()
        db.refresh(user1)
        db.refresh(user2)

        now = datetime.now(timezone.utc)

        create_token_usage(
            db, user1.id, effective_tokens=2000, timestamp=now - timedelta(hours=1)
        )

        create_token_limit(db, user2.id, limit_value=1000)

        is_allowed, reason = await TokenUsageService.check_token_limit(
            db, user2.id, AIModelId.QWEN3_8B
        )
        assert is_allowed is True
        assert reason == "OK"


class TestDefaultLimitsAndEdgeCases:
    """Test default limits and edge cases."""

    @pytest.mark.asyncio
    @patch("app.services.token_usage.AVAILABLE_MODELS")
    async def test_default_model_limits(
        self, mock_models: Any, db: Session, test_user: User, test_model_config: AIModel
    ) -> None:
        """Test fallback to default model limits when no user limits exist."""
        mock_models.__iter__.return_value = [test_model_config]

        now = datetime.now(timezone.utc)

        create_token_usage(
            db, test_user.id, effective_tokens=500, timestamp=now - timedelta(hours=1)
        )

        is_allowed, reason = await TokenUsageService.check_token_limit(
            db, test_user.id, AIModelId.QWEN3_8B
        )

        assert is_allowed is True
        assert reason == "OK"

    @pytest.mark.asyncio
    @patch("app.services.token_usage.AVAILABLE_MODELS")
    async def test_default_limit_exceeded(
        self, mock_models: Any, db: Session, test_user: User, test_model_config: AIModel
    ) -> None:
        """Test default limit breach."""
        mock_models.__iter__.return_value = [test_model_config]

        now = datetime.now(timezone.utc)

        create_token_usage(
            db, test_user.id, effective_tokens=1200, timestamp=now - timedelta(hours=1)
        )

        is_allowed, reason = await TokenUsageService.check_token_limit(
            db, test_user.id, AIModelId.QWEN3_8B
        )

        assert is_allowed is False
        assert "Default token limit exceeded" in reason

    @pytest.mark.asyncio
    async def test_no_limits_found(self, db: Session, test_user: User) -> None:
        """Test behavior when no limits are found."""
        with patch("app.services.token_usage.AVAILABLE_MODELS", []):
            is_allowed, reason = await TokenUsageService.check_token_limit(
                db, test_user.id, AIModelId.QWEN3_8B
            )

            assert is_allowed is True
            assert reason == "No limit found"

    @pytest.mark.asyncio
    async def test_zero_usage_within_limits(self, db: Session, test_user: User) -> None:
        """Test that zero usage is always within limits."""
        create_token_limit(db, test_user.id, limit_value=1000)

        is_allowed, reason = await TokenUsageService.check_token_limit(
            db, test_user.id, AIModelId.QWEN3_8B
        )

        assert is_allowed is True
        assert reason == "OK"

    @pytest.mark.asyncio
    async def test_usage_outside_time_window_ignored(
        self, db: Session, test_user: User
    ) -> None:
        """Test that usage outside the time window is ignored."""
        now = datetime.now(timezone.utc)

        create_token_usage(
            db, test_user.id, effective_tokens=2000, timestamp=now - timedelta(days=2)
        )

        create_token_limit(
            db,
            test_user.id,
            limit_value=1000,
            period_unit=PeriodUnit.DAY,
            period_value=1,
        )

        is_allowed, reason = await TokenUsageService.check_token_limit(
            db, test_user.id, AIModelId.QWEN3_8B
        )

        assert is_allowed is True
        assert reason == "OK"


class TestEffectiveTokenCalculation:
    """Test effective token calculation logic."""

    @patch("app.services.token_usage.AVAILABLE_MODELS")
    def test_get_model_token_ratio(
        self, mock_models: Any, test_model_config: AIModel
    ) -> None:
        """Test model token ratio retrieval."""
        mock_models.__iter__.return_value = [test_model_config]

        ratio = TokenUsageService.get_model_token_ratio(AIModelId.QWEN3_8B)
        assert ratio == 2.0

    @patch("app.services.token_usage.AVAILABLE_MODELS")
    def test_get_model_token_ratio_not_found(self, mock_models: Any) -> None:
        """Test default ratio when model not found."""
        mock_models.__iter__.return_value = []

        ratio = TokenUsageService.get_model_token_ratio(AIModelId.QWEN3_8B)
        assert ratio == 1.0

    def test_calculate_effective_tokens(self) -> None:
        """Test effective token calculation."""
        with patch.object(TokenUsageService, "get_model_token_ratio", return_value=4.0):
            effective = TokenUsageService.calculate_effective_tokens(
                AIModelId.QWEN3_8B, prompt_tokens=100, completion_tokens=50
            )
            assert effective == 300

    @pytest.mark.asyncio
    async def test_record_token_usage(self, db: Session, test_user: User) -> None:
        """Test token usage recording with effective tokens."""
        with patch.object(TokenUsageService, "get_model_token_ratio", return_value=3.0):
            usage = await TokenUsageService.record_token_usage(
                db,
                test_user.id,
                AIModelId.QWEN3_8B,
                prompt_tokens=200,
                completion_tokens=100,
            )

            assert usage.prompt_tokens == 200
            assert usage.completion_tokens == 100
            assert usage.total_tokens == 300
            assert usage.effective_tokens == 500
            assert usage.user_id == test_user.id
            assert usage.model_id == "qwen3:8b"

    @pytest.mark.asyncio
    async def test_get_model_default_limit(self, test_model_config: AIModel) -> None:
        """Test retrieval of model default limits."""
        with patch("app.services.token_usage.AVAILABLE_MODELS", [test_model_config]):
            result = TokenUsageService.get_model_default_limit(AIModelId.QWEN3_8B)

            assert result is not None
            limit_value, period_unit, period_value = result
            assert limit_value == 1000
            assert period_unit == PeriodUnit.DAY
            assert period_value == 1

    def test_get_model_default_limit_not_found(self) -> None:
        """Test default limit retrieval when model not found."""
        with patch("app.services.token_usage.AVAILABLE_MODELS", []):
            result = TokenUsageService.get_model_default_limit(AIModelId.QWEN3_8B)
            assert result is None


class TestUsageStatsAggregation:
    """Test token usage statistics aggregation."""

    @pytest.mark.asyncio
    async def test_get_usage_stats_by_model(self, db: Session, test_user: User) -> None:
        """Test usage statistics aggregation by model."""
        now = datetime.now(timezone.utc)

        create_token_usage(
            db,
            test_user.id,
            model_id="qwen3:8b",
            prompt_tokens=100,
            completion_tokens=50,
            effective_tokens=200,
            timestamp=now - timedelta(days=5),
        )
        create_token_usage(
            db,
            test_user.id,
            model_id="qwen3:8b",
            prompt_tokens=150,
            completion_tokens=75,
            effective_tokens=300,
            timestamp=now - timedelta(days=10),
        )

        create_token_usage(
            db,
            test_user.id,
            model_id="gpt-4.1-nano",
            prompt_tokens=200,
            completion_tokens=100,
            effective_tokens=600,
            timestamp=now - timedelta(days=15),
        )

        create_token_usage(
            db,
            test_user.id,
            model_id="qwen3:8b",
            prompt_tokens=50,
            completion_tokens=25,
            effective_tokens=100,
            timestamp=now - timedelta(days=35),
        )

        stats = await TokenUsageService.get_usage_stats_by_model(
            db, test_user.id, days=30
        )

        qwen_stats = next((s for s in stats if s.model_name == "qwen3:8b"), None)
        gpt_stats = next((s for s in stats if s.model_name == "gpt-4.1-nano"), None)

        assert qwen_stats is not None
        assert qwen_stats.total_prompt_tokens == 250
        assert qwen_stats.total_completion_tokens == 125
        assert qwen_stats.total_tokens == 375
        assert qwen_stats.effective_tokens == 500

        assert gpt_stats is not None
        assert gpt_stats.total_prompt_tokens == 200
        assert gpt_stats.total_completion_tokens == 100
        assert gpt_stats.effective_tokens == 600

    @pytest.mark.asyncio
    async def test_get_usage_stats_empty_result(
        self, db: Session, test_user: User
    ) -> None:
        """Test usage statistics when no usage exists."""
        stats = await TokenUsageService.get_usage_stats_by_model(
            db, test_user.id, days=30
        )
        assert stats == []

    @pytest.mark.asyncio
    async def test_get_usage_stats_different_time_periods(
        self, db: Session, test_user: User
    ) -> None:
        """Test usage statistics with different time periods."""
        now = datetime.now(timezone.utc)

        create_token_usage(
            db, test_user.id, effective_tokens=100, timestamp=now - timedelta(days=5)
        )
        create_token_usage(
            db, test_user.id, effective_tokens=200, timestamp=now - timedelta(days=15)
        )
        create_token_usage(
            db, test_user.id, effective_tokens=300, timestamp=now - timedelta(days=45)
        )

        stats_7_days = await TokenUsageService.get_usage_stats_by_model(
            db, test_user.id, days=7
        )
        stats_30_days = await TokenUsageService.get_usage_stats_by_model(
            db, test_user.id, days=30
        )

        assert len(stats_7_days) == 1
        assert stats_7_days[0].effective_tokens == 100

        assert len(stats_30_days) == 1
        assert stats_30_days[0].effective_tokens == 300
