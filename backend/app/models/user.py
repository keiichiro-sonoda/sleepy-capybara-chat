from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.chat import ChatSession
    from app.models.token_limit import TokenLimit
    from app.models.token_usage import TokenUsage


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, init=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), init=False, default=None
    )

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_token: Mapped[str | None] = mapped_column(
        String, nullable=True, index=True, default=None
    )
    verification_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    reset_token: Mapped[str | None] = mapped_column(
        String, nullable=True, index=True, default=None
    )
    reset_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    # リレーションシップ
    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        "ChatSession",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        init=False,
        default_factory=list,
    )
    token_limits: Mapped[list["TokenLimit"]] = relationship(
        "TokenLimit",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        init=False,
        default_factory=list,
    )
    token_usage: Mapped[list["TokenUsage"]] = relationship(
        "TokenUsage",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        init=False,
        default_factory=list,
    )
