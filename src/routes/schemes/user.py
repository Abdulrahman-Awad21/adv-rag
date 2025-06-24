from pydantic import BaseModel, Field
from typing import Optional

class UserBase(BaseModel):
    username: str = Field(..., min_length=3)

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    role: str = Field(default="chatter", examples=["admin", "uploader", "chatter"])

class UserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserInDB(UserBase):
    id: int
    role: str
    is_active: bool

    class Config:
        from_attributes = True