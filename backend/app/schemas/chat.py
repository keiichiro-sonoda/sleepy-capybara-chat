from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Literal


class MessageBase(BaseModel):
    content: str
    role: str


class MessageCreate(MessageBase):
    stream: bool = False


class Message(MessageBase):
    id: int
    session_id: int
    created_at: datetime
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class ChatSessionBase(BaseModel):
    model_name: str = "llama3"
    name: str | None = None


class ChatSessionCreate(ChatSessionBase):
    # サポートされるモデル名をLiteralで指定することで型チェックが可能になります
    # ただし、拡張性を考慮して単純なstrのままにしておくことも選択肢です
    model_name: str = "llama3"


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
