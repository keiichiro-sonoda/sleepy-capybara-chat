from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(
        Integer, ForeignKey("chat_sessions.id"), nullable=True, index=True
    )  # オプショナル：どのセッションでの使用か
    model_name = Column(String(255), nullable=False, index=True)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(
        Integer, nullable=False, default=0
    )  # 計算フィールドだが保存しておくと便利
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # リレーションシップ (必要に応じて)
    user = relationship("User")
    chat_session = relationship("ChatSession")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_tokens = self.input_tokens + self.output_tokens
