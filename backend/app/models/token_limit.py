from sqlalchemy import Column, Integer, String, Enum as SQLAlchemyEnum, ForeignKey
from app.db.session import Base
import enum


class LimitType(str, enum.Enum):
    TOKENS_PER_MINUTE = "tokens_per_minute"
    TOKENS_PER_HOUR = "tokens_per_hour"
    TOKENS_PER_DAY = "tokens_per_day"
    TOKENS_PER_MONTH = "tokens_per_month"
    REQUESTS_PER_MINUTE = "requests_per_minute"
    REQUESTS_PER_HOUR = "requests_per_hour"
    REQUESTS_PER_DAY = "requests_per_day"


class TokenLimit(Base):
    __tablename__ = "token_limits"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(
        String(255), index=True, nullable=True
    )  # NULLの場合は全モデル共通の制限
    user_id = Column(
        Integer, ForeignKey("users.id"), index=True, nullable=True
    )  # NULLの場合は全ユーザー共通の制限
    limit_type = Column(SQLAlchemyEnum(LimitType), nullable=False)
    limit_value = Column(Integer, nullable=False)

    # リレーションシップ (必要に応じて)
    # user = relationship("User")

    # 複合ユニーク制約（例：同じユーザー/モデルに対して同じ種類の制限は一つだけ）
    # __table_args__ = (UniqueConstraint('user_id', 'model_name', 'limit_type', name='_user_model_limit_uc'),)
