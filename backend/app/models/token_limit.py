from typing import TYPE_CHECKING

from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.schemas.enums import AIModelId, MetricType, PeriodUnit

if TYPE_CHECKING:
    from app.models.user import User


class TokenLimit(Base):
    __tablename__ = "token_limits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, init=False)
    model_id: Mapped[AIModelId] = mapped_column(
        SQLAlchemyEnum(AIModelId, name="aimodelid_enum", create_type=True),
        index=True,
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True, nullable=False
    )  # ユーザーIDは必須

    metric_type: Mapped[MetricType] = mapped_column(
        SQLAlchemyEnum(MetricType, name="metrictype_enum", create_type=True),
        nullable=False,
    )
    limit_value: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # 例: 1000 (トークン数やリクエスト数)

    period_unit: Mapped[PeriodUnit] = mapped_column(
        SQLAlchemyEnum(PeriodUnit, name="periodunit_enum", create_type=True),
        nullable=False,
    )  # 例: PeriodUnit.HOUR
    period_value: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )  # 例: 1 (period_unitと合わせて「1時間」)

    # リレーションシップ (必要に応じて)
    user: Mapped["User"] = relationship(
        "User", back_populates="token_limits", init=False
    )

    # 複合ユニーク制約（例：同じユーザー/モデルに対して同じ種類の制限は一つだけ）
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "model_id",
            "period_unit",
            "period_value",
            name="_user_model_period_uc",
        ),
    )
