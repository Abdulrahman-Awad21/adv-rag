from .minirag_base import SQLAlchemyBase
from sqlalchemy import Column, Integer, DateTime, func, ForeignKey # Add ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import relationship

class Project(SQLAlchemyBase):

    __tablename__ = "projects"
    
    project_id = Column(Integer, primary_key=True, autoincrement=True)
    project_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Allow null for legacy/system projects

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    owner = relationship("User", back_populates="projects")
    chunks = relationship("DataChunk", back_populates="project")
    assets = relationship("Asset", back_populates="project")
    chat_history_entries = relationship("ChatHistory", back_populates="project", cascade="all, delete-orphan", order_by="ChatHistory.timestamp")