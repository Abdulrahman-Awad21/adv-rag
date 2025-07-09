# FILE: src/routes/project.py

from fastapi import APIRouter, Depends, Request, Response, status, HTTPException
from typing import List

from models.db_schemes import User, Project
from services.ProjectService import ProjectService
from services.UserService import UserService
from .dependencies import get_current_user, require_uploader_role, get_project_from_uuid_and_verify_access
from .schemes.chat import ChatMessageCreate, ChatMessageResponse
from .schemes.project import ProjectAccessRequest, ProjectSettingsUpdate, ProjectDetailsResponse, ProjectListResponse # <-- Import new schema
from .schemes.user import UserInDB

project_router = APIRouter(
    prefix="/api/v1/projects",
    tags=["api_v1", "projects"], 
    dependencies=[Depends(get_current_user)]
)

def get_project_service(request: Request) -> ProjectService:
    return ProjectService(db_client=request.app.db_client)
    
def get_user_service(request: Request) -> UserService:
    return UserService(
        db_client=request.app.db_client,
        app_settings=None,
        email_service=None
    )

@project_router.post("/", response_model=ProjectListResponse, status_code=status.HTTP_201_CREATED) # Use ProjectListResponse
async def create_new_project(
    service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(require_uploader_role)
):
    new_project = await service.create_project(project_name="New Project", owner=current_user)
    return new_project # Return the full object, Pydantic will handle it

@project_router.get("/", response_model=List[ProjectListResponse]) # Use the new response model
async def list_projects(
    service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user)
):
    projects = await service.list_all_projects_for_user(user=current_user)
    return projects # Return the list of objects directly

@project_router.get("/{project_uuid}", response_model=ProjectDetailsResponse)
async def get_project_details(
    project: Project = Depends(get_project_from_uuid_and_verify_access),
    service: ProjectService = Depends(get_project_service)
):
    detailed_project = await service.get_project_details(project)
    return detailed_project

@project_router.put("/{project_uuid}/settings", response_model=ProjectDetailsResponse)
async def update_project_settings(
    settings: ProjectSettingsUpdate,
    project: Project = Depends(get_project_from_uuid_and_verify_access),
    service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(require_uploader_role)
):
    updated_project = await service.update_project_settings(project, settings)
    return updated_project

@project_router.post("/{project_uuid}/chat_history", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def add_project_chat_message(
    message: ChatMessageCreate,
    project: Project = Depends(get_project_from_uuid_and_verify_access),
    service: ProjectService = Depends(get_project_service)
):
    new_message = await service.add_chat_message(project=project, role=message.role, content=message.content)
    if new_message is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return new_message

@project_router.get("/{project_uuid}/chat_history", response_model=List[ChatMessageResponse])
async def get_project_chat_messages(
    limit: int = 100, offset: int = 0,
    project: Project = Depends(get_project_from_uuid_and_verify_access),
    service: ProjectService = Depends(get_project_service)
):
    return await service.get_chat_history(project_id=project.project_id, limit=limit, offset=offset)

# --- Access Control Routes ---

@project_router.post("/{project_uuid}/access", response_model=UserInDB)
async def grant_user_access_to_project(
    access_request: ProjectAccessRequest,
    project: Project = Depends(get_project_from_uuid_and_verify_access),
    project_service: ProjectService = Depends(get_project_service),
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_uploader_role)
):
    target_user = await user_service.get_user_by_email(access_request.email)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User to grant access to not found.")
    
    await project_service.grant_project_access(project, target_user)
    return target_user

@project_router.delete("/{project_uuid}/access/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_user_access_from_project(
    user_id: int,
    project: Project = Depends(get_project_from_uuid_and_verify_access),
    project_service: ProjectService = Depends(get_project_service),
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_uploader_role)
):
    target_user = await user_service.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User to revoke access from not found.")
        
    success = await project_service.revoke_project_access(project, target_user)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User did not have access to this project.")
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)
