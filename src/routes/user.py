from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List

from services.UserService import UserService
from config.settings import get_settings, Settings
from .dependencies import require_admin_role
from .schemes.user import UserInDB, UserCreate, UserUpdate

user_router = APIRouter(
    prefix="/api/v1/users",
    tags=["api_v1", "users", "admin"],
    dependencies=[Depends(require_admin_role)] # Protect all routes in this file
)

def get_user_service(request: Request, settings: Settings = Depends(get_settings)) -> UserService:
    return UserService(db_client=request.app.db_client, app_settings=settings)

@user_router.post("/", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
async def create_new_user(user_data: UserCreate, service: UserService = Depends(get_user_service)):
    user = await service.create_user(user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    return user

@user_router.get("/", response_model=List[UserInDB])
async def read_users(skip: int = 0, limit: int = 100, service: UserService = Depends(get_user_service)):
    users = await service.get_all_users(skip=skip, limit=limit)
    return users

@user_router.put("/{user_id}", response_model=UserInDB)
async def update_existing_user(user_id: int, user_data: UserUpdate, service: UserService = Depends(get_user_service)):
    user = await service.update_user(user_id, user_data)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@user_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_user(user_id: int, service: UserService = Depends(get_user_service)):
    success = await service.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return None