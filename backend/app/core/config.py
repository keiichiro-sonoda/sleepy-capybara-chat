from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # アプリケーション設定
    PROJECT_NAME: str = "Sleepy Capybara Chat"
    API_V1_STR: str = "/api/v1"

    # データベース設定
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgrespassword"
    POSTGRES_DB: str = "capybara_chat"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432

    # JWT設定
    JWT_SECRET_KEY: str = "dev_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS設定
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
    ]

    # Ollama設定
    OLLAMA_API_BASE_URL: str = "http://ollama:11434"

    # OpenAI設定
    OPENAI_API_KEY: str = ""
    OPENAI_ORGANIZATION_ID: str = ""
    OPENAI_DEFAULT_RESPONSES_MODEL: str = "gpt-5-nano"

    # メール設定 (MailHog用)
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = "noreply@example.com"
    MAIL_PORT: int = 1025
    MAIL_SERVER: str = "mailhog"
    MAIL_SSL_TLS: bool = False
    MAIL_STARTTLS: bool = False
    FRONTEND_URL: str = "http://localhost:3000"

    # Admin credentials
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "admin123"  # 本番環境では必ず変更すること

    # Email Service Configuration
    EMAIL_SERVICE: str = "mailhog"  # "mailhog", "sendgrid", or "gmail"
    SENDGRID_API_KEY: str = ""  # SendGrid API Key

    # Gmail SMTP設定
    GMAIL_USER: str = ""  # Gmail address
    GMAIL_APP_PASSWORD: str = ""  # Gmail App Password (not regular password)

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Pydantic v2の新しい設定方法
    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
