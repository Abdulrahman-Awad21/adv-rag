from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm

from config.settings import Settings, get_settings
from services.AuthService import AuthService
from services.UserService import UserService
from services.EmailService import EmailService
from .schemes.auth import Token
from .schemes.user import PasswordResetRequest, PasswordReset,SetInitialPassword

auth_router = APIRouter(
    prefix="/api/v1",
    tags=["api_v1", "authentication"],
)

# Dependency to get AuthService (FIXED a bug here)
def get_auth_service(request: Request, settings: Settings = Depends(get_settings)) -> AuthService:
    return AuthService(db_client=request.app.db_client, app_settings=settings)

# Dependency to get UserService
def get_user_service(request: Request, settings: Settings = Depends(get_settings)) -> UserService:
    return UserService(
        db_client=request.app.db_client, 
        app_settings=settings,
        email_service=request.app.email_service
    )

@auth_router.post("/token", response_model=Token)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings)
):
    # We use form_data.username as the email field
    user = await auth_service.get_user_by_email(form_data.username)
    if not user or not auth_service.verify_password(form_data.password, user.hashed_password) or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add the force_reset flag to the token if needed
    token_data = {
        "sub": user.email, 
        "role": user.role, 
        "uid": user.id,
        "force_reset": user.password_change_required
    }
    
    access_token = auth_service.create_access_token(
        data=token_data, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@auth_router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    password_request: PasswordResetRequest,
    auth_service: AuthService = Depends(get_auth_service),
    email_service: EmailService = Depends(lambda request: request.app.email_service, use_cache=True)
):
    user = await auth_service.get_user_by_email(password_request.email)
    if user:
        # Create a password reset token
        token = auth_service.create_password_reset_token(email=user.email)
        # The frontend URL needs to be configured or passed in
        frontend_url = "http://localhost:8501" # Replace with a configurable value later
        await email_service.send_password_reset_email(user.email, token, frontend_url)
    return {"message": "If an account with that email exists, a password reset link has been sent."}

@auth_router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    password_data: PasswordReset,
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service)
):
    email = await auth_service.verify_password_reset_token(password_data.token)
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    success = await user_service.reset_password(email, password_data.new_password)
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not reset password")
    
    return {"message": "Password has been reset successfully."}

@auth_router.post("/set-initial-password", status_code=status.HTTP_200_OK)
async def set_initial_password(
    password_data: SetInitialPassword,
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service)
):
    email = await auth_service.verify_account_setup_token(password_data.token)
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired setup token")

    success = await user_service.set_initial_password(email, password_data.new_password)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not set password. The account may already be active or does not exist.")
    
    return {"message": "Password has been set successfully. You can now log in."}
