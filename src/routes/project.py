from fastapi import APIRouter, Depends, Request, HTTPException, status, Response, Body
from typing import List, Dict

from models.db_schemes import User
from routes.schemes.chat import ChatMessageCreate, ChatMessageResponse
from services.ProjectService import ProjectService
from services.AuthService import AuthService # Import AuthService
from .dependencies import get_current_user, require_uploader_role # Import dependencies

project_router = APIRouter(
    prefix="/api/v1/projects",
    tags=["api_v1", "projects"], 
    dependencies=[Depends(get_current_user)] # Protect all project routes
)

def get_project_service(request: Request) -> ProjectService:
    """Dependency provider for ProjectService."""
    return ProjectService(db_client=request.app.db_client)

def get_auth_service(request: Request) -> AuthService:
    """Dependency provider for AuthService."""
    # This assumes get_settings() is available or settings are on the app
    from config.settings import get_settings
    return AuthService(db_client=request.app.db_client, app_settings=get_settings())

@project_router.post("/", response_model=Dict[str, str], status_code=status.HTTP_201_CREATED)
async def create_new_project(
    service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(require_uploader_role) # Only uploaders/admins can create
):
    # project_name can be passed in the body if needed, e.g., body: dict = Body(...)
    new_project = await service.create_project(project_name="New Project", owner=current_user)
    return {"project_id": str(new_project.project_id)}

@project_router.get("/", response_model=List[Dict[str, str]]) 
async def list_projects(
    service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user)
):
    projects = await service.list_all_projects_for_user(user=current_user)
    return [{"project_id": str(p.project_id)} for p in projects]

# Helper dependency to check project access
async def verify_project_access(
    project_id: int,
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user)
):
    has_access = await auth_service.is_project_owner(user=current_user, project_id=project_id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not authorized to access project {project_id}"
        )
    return True


@project_router.post("/{project_id}/chat_history", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_project_access)])
async def add_project_chat_message(
    project_id: int,
    message: ChatMessageCreate,
    service: ProjectService = Depends(get_project_service)
):
    # The verify_project_access dependency already checked ownership
    new_message = await service.add_chat_message(
        project_id=project_id, 
        role=message.role,
        content=message.content
    )
    return new_message

@project_router.get("/{project_id}/chat_history", response_model=List[ChatMessageResponse], dependencies=[Depends(verify_project_access)])
async def get_project_chat_messages(
    project_id: int,
    limit: int = 100,
    offset: int = 0,
    service: ProjectService = Depends(get_project_service)
):
    history = await service.get_chat_history(
        project_id=project_id, 
        limit=limit,
        offset=offset
    )
    return history

@project_router.delete("/{project_id}/chat_history", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_project_access)])
async def clear_project_chat_messages(
    project_id: int,
    service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(require_uploader_role) # Only owner/admin can clear
):
    await service.clear_chat_history(project_id=project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)