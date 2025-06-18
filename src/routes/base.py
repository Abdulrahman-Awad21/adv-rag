from fastapi import APIRouter, Depends
from config.settings import get_settings, Settings

base_router = APIRouter(
    prefix="/api/v1",
    tags=["api_v1", "base"], 
)

@base_router.get("/welcome") 
async def welcome(app_settings: Settings = Depends(get_settings)):
    """A welcome endpoint that returns basic application information."""
    return {
        "app_name": app_settings.APP_NAME,
        "app_version": app_settings.APP_VERSION,
    }