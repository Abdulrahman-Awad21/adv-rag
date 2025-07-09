from .minirag_base import SQLAlchemyBase
from sqlalchemy import Column, Integer, ForeignKey, Table, UniqueConstraint

# Define the association table for the many-to-many relationship
# between users and projects.
project_access_table = Table(
    'project_access',
    SQLAlchemyBase.metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
    Column('project_id', Integer, ForeignKey('projects.project_id', ondelete='CASCADE'), nullable=False),
    # Add a unique constraint to prevent a user from being granted access to the same project multiple times.
    UniqueConstraint('user_id', 'project_id', name='_user_project_uc')
)
