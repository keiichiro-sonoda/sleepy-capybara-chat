from datetime import datetime
from sqlalchemy import Boolean, Integer, String, DateTime, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_token: Mapped[str | None] = mapped_column(
        String, nullable=True, index=True
    )
    verification_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reset_token: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    reset_token_expires_at: Mapped[str | None] = mapped_column(
        String, nullable=True, index=True
    )

    # リレーションシップ
    chat_sessions = relationship(
        "ChatSession", back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    token_limits = relationship(
        "TokenLimit", back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    token_usage = relationship(
        "TokenUsage", back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
