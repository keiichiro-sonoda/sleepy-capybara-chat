from sendgrid import SendGridAPIClient  # type: ignore
from sendgrid.helpers.mail import (  # type: ignore
    Mail,
    Email,
    To,
    TrackingSettings,
    ClickTracking,
    OpenTracking,
    SubscriptionTracking,
)
from app.core.config import get_settings
from .base import EmailService
import logging
from pathlib import Path
from jinja2 import Template

logger = logging.getLogger(__name__)
settings = get_settings()


class SendGridService(EmailService):
    def __init__(self, api_key: str) -> None:
        self.sg = SendGridAPIClient(api_key)
        self.template_folder = Path(__file__).parent.parent / "templates"

    def _render_template(self, template_name: str, context: dict) -> str:
        template_path = self.template_folder / template_name
        with open(template_path, "r", encoding="utf-8") as f:
            template = Template(f.read())
        return template.render(**context)

    async def send_verification_email(self, email: str, token: str) -> None:
        try:
            verification_url = (
                f"{settings.FRONTEND_URL}/auth/verify-email?token={token}"
            )
            context = {
                "verification_url": verification_url,
                "app_name": "Sleepy Capybara Chat",
            }
            html_content = self._render_template("verification.html", context)

            message = Mail(
                from_email=Email(settings.MAIL_FROM),
                to_emails=To(email),
                subject="メールアドレスの確認",
                html_content=html_content,
            )
            message.tracking_settings = TrackingSettings(
                click_tracking=ClickTracking(enable=False),
                open_tracking=OpenTracking(enable=False),
                subscription_tracking=SubscriptionTracking(enable=False),
            )
            response = self.sg.send(message)
            logger.info(
                f"Verification email sent to {email}, status code: {response.status_code}"
            )
        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {str(e)}")
            raise

    async def send_password_reset_email(self, email: str, token: str) -> None:
        try:
            reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={token}"
            context = {
                "reset_url": reset_url,
                "app_name": "Sleepy Capybara Chat",
            }
            html_content = self._render_template("password_reset.html", context)

            message = Mail(
                from_email=Email(settings.MAIL_FROM),
                to_emails=To(email),
                subject="パスワードリセット",
                html_content=html_content,
            )
            message.tracking_settings = TrackingSettings(
                click_tracking=ClickTracking(enable=False),
                open_tracking=OpenTracking(enable=False),
                subscription_tracking=SubscriptionTracking(enable=False),
            )
            response = self.sg.send(message)
            logger.info(
                f"Password reset email sent to {email}, status code: {response.status_code}"
            )
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {str(e)}")
            raise
