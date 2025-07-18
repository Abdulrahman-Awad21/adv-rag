from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):

    APP_NAME: str
    APP_VERSION: str
    FRONTEND_URL: str
    OPENAI_API_KEY: str

    FILE_ALLOWED_TYPES: list
    FILE_MAX_SIZE: int
    FILE_DEFAULT_CHUNK_SIZE: int

    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_MAIN_DATABASE: str

    GENERATION_BACKEND: str
    EMBEDDING_BACKEND: str
    VISION_BACKEND: str

    OPENAI_API_KEY: str = None
    OPENAI_API_URL: str = None
    COHERE_API_KEY: str = None
    GROQ_API_KEY: str = None   
    OPENROUTER_API_KEY: str = None
    GOOGLE_API_KEY: str = None
    MISTRAL_API_KEY: str = None   

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ADMIN_RESET_API_KEY: str
    INITIAL_ADMIN_EMAIL: str = None
    INITIAL_ADMIN_PASSWORD: str = None

    # Email settings
    SMTP_HOST: str = None
    SMTP_PORT: int = None
    SMTP_USER: str = None
    SMTP_PASSWORD: str = None
    EMAILS_FROM_EMAIL: str = None

    VISION_MODEL_ID: str = None
    GENERATION_MODEL_ID_LITERAL: List[str] = None
    GENERATION_MODEL_ID: str = None
    EMBEDDING_MODEL_ID: str = None
    EMBEDDING_MODEL_SIZE: int = None
    INPUT_DAFAULT_MAX_CHARACTERS: int = None
    GENERATION_DAFAULT_MAX_TOKENS: int = None
    GENERATION_DAFAULT_TEMPERATURE: float = None

    VECTOR_DB_BACKEND_LITERAL: List[str] = None
    VECTOR_DB_BACKEND : str
    VECTOR_DB_PATH : str
    VECTOR_DB_DISTANCE_METHOD: str = None
    VECTOR_DB_PGVEC_INDEX_THRESHOLD: int = 100

    PRIMARY_LANG: str = "en"
    DEFAULT_LANG: str = "en"

    class Config:
        env_file = ".env"

def get_settings():
    return Settings()
