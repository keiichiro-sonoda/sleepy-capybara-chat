from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.schemas.enums import AIModelId

if TYPE_CHECKING:
    from app.models.user import User


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, init=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None
    )  # セッション名を格納するフィールド
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), init=False, default=None
    )

    # リレーションシップ
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="chat_session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        init=False,
        default_factory=list,
    )
    user: Mapped["User"] = relationship(
        "User", back_populates="chat_sessions", init=False
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, init=False)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chat_sessions.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String, nullable=False)  # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model_id: Mapped[AIModelId] = mapped_column(
        SQLAlchemyEnum(AIModelId, name="aimodelid_enum", create_type=False),
        nullable=False,
    )  # Renamed from model_name, 使用されたモデル名（必須）
    thinking_content: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None
    )  # 思考過程を保存するフィールド
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), init=False, default=None
    )

    # リレーションシップ
    chat_session: Mapped["ChatSession"] = relationship(
        "ChatSession", back_populates="messages", init=False
    )
