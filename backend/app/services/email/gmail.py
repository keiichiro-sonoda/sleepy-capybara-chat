import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Template

from app.core.config import get_settings

from .base import EmailService

logger = logging.getLogger(__name__)
settings = get_settings()


class GmailService(EmailService):
    def __init__(self, gmail_user: str, gmail_password: str) -> None:
        self.gmail_user = gmail_user
        self.gmail_password = gmail_password
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.template_folder = Path(__file__).parent.parent / "templates"

        logger.info(f"GmailService initialized with user: {gmail_user}")

    def _render_template(self, template_name: str, context: dict) -> str:
        """HTMLテンプレートをレンダリングする"""
        template_path = self.template_folder / template_name
        with open(template_path, "r", encoding="utf-8") as f:
            template = Template(f.read())
        return template.render(**context)

    def _create_message(
        self, to_email: str, subject: str, html_content: str
    ) -> MIMEMultipart:
        """メッセージオブジェクトを作成する"""
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self.gmail_user
        message["To"] = to_email

        # HTMLコンテンツを追加
        html_part = MIMEText(html_content, "html", "utf-8")
        message.attach(html_part)

        return message

    async def _send_email(self, to_email: str, subject: str, html_content: str) -> None:
        """Gmail SMTPを使用してメールを送信する"""
        try:
            # メッセージを作成
            message = self._create_message(to_email, subject, html_content)

            # SSL/TLS接続でSMTPサーバーに接続
            context = ssl.create_default_context()

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)  # TLS暗号化を開始
                server.login(self.gmail_user, self.gmail_password)  # ログイン

                # メール送信
                text = message.as_string()
                server.sendmail(self.gmail_user, to_email, text)

                logger.info(f"Email sent successfully to {to_email}")

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication failed: {str(e)}")
            raise Exception(
                f"Gmail認証に失敗しました。アプリパスワードを確認してください: {str(e)}"
            )
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"Recipient refused: {str(e)}")
            raise Exception(f"受信者のメールアドレスが拒否されました: {str(e)}")
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error occurred: {str(e)}")
            raise Exception(f"メール送信中にSMTPエラーが発生しました: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error occurred while sending email: {str(e)}")
            raise Exception(f"メール送信中に予期しないエラーが発生しました: {str(e)}")

    async def send_verification_email(self, email: str, token: str) -> None:
        """メール確認用のメールを送信する"""
        try:
            verification_url = (
                f"{settings.FRONTEND_URL}/auth/verify-email?token={token}"
            )
            context = {
                "verification_url": verification_url,
                "app_name": "Sleepy Capybara Chat",
            }
            html_content = self._render_template("verification.html", context)

            await self._send_email(
                to_email=email,
                subject="メールアドレスの確認",
                html_content=html_content,
            )

            logger.info(f"Verification email sent to {email}")

        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {str(e)}")
            raise

    async def send_password_reset_email(self, email: str, token: str) -> None:
        """パスワードリセット用のメールを送信する"""
        try:
            reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={token}"
            context = {
                "reset_url": reset_url,
                "app_name": "Sleepy Capybara Chat",
            }
            html_content = self._render_template("password_reset.html", context)

            await self._send_email(
                to_email=email, subject="パスワードリセット", html_content=html_content
            )

            logger.info(f"Password reset email sent to {email}")

        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {str(e)}")
            raise
