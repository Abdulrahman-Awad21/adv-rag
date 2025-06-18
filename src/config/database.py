from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from .settings import Settings # CORRECTED IMPORT

def setup_database_pool(settings: Settings):
    """
    Creates and returns synchronous and asynchronous database engines and a session factory.
    """
    # Asynchronous engine for FastAPI routes
    async_db_url = (
        f"postgresql+asyncpg://{settings.POSTGRES_USERNAME}:{settings.POSTGRES_PASSWORD}@"
        f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}"
    )
    async_engine = create_async_engine(async_db_url)
    
    # Asynchronous session factory
    AsyncSessionFactory = sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )

    # Synchronous engine for operations that require it (e.g., Pandas to_sql)
    sync_db_url = (
        f"postgresql+psycopg2://{settings.POSTGRES_USERNAME}:{settings.POSTGRES_PASSWORD}@"
        f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}"
    )
    sync_engine = create_engine(sync_db_url)
    
    return async_engine, sync_engine, AsyncSessionFactory