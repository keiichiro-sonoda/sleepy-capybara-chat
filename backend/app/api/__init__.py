"""
API module
"""

from app.api.auth.auth import router as auth_router
from app.api.chat.chat import router as chat_router
from app.api.users.users import router as users_router

# 外部からのアクセス用に公開
auth = auth_router
chat = chat_router
users = users_router
