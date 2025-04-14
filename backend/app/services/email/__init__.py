from app.core.config import get_settings
from .mailhog import MailHogService
from .sendgrid import SendGridService
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


def get_email_service():
    logger.info(f"EMAIL_SERVICE value: {settings.EMAIL_SERVICE}")
    if settings.EMAIL_SERVICE == "sendgrid":
        logger.info("Using SendGridService")
        return SendGridService(settings.SENDGRID_API_KEY)
    logger.info("Using MailHogService")
    return MailHogService()


def send_verification_email(email: str, token: str):
    """Send verification email using the configured email service"""
    service = get_email_service()
    return service.send_verification_email(email, token)


def send_password_reset_email(email: str, token: str):
    """Send password reset email using the configured email service"""
    service = get_email_service()
    return service.send_password_reset_email(email, token)
