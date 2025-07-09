from typing import List, Optional
from sqlalchemy.orm import sessionmaker, selectinload
from sqlalchemy.future import select
from sqlalchemy import delete, update

from models.ProjectModel import ProjectModel
from models.ChatHistoryModel import ChatHistoryModel
from models.db_schemes import Project, ChatHistory, User
from models.db_schemes.minirag.schemes.project_access import project_access_table
from routes.schemes.project import ProjectSettingsUpdate


class ProjectService:
    def __init__(self, db_client: sessionmaker):
        self.db_client = db_client

    async def list_all_projects_for_user(self, user: User, page: int = 1, page_size: int = 1000) -> List[Project]:
        """
        Lists projects a user has access to.
        - Admins see all projects.
        - Uploaders see projects they own.
        - Chatters see projects they own OR have been granted access to.
        """
        async with self.db_client() as session:
            if user.role == "admin":
                query = select(Project)
            else:
                # Join to find projects where user is owner OR is in the access table
                query = (
                    select(Project)
                    .outerjoin(project_access_table)
                    .where(
                        (Project.owner_id == user.id) |
                        (project_access_table.c.user_id == user.id)
                    )
                    .distinct()
                )
            
            result = await session.execute(
                query.order_by(Project.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
            )
            return result.scalars().all()

    async def get_project_details(self, project: Project) -> Project:
        """Refreshes and returns project details, ensuring relationships are loaded."""
        async with self.db_client() as session:
            # Re-fetch the project with necessary relationships eagerly loaded
            # The `selectin` on the model already helps, but this is explicit.
            result = await session.execute(
                select(Project).where(Project.project_id == project.project_id).options(
                    selectinload(Project.authorized_users)
                )
            )
            return result.scalar_one_or_none()

    async def create_project(self, project_name: str, owner: User) -> Project:
        """Creates a new project owned by the given user."""
        project_model = await ProjectModel.create_instance(self.db_client)
        new_project = Project(owner_id=owner.id)
        return await project_model.create_project(new_project)
        
    async def add_chat_message(self, project: Project, role: str, content: str) -> Optional[ChatHistory]:
        """
        Adds a new message to a project's chat history, but only if history is enabled.
        """
        if not project.is_chat_history_enabled:
            return None # Do not save if history is disabled

        chat_history_model = await ChatHistoryModel.create_instance(self.db_client)
        return await chat_history_model.add_message(project_id=project.project_id, role=role, content=content)

    async def get_chat_history(self, project_id: int, limit: int = 100, offset: int = 0) -> List[ChatHistory]:
        """Retrieves the chat history for a specific project."""
        chat_history_model = await ChatHistoryModel.create_instance(self.db_client)
        return await chat_history_model.get_chat_history_for_project(project_id=project_id, limit=limit, offset=offset)

    async def clear_chat_history(self, project_id: int) -> int:
        """Deletes all chat history messages for a specific project."""
        chat_history_model = await ChatHistoryModel.create_instance(self.db_client)
        return await chat_history_model.delete_chat_history_for_project(project_id=project_id)
        
    async def update_project_settings(self, project: Project, settings: ProjectSettingsUpdate) -> Optional[Project]:
        """Updates the settings for a specific project."""
        update_data = settings.model_dump(exclude_unset=True)
        if not update_data:
            return project

        async with self.db_client() as session:
            stmt = update(Project).where(Project.project_id == project.project_id).values(**update_data)
            await session.execute(stmt)
            await session.commit()
            await session.refresh(project)
        return project

    async def grant_project_access(self, project: Project, target_user: User) -> bool:
        """Grants a user access to a project."""
        if target_user in project.authorized_users:
            return True # Already has access
        
        async with self.db_client() as session:
            project.authorized_users.append(target_user)
            session.add(project)
            await session.commit()
        return True
        
    async def revoke_project_access(self, project: Project, target_user: User) -> bool:
        """Revokes a user's access to a project."""
        if target_user not in project.authorized_users:
            return False # User doesn't have access to begin with

        async with self.db_client() as session:
            project.authorized_users.remove(target_user)
            session.add(project)
            await session.commit()
        return True
    