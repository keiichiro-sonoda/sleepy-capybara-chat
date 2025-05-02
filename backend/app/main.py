from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from app.core.config import get_settings
from app.api import auth, chat, models, users
from app.db.session import Base, engine, SessionLocal
from app.db.seed import seed_admin_user

settings = get_settings()

# ロギング設定
log_level = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# データベーステーブルの作成
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # 起動時の処理
    db = SessionLocal()
    try:
        seed_admin_user(db)
    finally:
        db.close()
    yield
    # シャットダウン時の処理（必要な場合）


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターの登録
app.include_router(auth, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(chat, prefix=f"{settings.API_V1_STR}/chat", tags=["chat"])
app.include_router(models, prefix=f"{settings.API_V1_STR}/models", tags=["models"])
app.include_router(users, prefix=f"{settings.API_V1_STR}/users", tags=["users"])


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to Sleepy Capybara Chat API"}
