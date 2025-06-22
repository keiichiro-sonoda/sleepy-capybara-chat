from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.chat import ChatSession
    from app.models.user import User


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    session_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("chat_sessions.id"), nullable=True, index=True
    )
    model_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    effective_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    user: Mapped["User"] = relationship("User", back_populates="token_usage")
    chat_session: Mapped["ChatSession"] = relationship("ChatSession")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.total_tokens = self.prompt_tokens + self.completion_tokens

        # 実質トークン数の計算（初期化時にモデル名から比率を取得して計算する必要がある）
        # このコードはサービス側で計算して渡す方が適切なので、ここではデフォルト値の設定のみ
