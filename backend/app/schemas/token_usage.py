from pydantic import BaseModel
from datetime import datetime


class TokenUsageBase(BaseModel):
    user_id: int
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class TokenUsageCreate(TokenUsageBase):
    pass


class TokenUsage(TokenUsageBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True 
