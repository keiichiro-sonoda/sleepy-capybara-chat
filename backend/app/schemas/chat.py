from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import AIModelId, PeriodUnit


# AIモデルの定義用クラス
class AIModel(BaseModel):
    id: AIModelId
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
        id=AIModelId.QWEN3_8B,
        name="Qwen3 8B",
        provider="ollama",
        thinking_mode="optional",
        effective_token_ratio=4.0,  # オープンソースモデルは仮の値
        default_limit_value=500000,
        default_limit_period_unit=PeriodUnit.DAY,
        default_limit_period_value=1,
    ),
    AIModel(
        id=AIModelId.GPT_4_1_NANO,
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
DEFAULT_MODEL_ID: AIModelId = (
    AVAILABLE_MODELS[0].id if AVAILABLE_MODELS else AIModelId.QWEN3_8B
)
DEFAULT_MODEL: str = DEFAULT_MODEL_ID.value


class MessageBase(BaseModel):
    content: str
    role: str
    thinking_content: str | None = None  # 思考過程（オプショナル）


class MessageCreate(MessageBase):
    stream: bool = False
    model_id: AIModelId = DEFAULT_MODEL_ID
    thinking_mode: bool = False  # 思考モードのオン/オフ


class Message(MessageBase):
    id: int
    session_id: int
    created_at: datetime
    updated_at: datetime | None = None
    model_id: AIModelId  # Changed from str, Renamed from model_name, 使用されたモデル名（必須）
    model_config = ConfigDict(from_attributes=True)


class ChatSessionBase(BaseModel):
    # model_name フィールドを削除
    name: str | None = None


class ChatSessionCreate(ChatSessionBase):
    # model_name フィールドを削除
    pass


class ChatSessionUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="セッション名")


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
    model_id: AIModelId  # モデルIDを追加

    model_config = ConfigDict(from_attributes=True)
