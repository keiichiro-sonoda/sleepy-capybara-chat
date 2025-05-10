from pydantic import BaseModel, ConfigDict
from datetime import datetime


class TokenUsageBase(BaseModel):
    user_id: int
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    effective_tokens: int = 0  # 入出力トークンの重み付け合計


class TokenUsageCreate(TokenUsageBase):
    pass


class TokenUsage(TokenUsageBase):
    id: int
    message_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenUsageByModel(BaseModel):
    model_name: str
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    effective_tokens: int  # 実質トークン数（入出力の重み付け考慮）
