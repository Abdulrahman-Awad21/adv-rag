# FILE: src/models/db_schemes/adv_rag/schemes/project_access.py

from .adv_rag_base import SQLAlchemyBase
from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint


class ProjectAccess(SQLAlchemyBase):
    __tablename__ = 'project_access'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    project_id = Column(Integer, ForeignKey('projects.project_id', ondelete='CASCADE'), nullable=False)
    
    # Add a unique constraint to prevent duplicates.
    __table_args__ = (
        UniqueConstraint('user_id', 'project_id', name='_user_project_uc'),
    )