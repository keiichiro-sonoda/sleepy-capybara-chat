from datetime import datetime
from pydantic import BaseModel, ConfigDict


class MessageBase(BaseModel):
    content: str
    role: str


class MessageCreate(MessageBase):
    pass


class Message(MessageBase):
    id: int
    session_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ChatSessionBase(BaseModel):
    model_name: str


class ChatSessionCreate(ChatSessionBase):
    pass


class ChatSession(ChatSessionBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime | None
    messages: list[Message] = []
    model_config = ConfigDict(from_attributes=True)


class ChatResponse(BaseModel):
    response: str
    session_id: int
