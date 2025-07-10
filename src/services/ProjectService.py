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
        async with self.db_client() as session:
            if user.role == "admin":
                query = select(Project)
            else:
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
        async with self.db_client() as session:
            result = await session.execute(
                select(Project).where(Project.project_id == project.project_id).options(
                    selectinload(Project.authorized_users)
                )
            )
            return result.scalar_one_or_none()

    async def create_project(self, project_name: str, owner: User) -> Project:
        project_model = await ProjectModel.create_instance(self.db_client)
        new_project = Project(owner_id=owner.id)
        return await project_model.create_project(new_project)
        
    async def add_chat_message(self, project_id: int, user: User, role: str, content: str) -> ChatHistory:
        chat_history_model = await ChatHistoryModel.create_instance(self.db_client)
        return await chat_history_model.add_message(project_id=project_id, user_id=user.id, role=role, content=content)

    async def get_chat_history(self, project_id: int, user: User, limit: int = 100, offset: int = 0) -> List[ChatHistory]:
        chat_history_model = await ChatHistoryModel.create_instance(self.db_client)
        return await chat_history_model.get_chat_history_for_project_and_user(
            project_id=project_id, user_id=user.id, limit=limit, offset=offset
        )

    async def clear_chat_history(self, project_id: int) -> int:
        chat_history_model = await ChatHistoryModel.create_instance(self.db_client)
        return await chat_history_model.delete_chat_history_for_project(project_id=project_id)
        
    async def update_project_settings(self, project: Project, settings: ProjectSettingsUpdate) -> Optional[Project]:
        update_data = settings.model_dump(exclude_unset=True)
        if not update_data:
            return project

        async with self.db_client() as session:
            # <-- FIX: Use the project's ID to get a "live" instance within this session.
            project_in_session = await session.get(Project, project.project_id)
            if not project_in_session:
                return None # Should not happen if dependency worked, but good practice

            stmt = update(Project).where(Project.project_id == project_in_session.project_id).values(**update_data)
            await session.execute(stmt)
            await session.commit()
            await session.refresh(project_in_session) # Refresh the live instance
            return project_in_session

    async def grant_project_access(self, project: Project, target_user: User) -> bool:
        async with self.db_client() as session:
            # <-- FIX: Get live, session-managed instances of both project and user.
            project_in_session = await session.get(Project, project.project_id, options=[selectinload(Project.authorized_users)])
            target_user_in_session = await session.get(User, target_user.id)

            if not project_in_session or not target_user_in_session:
                return False # Should not happen

            if target_user_in_session in project_in_session.authorized_users:
                return True
            
            project_in_session.authorized_users.append(target_user_in_session)
            session.add(project_in_session)
            await session.commit()
        return True
        
    async def revoke_project_access(self, project: Project, target_user: User) -> bool:
        async with self.db_client() as session:
            # <-- FIX: Get a live, session-managed instance of the project.
            project_in_session = await session.get(Project, project.project_id, options=[selectinload(Project.authorized_users)])
            target_user_in_session = await session.get(User, target_user.id)

            if not project_in_session or not target_user_in_session:
                return False

            if target_user_in_session not in project_in_session.authorized_users:
                return False

            project_in_session.authorized_users.remove(target_user_in_session)
            session.add(project_in_session)
            await session.commit()
        return True
    