# FILE: src/routes/schemes/project.py

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import UUID
from .user import UserInDB

# New schema for listing projects, for consistency
class ProjectListResponse(BaseModel):
    project_uuid: UUID

    class Config:
        from_attributes = True

# Schema for granting access to a project
class ProjectAccessRequest(BaseModel):
    email: EmailStr

# Schema for updating project settings
class ProjectSettingsUpdate(BaseModel):
    is_chat_history_enabled: Optional[bool] = None
    is_thinking_visible: Optional[bool] = None

# Schema for the detailed project response
class ProjectDetailsResponse(BaseModel):
    project_uuid: UUID
    owner_id: Optional[int] = None
    is_chat_history_enabled: bool
    is_thinking_visible: bool
    authorized_users: List[UserInDB] = []

    class Config:
        from_attributes = True
