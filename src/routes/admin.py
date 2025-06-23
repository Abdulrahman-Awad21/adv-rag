# src/routes/admin.py

from fastapi import APIRouter, Depends, Request, Header, HTTPException, status
from config.settings import Settings, get_settings
from services.AdminService import AdminService

admin_router = APIRouter(
    prefix="/api/v1/admin",
    tags=["api_v1", "admin"], 
)

def get_admin_service(request: Request, app_settings: Settings = Depends(get_settings)) -> AdminService:
    """Dependency provider for AdminService."""
    # Note: vectordb_client is no longer needed for this simpler reset logic
    return AdminService(
        db_client=request.app.db_client, 
        app_settings=app_settings
    )

@admin_router.delete("/nuke-and-rebuild-db", summary="Perform a full system wipe and prepare for rebuild")
async def nuke_and_rebuild(
    service: AdminService = Depends(get_admin_service),
    app_settings: Settings = Depends(get_settings),
    x_reset_api_key: str = Header(..., description="The secret API key to authorize the reset operation.")
):
    """
    **DANGER ZONE: This is the most destructive operation available.**
    
    This endpoint will:
    1. Delete ALL physical asset files from the disk.
    2. Drop ALL core tables (`projects`, `assets`...), all dynamic `pgdata_*` tables,
       all `collection_*` tables, and the `alembic_version` table from the database.
    
    After this operation, you **MUST restart the application**. The startup script will
    then run `alembic upgrade head` to recreate the core tables in a pristine state.
    """
    if x_reset_api_key != app_settings.ADMIN_RESET_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-Reset-API-Key."
        )
    
    result = await service.nuke_and_rebuild_db()
    return result