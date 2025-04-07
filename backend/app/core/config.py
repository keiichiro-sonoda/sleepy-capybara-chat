from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


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
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Ollama設定
    OLLAMA_API_BASE_URL: str = "http://ollama:11434"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Pydantic v2の新しい設定方法
    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
