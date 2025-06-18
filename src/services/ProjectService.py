from typing import List
from sqlalchemy.orm import sessionmaker

from models.ProjectModel import ProjectModel
from models.ChatHistoryModel import ChatHistoryModel
from models.db_schemes import Project, ChatHistory # For type hinting

class ProjectService:
    def __init__(self, db_client: sessionmaker):
        self.db_client = db_client

    async def list_all_projects(self, page: int = 1, page_size: int = 1000) -> List[Project]:
        """Lists all projects from the database."""
        project_model = await ProjectModel.create_instance(self.db_client)
        projects, _ = await project_model.get_all_projects_for_view(page=page, page_size=page_size)
        return projects

    async def get_or_create_project(self, project_id: int) -> Project:
        """Retrieves a project by its ID, creating it if it doesn't exist."""
        project_model = await ProjectModel.create_instance(self.db_client)
        return await project_model.get_project_or_create_one(project_id=project_id)
        
    async def add_chat_message(self, project_id: int, role: str, content: str) -> ChatHistory:
        """Adds a new message to a project's chat history."""
        chat_history_model = await ChatHistoryModel.create_instance(self.db_client)
        return await chat_history_model.add_message(project_id=project_id, role=role, content=content)

    async def get_chat_history(self, project_id: int, limit: int = 100, offset: int = 0) -> List[ChatHistory]:
        """Retrieves the chat history for a specific project."""
        chat_history_model = await ChatHistoryModel.create_instance(self.db_client)
        return await chat_history_model.get_chat_history_for_project(project_id=project_id, limit=limit, offset=offset)

    async def clear_chat_history(self, project_id: int) -> int:
        """Deletes all chat history messages for a specific project."""
        chat_history_model = await ChatHistoryModel.create_instance(self.db_client)
        return await chat_history_model.delete_chat_history_for_project(project_id=project_id)