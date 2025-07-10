from .minirag_base import SQLAlchemyBase
from sqlalchemy import Column, Integer, DateTime, func, String, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy import Index

# Import the association table
from .project_access import project_access_table

class User(SQLAlchemyBase):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True) 
    role = Column(String, nullable=False, default="chatter")
    is_active = Column(Boolean, default=True)
    
    password_change_required = Column(Boolean, default=True, nullable=False) 

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    projects = relationship("Project", back_populates="owner")
    
    # New relationship to get projects a user can access
    accessible_projects = relationship(
        "Project",
        secondary=project_access_table,
        back_populates="authorized_users"
    )
    