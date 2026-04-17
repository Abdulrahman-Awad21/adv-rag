# FILE: src/config/lifespan.py

from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging
from sqlalchemy.sql import text as sql_text

from .settings import get_settings
from .database import setup_database_pool
from stores.llm.LLMProviderFactory import LLMProviderFactory
from stores.vectordb.VectorDBProviderFactory import VectorDBProviderFactory
from stores.llm.templates.template_parser import TemplateParser
from services.EmailService import EmailService
from services.UserService import UserService

logger = logging.getLogger('uvicorn.error')

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application's startup and shutdown events.
    """
    # --- Startup ---
    settings = get_settings()

    # Setup Database
    app.async_db_engine, app.sync_db_engine, app.db_client = setup_database_pool(settings)

    # ==================== START: CORRECTED CODE ====================
    # Ensure the pgvector extension is enabled in the database.
    # We use an autocommit connection for this DDL command to avoid
    # transactional errors if the extension already exists.
    try:
        async with app.async_db_engine.connect() as conn:
            # Set the connection to autocommit mode for this operation
            await conn.execution_options(isolation_level="AUTOCOMMIT")
            await conn.execute(sql_text("CREATE EXTENSION IF NOT EXISTS vector;"))
        logger.info("Successfully enabled 'vector' extension in the database (or it was already enabled).")
    except Exception as e:
        # This is a defensive check. Autocommit should prevent this, but if it still happens,
        # we log it as a warning instead of crashing the application.
        if "duplicate key value violates unique constraint" in str(e):
             logger.warning("Ignoring expected 'duplicate key' error on creating existing 'vector' extension. The app will continue.")
        else:
            # For any other unexpected errors, we should still raise them.
            logger.error(f"FATAL: Could not enable 'vector' extension due to an unexpected error: {e}")
            raise
    # ===================== END: CORRECTED CODE =====================

    # Setup Email Service
    app.email_service = EmailService(settings=settings)

    # Create initial admin user using the robust service method
    user_service = UserService(
        db_client=app.db_client, 
        app_settings=settings, 
        email_service=app.email_service
    )
    await user_service.create_initial_admin()

    # Setup LLM Clients
    llm_factory = LLMProviderFactory(settings)
    app.generation_client = llm_factory.create(provider=settings.GENERATION_BACKEND)
    app.generation_client.set_generation_model(model_id=settings.GENERATION_MODEL_ID)
    
    app.embedding_client = llm_factory.create(provider=settings.EMBEDDING_BACKEND)
    app.embedding_client.set_embedding_model(model_id=settings.EMBEDDING_MODEL_ID, embedding_size=settings.EMBEDDING_MODEL_SIZE)
    
    app.vision_client = llm_factory.create(provider=settings.VISION_BACKEND)
    app.vision_client.set_generation_model(model_id=settings.VISION_MODEL_ID)

    # Setup VectorDB Client
    vectordb_factory = VectorDBProviderFactory(config=settings, db_client=app.db_client)
    app.vectordb_client = vectordb_factory.create(provider=settings.VECTOR_DB_BACKEND)
    await app.vectordb_client.connect()

    # Setup Template Parser
    app.template_parser = TemplateParser(language=settings.PRIMARY_LANG, default_language=settings.DEFAULT_LANG)

    yield

    # --- Shutdown ---
    await app.async_db_engine.dispose()
    app.sync_db_engine.dispose()
    await app.vectordb_client.disconnect()