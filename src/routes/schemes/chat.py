from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid
from .user import UserEmailResponse 


class ChatMessageBase(BaseModel):
    role: str = Field(..., examples=["user", "assistant"])
    content: str

class ChatMessageCreate(ChatMessageBase):
    pass

class ChatMessageResponse(ChatMessageBase):
    id: int
    chat_uuid: uuid.UUID
    thinking: Optional[str]
    project_id: int
    timestamp: datetime

    class Config:
        from_attributes = True # Replaces orm_mode = True

class ChatMessageWithUserResponse(ChatMessageResponse):
    user: Optional[UserEmailResponse] = None

    class Config:
        from_attributes = True
class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessageResponse]