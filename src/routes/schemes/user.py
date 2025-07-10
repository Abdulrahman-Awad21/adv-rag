from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    role: str = Field(default="chatter", examples=["admin", "uploader", "chatter"])

class UserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None

class SetInitialPassword(BaseModel):
    token: str
    new_password: str = Field(min_length=8)
    
class UserInDB(UserBase):
    id: int
    role: str
    is_active: bool
    password_change_required: bool
    created_at: datetime  # <--- THIS IS THE FIX. Add the created_at field.

    class Config:
        from_attributes = True

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(min_length=8)