from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List

from services.UserService import UserService
from services.EmailService import EmailService
from config.settings import get_settings, Settings
from .dependencies import require_admin_role, get_current_user
from .schemes.user import UserInDB, UserCreate, UserUpdate, PasswordChange
from models.db_schemes import User

user_router = APIRouter(
    prefix="/api/v1/users",
    tags=["api_v1", "users"],
)

def get_user_service(request: Request, settings: Settings = Depends(get_settings)) -> UserService:
    return UserService(
        db_client=request.app.db_client,
        app_settings=settings,
        email_service=request.app.email_service
    )

@user_router.post("/", response_model=UserInDB, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin_role)])
async def create_new_user(user_data: UserCreate, service: UserService = Depends(get_user_service)):
    user = await service.create_user(user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    return user

@user_router.get("/", response_model=List[UserInDB], dependencies=[Depends(require_admin_role)])
async def read_users(skip: int = 0, limit: int = 100, service: UserService = Depends(get_user_service)):
    users = await service.get_all_users(skip=skip, limit=limit)
    return users

@user_router.put("/{user_id}", response_model=UserInDB, dependencies=[Depends(require_admin_role)])
async def update_existing_user(user_id: int, user_data: UserUpdate, service: UserService = Depends(get_user_service)):
    user = await service.update_user(user_id, user_data)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@user_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin_role)])
async def delete_existing_user(user_id: int, service: UserService = Depends(get_user_service)):
    success = await service.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return None

@user_router.post("/me/change-password", status_code=status.HTTP_200_OK)
async def user_change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service)
):
    success = await service.change_password(current_user, password_data)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password")
    return {"message": "Password changed successfully."}

@user_router.get("/me", response_model=UserInDB)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user