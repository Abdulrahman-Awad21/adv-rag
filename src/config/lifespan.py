from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging
from sqlalchemy import update

from models.db_schemes.minirag.schemes.user import User
from services.AuthService import AuthService

from .settings import get_settings
from .database import setup_database_pool
from stores.llm.LLMProviderFactory import LLMProviderFactory
from stores.vectordb.VectorDBProviderFactory import VectorDBProviderFactory
from stores.llm.templates.template_parser import TemplateParser
from services.EmailService import EmailService
from services.UserService import UserService
from routes.schemes.user import UserCreate

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

    # Setup Email Service
    app.email_service = EmailService(settings=settings)

      # Create initial admin user if configured
    if settings.INITIAL_ADMIN_EMAIL and settings.INITIAL_ADMIN_PASSWORD:
        auth_service = AuthService(app.db_client, settings)
        admin_user = await auth_service.get_user_by_email(settings.INITIAL_ADMIN_EMAIL)
        
        if not admin_user:
            logger.info("Initial admin user not found, creating one.")
            hashed_password = auth_service.get_password_hash(settings.INITIAL_ADMIN_PASSWORD)
            
            new_admin = User(
                email=settings.INITIAL_ADMIN_EMAIL,
                hashed_password=hashed_password,
                role="admin",
                password_change_required=False # Admin is ready to go
            )
            
            async with app.db_client() as session:
                session.add(new_admin)
                await session.commit()
            logger.info(f"Initial admin user '{settings.INITIAL_ADMIN_EMAIL}' created successfully.")
        else:
            logger.info("Initial admin user already exists.")


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