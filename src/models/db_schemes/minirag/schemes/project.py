from .minirag_base import SQLAlchemyBase
from sqlalchemy import Column, Integer, DateTime, func, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import relationship
from sqlalchemy import text # Import text

# Import the association table
from .project_access import project_access_table

class Project(SQLAlchemyBase):

    __tablename__ = "projects"
    
    project_id = Column(Integer, primary_key=True, autoincrement=True)
    project_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    is_chat_history_enabled = Column(Boolean, nullable=False, default=True)
    # CORRECTED LINE: Use server_default to handle existing rows in the database
    is_thinking_visible = Column(Boolean, nullable=False, server_default=text('false'))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    owner = relationship("User", back_populates="projects")
    chunks = relationship("DataChunk", back_populates="project")
    assets = relationship("Asset", back_populates="project")
    chat_history_entries = relationship("ChatHistory", back_populates="project", cascade="all, delete-orphan", order_by="ChatHistory.timestamp")

    # New relationship to get users with access
    authorized_users = relationship(
        "User",
        secondary=project_access_table,
        back_populates="accessible_projects",
        lazy="selectin"
    )
    