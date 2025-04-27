from datetime import datetime
from pydantic import BaseModel, ConfigDict


class MessageBase(BaseModel):
    content: str
    role: str


class MessageCreate(MessageBase):
    stream: bool = False
    model_name: str = "llama3"  # デフォルトでllama3を使用


class Message(MessageBase):
    id: int
    session_id: int
    created_at: datetime
    updated_at: datetime | None = None
    model_name: str  # 使用されたモデル名（必須）
    model_config = ConfigDict(from_attributes=True)


class ChatSessionBase(BaseModel):
    # model_name フィールドを削除
    name: str | None = None


class ChatSessionCreate(ChatSessionBase):
    # model_name フィールドを削除
    pass


class ChatSession(ChatSessionBase):
    id: int
    created_at: datetime
    updated_at: datetime | None = None
    messages: list[Message] = []
    model_config = ConfigDict(from_attributes=True)


class ChatResponse(BaseModel):
    response: str
    session_id: int


# 利用可能なモデルのリスト (フロントエンド側で使用)
AVAILABLE_MODELS = [
    {"id": "llama3", "name": "Llama 3", "provider": "ollama"},
    {"id": "gpt-4.1-nano", "name": "GPT-4.1 Nano", "provider": "openai"},
]
