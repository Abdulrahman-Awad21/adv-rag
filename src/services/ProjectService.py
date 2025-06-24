from typing import List
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

from models.ProjectModel import ProjectModel
from models.ChatHistoryModel import ChatHistoryModel
from models.db_schemes import Project, ChatHistory, User # Import User

class ProjectService:
    def __init__(self, db_client: sessionmaker):
        self.db_client = db_client

    async def list_all_projects_for_user(self, user: User, page: int = 1, page_size: int = 1000) -> List[Project]:
        """Lists all projects owned by a specific user. Admins get all projects."""
        project_model = await ProjectModel.create_instance(self.db_client)
        
        async with self.db_client() as session:
            if user.role == "admin":
                query = select(Project)
            else:
                query = select(Project).where(Project.owner_id == user.id)
            
            result = await session.execute(query.offset((page - 1) * page_size).limit(page_size))
            return result.scalars().all()

    async def get_project_by_id(self, project_id: int) -> Project:
        """Retrieves a project by its ID, without creating it."""
        async with self.db_client() as session:
            # Using session.get is efficient for primary key lookups
            project = await session.get(Project, project_id)
        return project

    async def create_project(self, project_name: str, owner: User) -> Project:
        """Creates a new project owned by the given user."""
        project_model = await ProjectModel.create_instance(self.db_client)
        new_project = Project(
            # project_name could be added to schema if desired
            owner_id=owner.id
        )
        # Note: project_id is autoincremented by the DB
        return await project_model.create_project(new_project)
        
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