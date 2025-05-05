from datetime import datetime
from pydantic import BaseModel, ConfigDict


# 利用可能なモデルのリスト
AVAILABLE_MODELS = [
    # {"id": "llama3", "name": "Llama 3", "provider": "ollama"},
    {
        "id": "qwen3:8b",
        "name": "Qwen3 8B",
        "provider": "ollama",
        "thinking_mode": "optional",
    },
    {
        "id": "gpt-4.1-nano",
        "name": "GPT-4.1 Nano",
        "provider": "openai",
        "thinking_mode": "none",
    },
]

# デフォルトモデルを最初のモデルに設定
DEFAULT_MODEL = AVAILABLE_MODELS[0]["id"] if AVAILABLE_MODELS else "qwen3"


class MessageBase(BaseModel):
    content: str
    role: str
    thinking_content: str | None = None  # 思考過程（オプショナル）


# AIモデルの定義用クラス
class AIModel(BaseModel):
    id: str
    name: str
    provider: str
    thinking_mode: str = "none"  # "none", "optional", "forced"


class MessageCreate(MessageBase):
    stream: bool = False
    model_name: str = DEFAULT_MODEL
    thinking_mode: bool = False  # 思考モードのオン/オフ


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


class ChatResponseWithThinking(ChatResponse):
    thinking_content: str | None = None


# メッセージ履歴表示用
class MessageSchema(MessageBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
