APP_NAME="mini-RAG"
APP_VERSION="0.1"

FILE_ALLOWED_TYPES=["text/plain", "application/pdf", "image/jpeg", "image/png", "image/gif", "image/webp"]
FILE_MAX_SIZE=10
FILE_DEFAULT_CHUNK_SIZE=512000 # 512KB

POSTGRES_USERNAME="postgres"
POSTGRES_PASSWORD="postgres_password"
POSTGRES_HOST="pgvector"
POSTGRES_PORT=5432
POSTGRES_MAIN_DATABASE="minirag"


# ========================= Security Config =========================
SECRET_KEY="your-32-byte-hex-secret-key-goes-here"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
ADMIN_RESET_API_KEY="SecureAdminKey"
INITIAL_ADMIN_EMAIL="admin@example.com"
INITIAL_ADMIN_PASSWORD="a_very_strong_password"




# ========================= Email Config =========================
SMTP_HOST="smtp.sendgrid.net"
SMTP_PORT=587
SMTP_USER="apikey"
SMTP_PASSWORD="SG.your sendgrid_api_key_here"
EMAILS_FROM_EMAIL="from email in sendgrid settings"


# ========================= LLM Config =========================
GENERATION_BACKEND = "GROQ" 
EMBEDDING_BACKEND = "COHERE"
VISION_BACKEND ="MISTRAL_VISION"

MISTRAL_API_KEY="key___"
OPENAI_API_KEY="key___"
OPENAI_API_URL= ""
COHERE_API_KEY="key___"
GROQ_API_KEY="key___"

# ========================= Model Config =========================

VISION_MODEL_ID="pixtral-12b-latest" 
GENERATION_MODEL_ID_LITERAL = ["qwen/qwen3-32b"]
GENERATION_MODEL_ID="qwen/qwen3-32b"
EMBEDDING_MODEL_ID="embed-multilingual-light-v3.0"
EMBEDDING_MODEL_SIZE=384

# Changing the embedding model to a larger one cuases issues with the current vector db
# EMBEDDING_MODEL_ID="embed-v4.0"
# EMBEDDING_MODEL_SIZE=128000


INPUT_DAFAULT_MAX_CHARACTERS=1024
GENERATION_DAFAULT_MAX_TOKENS=200
GENERATION_DAFAULT_TEMPERATURE=0.1

# ========================= Vector DB Config =========================
VECTOR_DB_BACKEND_LITERAL = ["QDRANT", "PGVECTOR"]
VECTOR_DB_BACKEND = "PGVECTOR"
VECTOR_DB_PATH = "qdrant_db"
VECTOR_DB_DISTANCE_METHOD = "cosine"
VECTOR_DB_PGVEC_INDEX_THRESHOLD = 100

# ========================= Template Config =========================
PRIMARY_LANG = "en"
DEFAULT_LANG = "en"
