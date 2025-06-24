from typing import List, Optional
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import delete, update

from models.db_schemes import User
from services.AuthService import AuthService
from routes.schemes.user import UserCreate, UserUpdate
from config.settings import Settings

class UserService:
    def __init__(self, db_client: sessionmaker, app_settings: Settings):
        self.db_client = db_client
        self.app_settings = app_settings
        self.auth_service = AuthService(db_client, app_settings)

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        async with self.db_client() as session:
            return await session.get(User, user_id)

    async def get_user_by_username(self, username: str) -> Optional[User]:
        return await self.auth_service.get_user(username)

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        async with self.db_client() as session:
            result = await session.execute(
                select(User).offset(skip).limit(limit)
            )
            return result.scalars().all()

    async def create_user(self, user_data: UserCreate) -> User:
        existing_user = await self.get_user_by_username(user_data.username)
        if existing_user:
            return None # Or raise an exception

        hashed_password = self.auth_service.get_password_hash(user_data.password)
        new_user = User(
            username=user_data.username,
            hashed_password=hashed_password,
            role=user_data.role
        )
        async with self.db_client() as session:
            async with session.begin():
                session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
        return new_user

    async def update_user(self, user_id: int, user_update_data: UserUpdate) -> Optional[User]:
        async with self.db_client() as session:
            async with session.begin():
                user = await session.get(User, user_id)
                if not user:
                    return None
                
                update_data = user_update_data.model_dump(exclude_unset=True)
                if not update_data:
                    return user # Nothing to update

                stmt = update(User).where(User.id == user_id).values(**update_data)
                await session.execute(stmt)

            await session.commit()
            updated_user = await session.get(User, user_id)
            return updated_user

    async def delete_user(self, user_id: int) -> bool:
        async with self.db_client() as session:
            async with session.begin():
                user = await session.get(User, user_id)
                if not user:
                    return False
                
                stmt = delete(User).where(User.id == user_id)
                result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0