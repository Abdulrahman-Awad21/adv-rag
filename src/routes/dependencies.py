# FILE: src/routes/dependencies.py

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError, EmailStr
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from config.settings import get_settings, Settings
from services.AuthService import AuthService
from .schemes.auth import TokenData
from models.db_schemes import User, Project
from models.db_schemes.minirag.schemes.project_access import project_access_table

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/token")

def get_auth_service(request: Request, settings: Settings = Depends(get_settings)) -> AuthService:
    return AuthService(db_client=request.app.db_client, app_settings=settings)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
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
    if current_user.role not in ["uploader", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted. Requires 'uploader' or 'admin' role.",
        )
    return current_user

async def require_admin_role(current_user: User = Depends(get_current_user)) -> User:
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
) -> Project:
    """
    Gets a project by UUID and verifies access in a single, atomic database query.
    This is the definitive, robust way to handle this authorization check.
    """
    async with request.app.db_client() as session:
        if current_user.role == "admin":
            stmt = select(Project).where(Project.project_uuid == project_uuid)
        else:
            stmt = (
                select(Project)
                .outerjoin(project_access_table, Project.project_id == project_access_table.c.project_id)
                .where(
                    Project.project_uuid == project_uuid,
                    or_(
                        Project.owner_id == current_user.id,
                        project_access_table.c.user_id == current_user.id
                    )
                )
                .distinct()
            )
        
        # Eagerly load relationships needed by the endpoints
        stmt = stmt.options(
            selectinload(Project.authorized_users),
            selectinload(Project.owner) # Eagerly load the owner for email notifications
        )

        result = await session.execute(stmt)
        project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not authorized to access project {project_uuid}"
        )
        
    return project
