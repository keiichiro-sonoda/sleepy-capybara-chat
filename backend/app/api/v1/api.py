from fastapi import APIRouter
from app.api.v1.chat.chat import router as chat_router
from app.api.v1.users.users import router as users_router
from app.api.v1.admin.token_limits import router as token_limits_router
from app.api.v1.auth.auth import router as auth_router
from app.api.v1.models.models import router as models_router

api_router = APIRouter()

# APIルーターを追加
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(models_router, prefix="/models", tags=["models"])

# 管理者用ルーターを追加
api_router.include_router(
    token_limits_router,
    prefix="/admin",
    tags=["admin"],
)
