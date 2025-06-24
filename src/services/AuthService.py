import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

from config.settings import Settings
from models.db_schemes import User
from models.ProjectModel import ProjectModel

logger = logging.getLogger('uvicorn.error')

class AuthService:
    def __init__(self, db_client: sessionmaker, app_settings: Settings):
        self.db_client = db_client
        self.app_settings = app_settings
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verifies a plain password against a hashed one."""
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hashes a plain password."""
        return self.pwd_context.hash(password)

    async def get_user(self, username: str) -> Optional[User]:
        """Retrieves a user by username from the database."""
        async with self.db_client() as session:
            result = await session.execute(select(User).where(User.username == username))
            return result.scalar_one_or_none()

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Creates a new JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.app_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.app_settings.SECRET_KEY, algorithm=self.app_settings.ALGORITHM)
        return encoded_jwt

    async def is_project_owner(self, user: User, project_id: int) -> bool:
        """Checks if the given user is the owner of the project."""
        if user.role == 'admin':
            return True # Admins can access all projects
        
        project_model = await ProjectModel.create_instance(self.db_client)
        project = await project_model.get_project_or_create_one(project_id) # This should just be a get, not create
        
        if project and project.owner_id == user.id:
            return True
        return False