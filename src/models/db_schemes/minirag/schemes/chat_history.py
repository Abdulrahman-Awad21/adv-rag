from .minirag_base import SQLAlchemyBase
from sqlalchemy import Column, Integer, DateTime, func, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import Index
import uuid # For potential application-level default if DB default is not preferred

class ChatHistory(SQLAlchemyBase):
    __tablename__ = "chat_histories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # If you prefer application-level default for UUID:
    # chat_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    # If using DB-level default (as in migration):
    chat_uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, server_default=func.gen_random_uuid())


    project_id = Column(Integer, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False) # "user" or "assistant"
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    project = relationship("Project", back_populates="chat_history_entries")

    __table_args__ = (
        Index('ix_chat_histories_project_id', project_id),
        Index('ix_chat_histories_timestamp', timestamp),
        Index('ix_chat_histories_chat_uuid', chat_uuid, unique=True),
    )
    