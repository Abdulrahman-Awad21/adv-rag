import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets
import string

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

from config.settings import Settings
from models.db_schemes import User,Project
from models.ProjectModel import ProjectModel

logger = logging.getLogger('uvicorn.error')

class AuthService:
    def __init__(self, db_client: sessionmaker, app_settings: Settings):
        self.db_client = db_client
        self.app_settings = app_settings
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verifies a plain password against a hashed one."""
        if not plain_password or not hashed_password:
            return False
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hashes a plain password."""
        return self.pwd_context.hash(password)
    
    def generate_temporary_password(self, length: int = 12) -> str:
        """Generates a secure random password."""
        alphabet = string.ascii_letters + string.digits + string.punctuation
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        return password

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Retrieves a user by email from the database."""
        async with self.db_client() as session:
            result = await session.execute(select(User).where(User.email == email))
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
    
    def create_password_reset_token(self, email: str) -> str:
        """Creates a short-lived token for password reset."""
        expires = timedelta(minutes=15)
        return self.create_access_token(data={"sub": email, "type": "password_reset"}, expires_delta=expires)

    async def verify_password_reset_token(self, token: str) -> Optional[str]:
        """Verifies the password reset token and returns the user's email."""
        try:
            payload = jwt.decode(token, self.app_settings.SECRET_KEY, algorithms=[self.app_settings.ALGORITHM])
            if payload.get("type") != "password_reset":
                return None
            return payload.get("sub")
        except JWTError:
            return None
            
    def create_account_setup_token(self, email: str) -> str:
        """Creates a long-lived token for initial account setup."""
        expires = timedelta(hours=24) # Link is valid for 24 hours
        return self.create_access_token(data={"sub": email, "type": "account_setup"}, expires_delta=expires)
    
    async def verify_account_setup_token(self, token: str) -> Optional[str]:
        """Verifies the account setup token and returns the user's email."""
        try:
            payload = jwt.decode(token, self.app_settings.SECRET_KEY, algorithms=[self.app_settings.ALGORITHM])
            if payload.get("type") != "account_setup":
                return None
            return payload.get("sub")
        except JWTError:
            return None

    async def has_project_access(self, user: User, project: Project) -> bool:
        """
        Checks if a user has access to a project.
        Access is granted if:
        1. The user is an 'admin'.
        2. The user is the owner of the project.
        3. The user has been explicitly granted access in the project_access table.
        """
        # Admin has access to everything.
        if user.role == 'admin':
            return True
        
        # Project owner has access.
        if project and project.owner_id == user.id:
            return True
        
        # Check if user is in the authorized users list.
        # This check is efficient because of the `lazy="selectin"` loading strategy.
        if project and user in project.authorized_users:
            return True
        
        return False
    