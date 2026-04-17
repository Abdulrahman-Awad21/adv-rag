# src/routes/admin.py

from fastapi import APIRouter, Depends, Request, Header, HTTPException, status
from config.settings import Settings, get_settings
from services.AdminService import AdminService
from .dependencies import require_admin_role # Import the dependency
from models.db_schemes import User # Import User for type hinting

admin_router = APIRouter(
    prefix="/api/v1/admin",
    tags=["api_v1", "admin"], 
)

def get_admin_service(request: Request, app_settings: Settings = Depends(get_settings)) -> AdminService:
    """Dependency provider for AdminService."""
    return AdminService(
        db_engine=request.app.async_db_engine,
        db_client=request.app.db_client,
        app_settings=app_settings,
        email_service=request.app.email_service
    )

@admin_router.delete("/nuke-and-rebuild-db", summary="Perform a full system wipe and rebuild")
async def nuke_and_rebuild(
    service: AdminService = Depends(get_admin_service),
    # Use the dependency to ensure the user is an admin and get the user object
    current_user: User = Depends(require_admin_role) 
):
    """
    **DANGER ZONE: This is a highly destructive operation.**
    
    This endpoint will:
    1.  Delete ALL physical asset files from the disk.
    2.  Drop ALL tables from the public schema in the database.
    3.  **Immediately rebuild** the database schema from the application's models.
    4.  **Immediately re-provision** the initial admin user from environment variables.
    
    After this operation, the system will be in a clean, pristine state and is ready for
    immediate use. **No manual restart is required.**
    
    This endpoint is protected and can only be called by authenticated users with the 'admin' role.
    """
    result = await service.nuke_and_rebuild_db()
    return result