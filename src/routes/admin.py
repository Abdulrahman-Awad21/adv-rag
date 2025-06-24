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
        db_client=request.app.db_client, 
        app_settings=app_settings
    )

@admin_router.delete("/nuke-and-rebuild-db", summary="Perform a full system wipe and prepare for rebuild")
async def nuke_and_rebuild(
    service: AdminService = Depends(get_admin_service),
    # Use the dependency to ensure the user is an admin and get the user object
    current_user: User = Depends(require_admin_role) 
):
    """
    **DANGER ZONE: This is the most destructive operation available.**
    
    This endpoint will:
    1. Delete ALL physical asset files from the disk.
    2. Drop ALL core tables (`projects`, `assets`, `users`...), all dynamic `pgdata_*` tables,
       all `collection_*` tables, and the `alembic_version` table from the database.
    
    After this operation, you **MUST restart the application**. The startup script will
    then run `alembic upgrade head` to recreate the core tables in a pristine state.
    
    This endpoint is protected and can only be called by authenticated users with the 'admin' role.
    The old 'X-Reset-API-Key' is no longer needed as auth is handled by JWT.
    """
    result = await service.nuke_and_rebuild_db()
    return result