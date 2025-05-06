from app.core.config import get_settings
from app.services.email.sendgrid import SendGridService

settings = get_settings()

if not settings.SENDGRID_API_KEY:
    raise ValueError("SENDGRID_API_KEY is not set in environment variables")

email_service = SendGridService(settings.SENDGRID_API_KEY)
