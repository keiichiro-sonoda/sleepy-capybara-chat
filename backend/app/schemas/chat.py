from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.token_limit import PeriodUnit


# AIモデルの定義用クラス
class AIModel(BaseModel):
    id: str
    name: str
    provider: str
    thinking_mode: str = "none"  # "none", "optional", "forced"
    # 入力トークン1つに対する出力トークンの実質コスト比
    # 例: 4.0 は出力トークン1つが入力トークン4つ分のコストであることを示す
    effective_token_ratio: float = Field(
        default=1.0, description="Output to input token cost ratio"
    )
    default_limit_value: int = Field(
        default=1000000, description="Default token limit value for the defined period"
    )
    default_limit_period_unit: PeriodUnit = Field(
        default=PeriodUnit.DAY,
        description="Default period unit for token limit (e.g., day, hour)",
    )
    default_limit_period_value: int = Field(
        default=1,
        description="Default period value for token limit (e.g., 1 for 1 day/hour)",
    )


# 利用可能なモデルのリスト (AIModelインスタンスのリストとして定義)
AVAILABLE_MODELS: list[AIModel] = [
    AIModel(
        id="qwen3:8b",
        name="Qwen3 8B",
        provider="ollama",
        thinking_mode="optional",
        effective_token_ratio=4.0,  # オープンソースモデルは仮の値
        default_limit_value=500000,
        default_limit_period_unit=PeriodUnit.DAY,
        default_limit_period_value=1,
    ),
    AIModel(
        id="gpt-4.1-nano",
        name="GPT-4.1 Nano",
        provider="openai",
        thinking_mode="none",
        effective_token_ratio=4.0,  # 出力は入力の4倍のコスト
        default_limit_value=2000000,
        default_limit_period_unit=PeriodUnit.DAY,
        default_limit_period_value=1,
    ),
    # 他のモデルも同様にAIModelインスタンスとして追加
]

# デフォルトモデルを最初のモデルに設定
DEFAULT_MODEL: str = AVAILABLE_MODELS[0].id if AVAILABLE_MODELS else "qwen3"


class MessageBase(BaseModel):
    content: str
    role: str
    thinking_content: str | None = None  # 思考過程（オプショナル）


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

    model_config = ConfigDict(from_attributes=True)
