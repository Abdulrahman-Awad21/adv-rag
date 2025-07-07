# FILE: src/routes/project.py

from fastapi import APIRouter, Depends, Request, Response, status
from typing import List, Dict

from models.db_schemes import User, Project
from routes.schemes.chat import ChatMessageCreate, ChatMessageResponse
from services.ProjectService import ProjectService
from .dependencies import get_current_user, require_uploader_role, get_project_from_uuid_and_verify_access

project_router = APIRouter(
    prefix="/api/v1/projects",
    tags=["api_v1", "projects"], 
    dependencies=[Depends(get_current_user)] # Protect all project routes
)

def get_project_service(request: Request) -> ProjectService:
    """Dependency provider for ProjectService."""
    return ProjectService(db_client=request.app.db_client)

@project_router.post("/", response_model=Dict[str, str], status_code=status.HTTP_201_CREATED)
async def create_new_project(
    service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(require_uploader_role) # Only uploaders/admins can create
):
    new_project = await service.create_project(project_name="New Project", owner=current_user)
    return {"project_uuid": str(new_project.project_uuid)}

@project_router.get("/", response_model=List[Dict[str, str]]) 
async def list_projects(
    service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user)
):
    projects = await service.list_all_projects_for_user(user=current_user)
    # Return UUID for frontend use
    return [{"project_uuid": str(p.project_uuid)} for p in projects]

@project_router.post("/{project_uuid}/chat_history", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def add_project_chat_message(
    message: ChatMessageCreate,
    project: Project = Depends(get_project_from_uuid_and_verify_access),
    service: ProjectService = Depends(get_project_service)
):
    new_message = await service.add_chat_message(
        project_id=project.project_id, # Use internal integer ID for service
        role=message.role,
        content=message.content
    )
    return new_message

@project_router.get("/{project_uuid}/chat_history", response_model=List[ChatMessageResponse])
async def get_project_chat_messages(
    limit: int = 100,
    offset: int = 0,
    project: Project = Depends(get_project_from_uuid_and_verify_access),
    service: ProjectService = Depends(get_project_service)
):
    history = await service.get_chat_history(
        project_id=project.project_id, 
        limit=limit,
        offset=offset
    )
    return history

@project_router.delete("/{project_uuid}/chat_history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_project_chat_messages(
    project: Project = Depends(get_project_from_uuid_and_verify_access),
    service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(require_uploader_role) # Extra check for safety
):
    await service.clear_chat_history(project_id=project.project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)