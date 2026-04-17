# FILE: src/services/UserService.py

from typing import List, Optional
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError # Import the exception
import logging

from models.db_schemes import User
from services.AuthService import AuthService
from services.EmailService import EmailService
from routes.schemes.user import UserCreate, UserUpdate, PasswordChange
from config.settings import Settings

logger = logging.getLogger('uvicorn.error')

class UserService:
    def __init__(self, db_client: sessionmaker, app_settings: Settings, email_service: EmailService):
        self.db_client = db_client
        self.app_settings = app_settings
        self.auth_service = AuthService(db_client, app_settings)
        self.email_service = email_service

    async def create_initial_admin(self):
        """
        Creates the initial admin user from environment variables if it doesn't exist.
        This method is idempotent and safe from race conditions.
        """
        initial_email = self.app_settings.INITIAL_ADMIN_EMAIL.lower()
        initial_password = self.app_settings.INITIAL_ADMIN_PASSWORD

        if not initial_email or not initial_password:
            logger.info("Initial admin credentials not set in environment. Skipping creation.")
            return

        # First, check if the user already exists.
        existing_admin = await self.get_user_by_email(initial_email)
        if existing_admin:
            logger.info("Initial admin user already exists.")
            return

        logger.info("Initial admin user not found, attempting to create one.")
        hashed_password = self.auth_service.get_password_hash(initial_password)
        
        new_admin = User(
            email=initial_email,
            hashed_password=hashed_password,
            role="admin",
            password_change_required=False # Admin is ready to go
        )
        
        async with self.db_client() as session:
            session.add(new_admin)
            try:
                await session.commit()
                logger.info(f"Initial admin user '{initial_email}' created successfully.")
            except IntegrityError:
                # This block handles the race condition.
                await session.rollback()
                logger.warning(
                    f"A race condition occurred while creating the initial admin user '{initial_email}'. "
                    "Another worker likely created it. This is safe to ignore."
                )

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        async with self.db_client() as session:
            return await session.get(User, user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        return await self.auth_service.get_user_by_email(email)

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        async with self.db_client() as session:
            result = await session.execute(
                select(User).order_by(User.id).offset(skip).limit(limit)
            )
            return result.scalars().all()

    async def create_user(self, user_data: UserCreate) -> Optional[User]:
        normalized_email = user_data.email.lower()
        existing_user = await self.get_user_by_email(normalized_email)
        if existing_user:
            logger.warning(f"Attempted to create a user with an existing email: {normalized_email}")
            return None

        new_user = User(
            email=normalized_email,
            hashed_password=None,
            role=user_data.role,
            password_change_required=True
        )
        
        async with self.db_client() as session:
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
        
        setup_token = self.auth_service.create_account_setup_token(email=new_user.email)
        await self.email_service.send_account_setup_email(
            email_to=new_user.email,
            token=setup_token
        )

        return new_user

    async def set_initial_password(self, email: str, new_password: str) -> bool:
        user = await self.get_user_by_email(email)
        if not user or not user.password_change_required:
            return False
            
        new_hashed_password = self.auth_service.get_password_hash(new_password)
        async with self.db_client() as session:
            stmt = update(User).where(User.email == email).values(
                hashed_password=new_hashed_password,
                password_change_required=False
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def update_user(self, user_id: int, user_update_data: UserUpdate) -> Optional[User]:
        async with self.db_client() as session:
            user = await session.get(User, user_id)
            if not user:
                return None
            
            update_data = user_update_data.model_dump(exclude_unset=True)
            if not update_data:
                return user 

            stmt = update(User).where(User.id == user_id).values(**update_data)
            await session.execute(stmt)
            await session.commit()
            await session.refresh(user)
            return user

    async def change_password(self, user: User, password_data: PasswordChange) -> bool:
        if not self.auth_service.verify_password(password_data.current_password, user.hashed_password):
            return False
        
        new_hashed_password = self.auth_service.get_password_hash(password_data.new_password)
        
        async with self.db_client() as session:
            stmt = update(User).where(User.id == user.id).values(
                hashed_password=new_hashed_password,
                password_change_required=False
            )
            await session.execute(stmt)
            await session.commit()
        return True

    async def reset_password(self, email: str, new_password: str) -> bool:
        new_hashed_password = self.auth_service.get_password_hash(new_password)
        async with self.db_client() as session:
            stmt = update(User).where(User.email == email).values(
                hashed_password=new_hashed_password,
                password_change_required=False
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def delete_user(self, user_id: int) -> bool:
        async with self.db_client() as session:
            user = await session.get(User, user_id)
            if not user:
                return False
            
            await session.delete(user)
            await session.commit()
            return True