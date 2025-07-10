from .BaseDataModel import BaseDataModel
from .db_schemes.minirag.schemes import ChatHistory, Project
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from typing import List, Optional

class ChatHistoryModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        return instance

    # Method now requires user_id
    async def add_message(self, project_id: int, user_id: int, role: str, content: str) -> ChatHistory:
        async with self.db_client() as session:
            async with session.begin():
                chat_message = ChatHistory(
                    project_id=project_id,
                    user_id=user_id, # Save the user ID with the message
                    role=role,
                    content=content
                )
                session.add(chat_message)
            await session.commit()
            await session.refresh(chat_message)
        return chat_message

    # Method now requires user_id to fetch history
    async def get_chat_history_for_project_and_user(
        self, 
        project_id: int,
        user_id: int,
        limit: int = 100, 
        offset: int = 0
    ) -> List[ChatHistory]:
        async with self.db_client() as session:
            stmt = (
                select(ChatHistory)
                .where(ChatHistory.project_id == project_id, ChatHistory.user_id == user_id) # Filter by user
                .order_by(ChatHistory.timestamp.asc())
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(stmt)
            messages = result.scalars().all()
        return messages

    async def delete_chat_history_for_project(self, project_id: int) -> int:
        async with self.db_client() as session:
            async with session.begin():
                stmt = ChatHistory.__table__.delete().where(ChatHistory.project_id == project_id)
                result = await session.execute(stmt)
            await session.commit()
            return result.rowcount
        