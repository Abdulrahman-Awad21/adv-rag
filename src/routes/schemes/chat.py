from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
import uuid

class ChatMessageBase(BaseModel):
    role: str = Field(..., examples=["user", "assistant"])
    content: str

class ChatMessageCreate(ChatMessageBase):
    pass

class ChatMessageResponse(ChatMessageBase):
    id: int
    chat_uuid: uuid.UUID
    project_id: int
    timestamp: datetime

    class Config:
        from_attributes = True # Replaces orm_mode = True

class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessageResponse]