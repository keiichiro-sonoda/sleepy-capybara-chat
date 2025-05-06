from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from fastapi_mail.schemas import MessageType
from app.core.config import get_settings
from pathlib import Path
from pydantic import SecretStr
from .base import EmailService

settings = get_settings()


class MailHogService(EmailService):
    def __init__(self) -> None:
        self.conf = ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USERNAME,
            MAIL_PASSWORD=SecretStr(settings.MAIL_PASSWORD),
            MAIL_FROM=settings.MAIL_FROM,
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_SERVER=settings.MAIL_SERVER,
            MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
            MAIL_STARTTLS=settings.MAIL_STARTTLS,
            TEMPLATE_FOLDER=Path(__file__).parent.parent / "templates",
        )

    async def send_verification_email(self, email: str, token: str) -> None:
        verification_url = f"{settings.FRONTEND_URL}/auth/verify-email?token={token}"
        message = MessageSchema(
            subject="メールアドレスの確認",
            recipients=[email],
            template_body={
                "verification_url": verification_url,
                "app_name": "Sleepy Capybara Chat",
            },
            subtype=MessageType.html,
        )
        fm = FastMail(self.conf)
        await fm.send_message(message, template_name="verification.html")

    async def send_password_reset_email(self, email: str, token: str) -> None:
        reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={token}"
        message = MessageSchema(
            subject="パスワードリセット",
            recipients=[email],
            template_body={
                "reset_url": reset_url,
                "app_name": "Sleepy Capybara Chat",
            },
            subtype=MessageType.html,
        )
        fm = FastMail(self.conf)
        await fm.send_message(message, template_name="password_reset.html")
