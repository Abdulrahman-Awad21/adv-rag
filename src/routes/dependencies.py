from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError, EmailStr

from config.settings import get_settings, Settings
from services.AuthService import AuthService
from .schemes.auth import TokenData
from models.db_schemes import User

# This tells FastAPI where to look for the token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/token")

def get_auth_service(request: Request, settings: Settings = Depends(get_settings)) -> AuthService:
    """Dependency to get an instance of the AuthService."""
    # This was fixed in the previous step and is correct.
    return AuthService(db_client=request.app.db_client, app_settings=settings)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """
    Decodes the JWT token, validates it, and returns the corresponding user from the database.
    This is the primary dependency for requiring a user to be logged in.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # The "sub" (subject) claim holds the user's email
        email: EmailStr = payload.get("sub")
        if email is None:
            raise credentials_exception
        
        # We can create a TokenData object for consistency if needed, but we already have the email
        token_data = TokenData(email=email)

    except (JWTError, ValidationError):
        raise credentials_exception
    
    # --- THIS IS THE FIX ---
    # Call the correct method `get_user_by_email` and pass the email from the token.
    user = await auth_service.get_user_by_email(email=token_data.email)
    # --- END OF FIX ---

    if user is None or not user.is_active:
        raise credentials_exception
    return user

async def require_uploader_role(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency that requires the current user to have 'uploader' or 'admin' role.
    """
    if current_user.role not in ["uploader", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted. Requires 'uploader' or 'admin' role.",
        )
    return current_user

async def require_admin_role(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency that requires the current user to have the 'admin' role.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted. Requires 'admin' role.",
        )
    return current_user