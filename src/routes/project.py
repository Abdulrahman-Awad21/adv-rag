from fastapi import APIRouter, Depends, Request, HTTPException, status, Response
from typing import List

from models import ResponseSignal
from routes.schemes.chat import ChatMessageCreate, ChatMessageResponse
from services.ProjectService import ProjectService

project_router = APIRouter(
    prefix="/api/v1/projects",
    tags=["api_v1", "projects"], 
)

def get_project_service(request: Request) -> ProjectService:
    """Dependency provider for ProjectService."""
    return ProjectService(db_client=request.app.db_client)

@project_router.get("/", response_model=List[str]) 
async def list_projects(service: ProjectService = Depends(get_project_service)):
    projects = await service.list_all_projects()
    return [str(p.project_id) for p in projects]

@project_router.post("/{project_id}/chat_history", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def add_project_chat_message(
    project_id: int,
    message: ChatMessageCreate,
    service: ProjectService = Depends(get_project_service)
):
    db_project = await service.get_or_create_project(project_id=project_id)
    if not db_project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found and could not be created.")

    new_message = await service.add_chat_message(
        project_id=db_project.project_id, 
        role=message.role,
        content=message.content
    )
    return new_message

@project_router.get("/{project_id}/chat_history", response_model=List[ChatMessageResponse])
async def get_project_chat_messages(
    project_id: int,
    limit: int = 100,
    offset: int = 0,
    service: ProjectService = Depends(get_project_service)
):
    db_project = await service.get_or_create_project(project_id=project_id)
    if not db_project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found.")

    history = await service.get_chat_history(
        project_id=db_project.project_id, 
        limit=limit,
        offset=offset
    )
    return history

@project_router.delete("/{project_id}/chat_history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_project_chat_messages(
    project_id: int,
    service: ProjectService = Depends(get_project_service)
):
    db_project = await service.get_or_create_project(project_id=project_id)
    if not db_project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found.")

    await service.clear_chat_history(project_id=db_project.project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)