from .BaseDataModel import BaseDataModel
from .db_schemes.illa_rag.schemes import ChatHistory, Project
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from typing import List, Optional
from datetime import datetime

class ChatHistoryModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        return instance
    async def add_message(self, project_id: int, user_id: int, role: str, content: str, thinking: Optional[str] = None) -> ChatHistory:
        """
        Adds a new chat message to the database within a single transaction.
        """
        async with self.db_client() as session:
            # The 'async with session.begin()' block handles the entire
            # transaction lifecycle, including commit and rollback.
            async with session.begin():
                chat_message = ChatHistory(
                    project_id=project_id,
                    user_id=user_id,
                    role=role,
                    content=content,
                    thinking=thinking
                )
                session.add(chat_message)
                # We need to flush to get the ID before the transaction ends
                await session.flush()
                # Refresh to load all attributes, like UUIDs and timestamps
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
    
    async def get_all_chat_history_for_project(
        self,
        project_id: int,
        user_id: Optional[int] = None,
        chat_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        order: str = 'desc',
        limit: int = 200,
        offset: int = 0
    ) -> List[ChatHistory]:
        """
        Fetches all chat messages for a specific project, with optional filters.
        """
        async with self.db_client() as session:
            stmt = select(ChatHistory).where(ChatHistory.project_id == project_id)

            # Apply optional filters
            if user_id:
                stmt = stmt.where(ChatHistory.user_id == user_id)
            if chat_id:
                stmt = stmt.where(ChatHistory.id == chat_id)
            if start_time:
                stmt = stmt.where(ChatHistory.timestamp >= start_time)
            if end_time:
                stmt = stmt.where(ChatHistory.timestamp <= end_time)

            # Apply ordering
            if order == 'asc':
                stmt = stmt.order_by(ChatHistory.timestamp.asc())
            else:
                stmt = stmt.order_by(ChatHistory.timestamp.desc())

            # Eagerly load user details and apply pagination
            stmt = stmt.options(joinedload(ChatHistory.user)).offset(offset).limit(limit)
            
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
        