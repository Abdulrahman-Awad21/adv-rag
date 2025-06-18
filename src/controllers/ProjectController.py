from .BaseController import BaseController
from fastapi import UploadFile
from models import ResponseSignal
import os
from models.ChatHistoryModel import ChatHistoryModel
from models.db_schemes.minirag.schemes import ChatHistory # For type hinting
from typing import List

class ProjectController(BaseController):
    
    def __init__(self):
        super().__init__()

    def get_project_path(self, project_id: str):
        project_dir = os.path.join(
            self.files_dir,
            str(project_id)
        )

        if not os.path.exists(project_dir):
            os.makedirs(project_dir)

        return project_dir
    
    async def add_chat_message(self, db_client: object, project_id: int, role: str, content: str) -> ChatHistory:
        chat_history_model = await ChatHistoryModel.create_instance(db_client)
        return await chat_history_model.add_message(project_id=project_id, role=role, content=content)
    async def get_project_chat_history(
        self, 
        db_client: object, 
        project_id: int, 
        limit: int = 100, 
        offset: int = 0
        ) -> List[ChatHistory]:

        chat_history_model = await ChatHistoryModel.create_instance(db_client)
        return await chat_history_model.get_chat_history_for_project(
            project_id=project_id, limit=limit, offset=offset)

    async def clear_project_chat_history(self, db_client: object, project_id: int) -> int:
        chat_history_model = await ChatHistoryModel.create_instance(db_client)
        return await chat_history_model.delete_chat_history_for_project(project_id=project_id)


    
