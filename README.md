# Advanced RAG System for Structured & Unstructured Data

A full-stack, enterprise-ready RAG (Retrieval-Augmented Generation) system for querying documents, images, and SQL databases using natural language. Built with a modular, pluggable architecture, role-based access control, and a complete containerized deployment stack.

---

## Key Features

- **Hybrid RAG Pipeline**: Queries text, images, and tabular data (CSV/XLSX → SQL) in a single unified flow.
- **Multi-Modal Understanding**: Automatically captions images using vision models; captions become searchable knowledge.
- **Intent Classification Gate**: Classifies queries before retrieval to prevent hallucination on out-of-scope questions.
- **Multi-Stage Answer Moderation**: Synthesis and moderation gates ensure grounded, clean answers.
- **Structured Thinking Process**: Captures the LLM's internal reasoning (`<think>` tags) and stores it per chat message.
- **Pluggable LLM & Vector DB Providers**: Factory pattern supports OpenAI, Groq, Cohere, Google, OpenRouter, and Mistral for LLMs; pgvector and Qdrant for vector storage.
- **Role-Based Access Control**: Admin, Uploader, and Chatter roles with per-project granular permissions.
- **Email Failure Notifications**: Alerts project owners when the RAG pipeline cannot answer a question.
- **Multi-Language Prompts**: Prompt templates available in English and Arabic.
- **Prometheus + Grafana Monitoring**: Full observability stack included out of the box.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Streamlit :8501)           │
│  Login │ Admin Dashboard │ Uploader Dashboard │ Chat UI     │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API (JWT)
┌──────────────────────────▼──────────────────────────────────┐
│                    Backend (FastAPI :8000)                   │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │ Auth/Users  │  │ Data/Vision  │  │   NLP / RAG        │ │
│  └─────────────┘  └──────────────┘  └────────────────────┘ │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            Services Layer                            │  │
│  │  Ingestion → Processing → Indexing → RAG Pipeline   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─────────────────┐        ┌──────────────────────────┐  │
│  │  LLM Providers  │        │    Vector DB Providers   │  │
│  │  (Factory)      │        │    (Factory)             │  │
│  └─────────────────┘        └──────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
   PostgreSQL          Qdrant           PostgreSQL
   (pgvector)      (Vector Store)    (Tabular / SQL)
```

---

## RAG Pipeline & Workflow

The system processes data through six sequential phases:

### Phase 1 — Ingestion (Upload)

Files are uploaded to a project via `POST /api/v1/data/upload/{project_uuid}`.

| File Type | Handling |
|-----------|----------|
| PDF | Loaded with PyMuPDF; embedded images are auto-captioned |
| TXT | Loaded with LangChain TextLoader |
| PNG / JPG / GIF / WebP | Captioned by vision model; caption stored as a text chunk |
| CSV / XLSX | Loaded with pandas; schema extracted for SQL generation |

- Max file size: 10 MB
- Assets are recorded in the `assets` table with their processing status.

---

### Phase 2 — Processing (Chunking & ETL)

Triggered via `POST /api/v1/data/process/{project_uuid}`.

**Text & PDF files:**
- Split into overlapping chunks (configurable `chunk_size` and `overlap_size`).
- Each chunk stored as a `DataChunk` with `chunk_text` and `chunk_metadata` (source, type, page).

**Tabular files (CSV / XLSX):**
- Loaded into PostgreSQL as native tables (`pgdata_projXXX_assetYYY_sheetname`).
- A schema document chunk is generated and stored so the LLM knows how to query it.
- Only `SELECT` queries are permitted at runtime.

**Images (standalone uploads):**
- Vision model generates a natural-language caption.
- Caption is stored as a chunk with `type: "image_caption_upload"` metadata.

---

### Phase 3 — Indexing (Vectorization)

Triggered via `POST /api/v1/nlp/index/push/{project_uuid}`.

- All chunks for the project are retrieved from PostgreSQL.
- Texts are batch-embedded by the configured embedding model.
- Vectors are inserted into a named collection: `collection_{embedding_size}_{project_uuid}`.
- Distance metric: cosine (configurable).

---

### Phase 4 — Retrieval (Semantic Search)

Called internally during answer generation (also directly via `POST /api/v1/nlp/index/search/{project_uuid}`).

1. The user query is embedded using the same embedding model.
2. The vector DB performs a nearest-neighbour search (default top-10).
3. Returns `RetrievedDocument` objects with `text`, `score`, and `metadata`.

---

### Phase 5 — Synthesis (Multi-Stage LLM Processing)

The core RAG answering flow, triggered via `POST /api/v1/nlp/index/answer/{project_uuid}`:

```
User Query
    │
    ▼
┌────────────────────┐
│ Intent Gate        │  LLM classifies if query is document-relevant.
│                    │  "violation" → return "I can only answer questions
│                    │  related to the provided documents."
└────────┬───────────┘
         │ valid
         ▼
┌────────────────────┐
│ Vector Retrieval   │  Semantic search → top-K chunks retrieved.
└────────┬───────────┘
         │
         ▼
┌────────────────────────────────────────────┐
│ Hybrid Routing                             │
│                                            │
│  Has SQL schema chunk? ──Yes──► SQL Path   │
│         │                                  │
│         No                                 │
│         ▼                                  │
│      Text Path                             │
└────────┬───────────────────────────────────┘
         │
    SQL Path:                    Text Path:
    LLM generates SELECT query   Concatenate text chunks
    → Execute safely on Postgres → Pass to synthesis prompt
    → Format results as table
    → Combine with text chunks
         │
         ▼
┌────────────────────┐
│ Synthesis Gate     │  LLM synthesizes answer from combined context.
│                    │  If context is irrelevant → force "NO_ANSWER".
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Moderation Gate    │  Cleans answer, removes source references,
│                    │  final "NO_ANSWER" check.
└────────┬───────────┘
         │
         ▼
    Return to user:
    { answer, thinking, full_prompt }
```

---

### Phase 6 — Chat History & Notifications

- Every user message and assistant response is persisted to the `chat_history` table.
- The `thinking` field stores the full LLM reasoning log (SQL queries, synthesis steps).
- If `project.is_thinking_visible = true`, the frontend displays a collapsible thought process panel.
- On RAG failure (no answer found), the system emails the project owner with the failed query and response.

---

## Technology Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | FastAPI, Python ≥ 3.9, SQLAlchemy, Alembic, Uvicorn |
| **Frontend** | Streamlit |
| **Relational DB** | PostgreSQL 17 with pgvector extension |
| **Vector DB** | pgvector (default) or Qdrant |
| **LLM Providers** | OpenAI, Groq, Cohere, Google Generative AI, OpenRouter, Mistral |
| **Core Libraries** | LangChain, PyMuPDF, pandas, Pydantic, Passlib, PyJWT |
| **Monitoring** | Prometheus, Grafana, Node Exporter, Postgres Exporter |
| **Containerization** | Docker, Docker Compose |

---

## Supported LLM Providers

| Provider | Generation | Embedding | Vision |
|----------|-----------|-----------|--------|
| OpenAI | Yes | Yes | - |
| Groq | Yes | - | - |
| Cohere | Yes | Yes | - |
| Google | Yes | Yes | - |
| OpenRouter | Yes | - | - |
| Mistral | Yes | - | Yes (Pixtral) |

Configure via environment variables:
```env
GENERATION_BACKEND=GROQ
EMBEDDING_BACKEND=COHERE
VISION_BACKEND=MISTRAL_VISION
```

---

## User Roles & Access Control

| Role | Capabilities |
|------|-------------|
| **Admin** | Full system access, create/edit/delete users, view all projects |
| **Uploader** | Create projects, upload & process files, manage project access |
| **Chatter** | Chat on projects they have been granted access to |

Access is controlled at two levels:
1. **Role-level**: Enforced via JWT token claims on every request.
2. **Project-level**: `ProjectAccess` junction table; owners grant/revoke individual users.

---

## Getting Started

Choose between Docker (recommended for production/demo) or local development.

---

### Option 1: Docker Setup (Recommended)

One command starts all 8 services (backend, frontend, databases, monitoring).

> **See [docker/README.md](./docker/README.md) for full instructions.**

---

### Option 2: Local Development Setup

#### Prerequisites

- Python ≥ 3.9
- Miniconda
- PostgreSQL running locally

#### Step 1: Clone the Repository

```bash
git clone https://github.com/abdulrahman-awad21/adv-rag.git
cd adv-rag
```

#### Step 2: Create and Activate Conda Environment

```bash
conda create -n adv-rag python=3.9
conda activate adv-rag
```

#### Step 3: Configure and Run the Backend

Navigate to the backend source directory:

```bash
cd src
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure environment variables:

```bash
cp .env.example .env
```

Edit `.env` and set:

| Variable | Description |
|----------|-------------|
| `POSTGRES_*` | Your local PostgreSQL credentials |
| `SECRET_KEY` | Generate with `openssl rand -hex 32` |
| `GENERATION_BACKEND` | LLM provider for generation (e.g. `GROQ`) |
| `EMBEDDING_BACKEND` | LLM provider for embeddings (e.g. `COHERE`) |
| `VISION_BACKEND` | LLM provider for image captioning (e.g. `MISTRAL_VISION`) |
| `GENERATION_MODEL_ID` | Model ID for generation |
| `EMBEDDING_MODEL_ID` | Model ID for embeddings |
| `EMBEDDING_MODEL_SIZE` | Embedding vector dimension |
| `GROQ_API_KEY` / `COHERE_API_KEY` / etc. | API keys for your chosen providers |
| `INITIAL_ADMIN_EMAIL` | Email for the auto-created admin account |
| `INITIAL_ADMIN_PASSWORD` | Password for the admin account |
| `FRONTEND_URL` | Set to `http://localhost:8501` |
| `SMTP_*` | SMTP credentials for email notifications |

#### Step 4: Run Database Migrations

From `src/`, navigate to the Alembic directory:

```bash
cd models/db_schemes/adv_rag
cp alembic.ini.example alembic.ini
```

Edit `alembic.ini` and set `sqlalchemy.url` to your PostgreSQL connection string, then run:

```bash
alembic upgrade head
cd ../../..
```

#### Step 5: Start the Backend

From the `src/` directory:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API and interactive docs available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

#### Step 6: Run the Frontend

See the [Frontend README](./frontend/README.md) for setup.

The frontend will be available at `http://localhost:8501`.

---

## First-Time Login

Use the credentials set in `.env`:

- **Email**: value of `INITIAL_ADMIN_EMAIL`
- **Password**: value of `INITIAL_ADMIN_PASSWORD`

---

## API Reference

All endpoints are prefixed with `/api/v1`.

| Group | Endpoint | Description |
|-------|----------|-------------|
| Auth | `POST /token` | Login and get JWT token |
| Auth | `POST /forgot-password` | Request password reset email |
| Auth | `POST /reset-password` | Reset password with token |
| Auth | `POST /set-initial-password` | Set password for new accounts |
| Users | `POST /users/` | Create user (Admin) |
| Users | `GET /users/` | List all users (Admin) |
| Users | `GET /users/me` | Get own profile |
| Users | `POST /users/me/change-password` | Change own password |
| Projects | `POST /projects/` | Create project |
| Projects | `GET /projects/` | List accessible projects |
| Projects | `PUT /projects/{uuid}/settings` | Toggle chat history, thinking visibility |
| Projects | `POST /projects/{uuid}/access` | Grant user access |
| Projects | `DELETE /projects/{uuid}/access/{user_id}` | Revoke user access |
| Chat | `POST /projects/{uuid}/chat_history` | Save a chat message |
| Chat | `GET /projects/{uuid}/chat_history` | Get own chat history |
| Chat | `GET /projects/{uuid}/all_chat_history` | Get all messages with filters (Admin/Owner) |
| Data | `POST /data/upload/{uuid}` | Upload files to project |
| Data | `POST /data/process/{uuid}` | Chunk and ETL uploaded files |
| NLP | `POST /nlp/index/push/{uuid}` | Embed chunks into vector DB |
| NLP | `GET /nlp/index/info/{uuid}` | Get vector collection stats |
| NLP | `POST /nlp/index/search/{uuid}` | Semantic search |
| NLP | `POST /nlp/index/answer/{uuid}` | Full RAG answer generation |
| Vision | `POST /vision/explain-image` | Caption a single image |

### Making API Requests with Postman

A Postman collection is available at `src/assets/adv-rag-app.postman_collection.json`.

1. Import the collection into Postman.
2. Set the `api` collection variable to `http://localhost:8000/api/v1`.
3. Obtain a token via `POST {{api}}/token` with `username` and `password` form fields.
4. Add the following Tests script to save the token automatically:

```javascript
const response = pm.response.json();
if (response.access_token) {
    pm.collectionVariables.set("authToken", response.access_token);
}
```

5. Use **Bearer Token** auth with `{{authToken}}` for all subsequent requests.

---

## License

This project is licensed under the Apache License 2.0.
See the [LICENSE](./LICENSE) file for details.
