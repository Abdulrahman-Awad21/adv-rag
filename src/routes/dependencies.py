from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError, EmailStr
from sqlalchemy import select

from config.settings import get_settings, Settings
from services.AuthService import AuthService
from .schemes.auth import TokenData
from models.ProjectModel import ProjectModel
from models.db_schemes import User, Project
from sqlalchemy.orm import selectinload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/token")

def get_auth_service(request: Request, settings: Settings = Depends(get_settings)) -> AuthService:
    """Dependency to get an instance of the AuthService."""
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
        email: EmailStr = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except (JWTError, ValidationError):
        raise credentials_exception
    
    user = await auth_service.get_user_by_email(email=token_data.email)
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

async def get_project_from_uuid_and_verify_access(
    project_uuid: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
) -> Project:
    """
    Dependency that gets a project by its UUID, verifies the current user has access,
    and returns the project object.
    """
    # Use selectinload to eagerly load the authorized_users relationship
    # This avoids extra database queries when checking for access.
    async with request.app.db_client() as session:
        stmt = (
            select(Project)
            .where(Project.project_uuid == project_uuid)
            .options(selectinload(Project.authorized_users))
        )
        result = await session.execute(stmt)
        project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Use the new centralized access control logic
    has_access = await auth_service.has_project_access(user=current_user, project=project)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not authorized to access project {project_uuid}"
        )
    return project
