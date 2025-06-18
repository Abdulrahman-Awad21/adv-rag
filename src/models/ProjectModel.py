from .BaseDataModel import BaseDataModel
from .db_schemes import Project
from sqlalchemy.future import select
from sqlalchemy import func

class ProjectModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.db_client = db_client

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        return instance

    async def create_project(self, project: Project):
        async with self.db_client() as session:
            async with session.begin():
                session.add(project)
            await session.commit()
            await session.refresh(project)
        return project

    async def get_project_or_create_one(self, project_id: int): # ✅ UPDATED: project_id type hint to int
        async with self.db_client() as session:
            async with session.begin():
                query = select(Project).where(Project.project_id == project_id)
                result = await session.execute(query)
                project_record = result.scalar_one_or_none()
                
                if project_record is None:
                    # This assumes that if a project with the given integer 'project_id'
                    # is not found, a new project should be created, attempting to use
                    # this 'project_id' as its primary key.
                    # This implies Project.project_id in the DB schema is not autoincrementing,
                    # or the DB allows specifying the PK for an autoincrementing field on insert
                    # if the value is new.
                    # If Project.project_id IS autoincrementing and the DB assigns it,
                    # then `Project()` should be used and the returned project will have a DB-assigned ID.
                    # For now, matching the apparent intent of using the passed ID:
                    project_to_be_created = Project(project_id=project_id)
                    project_record = await self.create_project(project=project_to_be_created)
                
                return project_record

    async def get_all_projects(self, page: int=1, page_size: int=10):
        async with self.db_client() as session:
            async with session.begin():
                total_documents_query = select(func.count(Project.project_id))
                total_documents_result = await session.execute(total_documents_query)
                total_documents = total_documents_result.scalar_one()

                total_pages = total_documents // page_size
                if total_documents % page_size > 0:
                    total_pages += 1

                query = select(Project).offset((page - 1) * page_size).limit(page_size)
                projects_result = await session.execute(query)
                projects = projects_result.scalars().all()

                return projects, total_pages
            
    async def get_all_projects_for_view(self, page: int=1, page_size: int=10):
        async with self.db_client() as session:
            async with session.begin():
                count_query = select(func.count(Project.project_id))
                total_documents_result = await session.execute(count_query)
                total_documents = total_documents_result.scalar_one()

                total_pages = total_documents // page_size
                if total_documents % page_size > 0:
                    total_pages += 1

                query = select(Project).offset((page - 1) * page_size).limit(page_size)
                result = await session.execute(query) 
                projects = result.scalars().all()     

                return projects, total_pages
            