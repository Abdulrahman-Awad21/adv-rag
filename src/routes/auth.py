from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from config.settings import Settings, get_settings
from services.AuthService import AuthService
from .schemes.auth import Token

auth_router = APIRouter(
    prefix="/api/v1",
    tags=["api_v1", "authentication"],
)

def get_auth_service(settings: Settings = Depends(get_settings), request: "Request" = None) -> AuthService:
    # The 'request' is not directly used but ensures db_client is available on the app state
    # This is a common pattern to pass app-level state to dependencies
    from fastapi import Request as FastAPIRequest
    if request and hasattr(request.app, 'db_client'):
         return AuthService(db_client=request.app.db_client, app_settings=settings)
    raise RuntimeError("Application state `db_client` not found. Ensure lifespan is configured.")


@auth_router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings)
):
    user = await auth_service.get_user(form_data.username)
    if not user or not auth_service.verify_password(form_data.password, user.hashed_password) or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.username, "role": user.role, "uid": user.id}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}