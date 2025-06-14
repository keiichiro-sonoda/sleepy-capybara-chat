from app.core.config import get_settings
from .mailhog import MailHogService
from .sendgrid import SendGridService
from .gmail import GmailService
from .base import EmailService
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


def get_email_service() -> EmailService:
    logger.info(f"EMAIL_SERVICE value: {settings.EMAIL_SERVICE}")
    if settings.EMAIL_SERVICE == "sendgrid":
        logger.info("Using SendGridService")
        return SendGridService(settings.SENDGRID_API_KEY)
    elif settings.EMAIL_SERVICE == "gmail":
        logger.info("Using GmailService")
        if not settings.GMAIL_USER or not settings.GMAIL_APP_PASSWORD:
            raise ValueError(
                "GMAIL_USER and GMAIL_APP_PASSWORD must be set when using Gmail service"
            )
        return GmailService(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD)
    logger.info("Using MailHogService")
    return MailHogService()


async def send_verification_email(email: str, token: str) -> None:
    """Send verification email using the configured email service"""
    service = get_email_service()
    await service.send_verification_email(email, token)


async def send_password_reset_email(email: str, token: str) -> None:
    """Send password reset email using the configured email service"""
    service = get_email_service()
    await service.send_password_reset_email(email, token)
