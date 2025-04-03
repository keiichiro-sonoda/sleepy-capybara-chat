from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class MessageBase(BaseModel):
    content: str
    role: str

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    id: int
    session_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ChatSessionBase(BaseModel):
    model_name: str

class ChatSessionCreate(ChatSessionBase):
    pass

class ChatSession(ChatSessionBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    messages: List[Message] = []

    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    response: str
    session_id: int 
