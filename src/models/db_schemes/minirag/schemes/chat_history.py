from .minirag_base import SQLAlchemyBase
from sqlalchemy import Column, Integer, DateTime, func, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import Index
import uuid

class ChatHistory(SQLAlchemyBase):
    __tablename__ = "chat_histories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, server_default=func.gen_random_uuid())

    project_id = Column(Integer, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    # Add a user_id foreign key. Make it nullable to support old messages that didn't have a user.
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True) 

    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    project = relationship("Project", back_populates="chat_history_entries")
    # Add relationship to the User model
    user = relationship("User") 

    __table_args__ = (
        Index('ix_chat_histories_project_id', project_id),
        Index('ix_chat_histories_user_id', user_id), # Index the new column
        Index('ix_chat_histories_timestamp', timestamp),
        Index('ix_chat_histories_chat_uuid', chat_uuid, unique=True),
    )
    