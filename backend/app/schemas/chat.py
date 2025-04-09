from datetime import datetime
from pydantic import BaseModel, ConfigDict


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


class ChatSessionCreate(ChatSessionBase):
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
