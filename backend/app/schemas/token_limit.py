from pydantic import BaseModel, ConfigDict

from app.schemas.enums import AIModelId, MetricType, PeriodUnit


class TokenLimitBase(BaseModel):
    model_id: AIModelId
    user_id: int
    metric_type: MetricType = MetricType.TOKENS
    limit_value: int
    period_unit: PeriodUnit
    period_value: int = 1


class TokenLimitCreate(TokenLimitBase):
    pass


class TokenLimitUpdate(BaseModel):
    model_id: AIModelId | None = None
    user_id: int | None = None
    metric_type: MetricType | None = None
    limit_value: int | None = None
    period_unit: PeriodUnit | None = None
    period_value: int | None = None


class TokenLimit(TokenLimitBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class TokenLimitWithModelName(TokenLimit):
    model_name: str

    model_config = ConfigDict(from_attributes=True)
