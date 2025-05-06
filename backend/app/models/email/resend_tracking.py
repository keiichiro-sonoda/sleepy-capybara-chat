from datetime import datetime, timedelta, timezone
from sqlalchemy import Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class EmailResendTracking(Base):
    """
    Model to track email resend attempts for rate limiting.
    This helps prevent abuse of the email resend functionality.
    """
    __tablename__ = "email_resend_tracking"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, index=True, nullable=False)
    last_resend_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resend_count_hour: Mapped[int] = mapped_column(Integer, default=1)
    resend_count_day: Mapped[int] = mapped_column(Integer, default=1)

    @classmethod
    def can_resend(cls, db, email: str) -> tuple[bool, str, datetime | None]:
        """
        Check if an email can be resent based on rate limits.
        Returns a tuple of (can_resend, message, next_available_time).
        """
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)
        
        tracking = db.query(cls).filter(cls.email == email).first()
        
        if not tracking:
            return True, "", None
            
        if tracking.last_resend_at > one_hour_ago:
            next_available = tracking.last_resend_at + timedelta(hours=1)
            return False, "メール再送信は1時間に1回までです。", next_available
            
        if tracking.last_resend_at > one_day_ago and tracking.resend_count_day >= 3:
            next_available = tracking.last_resend_at.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + timedelta(days=1)
            return False, "メール再送信は24時間に3回までです。", next_available
            
        return True, "", None
        
    @classmethod
    def update_tracking(cls, db, email: str) -> None:
        """
        Update the tracking record for an email resend.
        Creates a new record if one doesn't exist, or updates the existing one.
        """
        now = datetime.now(timezone.utc)
        one_day_ago = now - timedelta(days=1)
        one_hour_ago = now - timedelta(hours=1)
        
        tracking = db.query(cls).filter(cls.email == email).first()
        
        if not tracking:
            tracking = cls(
                email=email,
                last_resend_at=now,
                resend_count_hour=1,
                resend_count_day=1
            )
            db.add(tracking)
        else:
            tracking.last_resend_at = now
            
            if tracking.last_resend_at < one_hour_ago:
                tracking.resend_count_hour = 1
            else:
                tracking.resend_count_hour += 1
                
            if tracking.last_resend_at < one_day_ago:
                tracking.resend_count_day = 1
            else:
                tracking.resend_count_day += 1
                
        db.commit()
