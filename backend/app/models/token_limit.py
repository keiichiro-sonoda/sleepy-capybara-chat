from sqlalchemy import (
    Integer,
    String,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
import enum


class MetricType(str, enum.Enum):
    TOKENS = "tokens"
    # REQUESTS = "requests" # 一旦コメントアウトまたは削除


class PeriodUnit(str, enum.Enum):
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"


class TokenLimit(Base):
    __tablename__ = "token_limits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    model_name: Mapped[str] = mapped_column(
        String(255), index=True, nullable=False
    )  # モデル名は必須
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True, nullable=False
    )  # ユーザーIDは必須

    metric_type: Mapped[MetricType] = mapped_column(
        SQLAlchemyEnum(MetricType), nullable=False
    )
    limit_value: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # 例: 1000 (トークン数やリクエスト数)

    period_unit: Mapped[PeriodUnit] = mapped_column(
        SQLAlchemyEnum(PeriodUnit), nullable=False
    )  # 例: PeriodUnit.HOUR
    period_value: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )  # 例: 1 (period_unitと合わせて「1時間」)

    # リレーションシップ (必要に応じて)
    user = relationship("User", back_populates="token_limits")

    # 複合ユニーク制約（例：同じユーザー/モデルに対して同じ種類の制限は一つだけ）
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "model_name",
            "period_unit",
            "period_value",
            name="_user_model_period_uc",
        ),
    )
