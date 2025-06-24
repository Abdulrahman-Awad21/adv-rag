from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError

from config.settings import get_settings, Settings
from services.AuthService import AuthService
from .schemes.auth import TokenData
from models.db_schemes import User

# This tells FastAPI where to look for the token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/token")

def get_auth_service(settings: Settings = Depends(get_settings), request: Request = None) -> AuthService:
    """Dependency to get an instance of the AuthService."""
    if request and hasattr(request.app, 'db_client'):
        return AuthService(db_client=request.app.db_client, app_settings=settings)
    raise RuntimeError("Application state `db_client` not found.")

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
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except (JWTError, ValidationError):
        raise credentials_exception
    
    user = await auth_service.get_user(username=token_data.username)
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