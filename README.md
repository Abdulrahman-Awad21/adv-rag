# Advanced RAG System

A system that lets you chat with your documents, spreadsheets, and images using natural language. Upload your files, and ask questions — the system finds the relevant information and generates an answer.

---

## What It Does

- Chat with **PDFs, text files, images, and spreadsheets (CSV/XLSX)**
- Understands **images** by auto-generating captions
- Queries **spreadsheets** by generating SQL under the hood
- Supports multiple AI providers (Groq, OpenAI, Cohere, Google, Mistral, OpenRouter)
- Full **user management** with roles and per-project access control
- Built-in **monitoring** with Prometheus + Grafana

---

## How It Works

### 1. Upload & Process Files

When you upload a file, the system handles it based on its type:

| File Type | What Happens |
|-----------|-------------|
| PDF / TXT | Split into small text chunks |
| CSV / XLSX | Loaded into a database table for SQL queries |
| Image | AI vision model generates a text caption |

---

### 2. Chunking

Text files are broken into chunks so the system can find specific parts later.

```
Full document text
        │
        ▼
Split into lines
        │
        ▼
Group lines until chunk size is reached → save chunk → start new chunk
        │
        ▼
Each chunk stored with its source info (file name, page, type)
```

---

### 3. Embedding (Turning Text into Numbers)

Each chunk is converted into a vector — a list of numbers that represents its meaning. Chunks with similar meaning get similar numbers.

```
Text Chunk  →  Embedding Model  →  Vector [0.12, -0.45, 0.87, ...]
                (document mode)
```

All vectors are stored in a vector database (pgvector inside PostgreSQL).

---

### 4. Answering a Question

When you ask a question:

```
Your Question
      │
      ▼
Converted to a vector
(query mode — optimised for search)
      │
      ▼
Compare against all stored chunk vectors
      │
      ▼
Return the top 10 most similar chunks
      │
      ▼
┌─────────────────────────────┐
│   Is the question relevant? │  No → "I can only answer questions
│   (Intent check by LLM)     │        related to the documents."
└────────────┬────────────────┘
             │ Yes
             ▼
   Spreadsheet data? → Generate SQL → Run query → get table results
   Text data?        → Use retrieved chunks directly
             │
             ▼
   LLM writes an answer using the retrieved content
             │
             ▼
   Answer is reviewed and cleaned (moderation step)
             │
             ▼
        Final Answer
```

---

## User Roles

| Role | Can Do |
|------|--------|
| **Admin** | Manage users, view all projects |
| **Uploader** | Create projects, upload files, manage access |
| **Chatter** | Chat on projects they have access to |

---

## Tech Stack

| | |
|-|-|
| Backend | FastAPI (Python) |
| Frontend | Streamlit |
| Database | PostgreSQL with pgvector |
| Vector DB | pgvector or Qdrant |
| AI Providers | OpenAI, Groq, Cohere, Google, Mistral, OpenRouter |
| Monitoring | Prometheus + Grafana |
| Deployment | Docker Compose |

---

## Getting Started

### Option 1: Docker (Recommended)

One command starts everything:

```bash
cd docker
docker compose up --build -d
```

> See [docker/README.md](./docker/README.md) for configuration details.

---

### Option 2: Local Setup

**Prerequisites:** Python ≥ 3.9, Miniconda, PostgreSQL

```bash
# Clone
git clone https://github.com/abdulrahman-awad21/adv-rag.git
cd adv-rag

# Create environment
conda create -n adv-rag python=3.9
conda activate adv-rag

# Install backend dependencies
cd src
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env — set your DB credentials, API keys, and admin account

# Run migrations
cd models/db_schemes/adv_rag
cp alembic.ini.example alembic.ini
# Edit alembic.ini with your DB connection string
alembic upgrade head
cd ../../..

# Start backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Then set up the frontend — see [frontend/README.md](./frontend/README.md).

**Access:**
- Frontend: `http://localhost:8501`
- API docs: `http://localhost:8000/docs`

---

## First Login

Use the credentials you set in `.env`:
- `INITIAL_ADMIN_EMAIL`
- `INITIAL_ADMIN_PASSWORD`

---

## API Endpoints

All routes prefixed with `/api/v1`.

| Area | Method | Endpoint | Description |
|------|--------|----------|-------------|
| Auth | POST | `/token` | Login |
| Auth | POST | `/forgot-password` | Request password reset |
| Auth | POST | `/reset-password` | Reset password |
| Users | GET | `/users/` | List users (Admin) |
| Users | POST | `/users/` | Create user (Admin) |
| Users | GET | `/users/me` | My profile |
| Projects | POST | `/projects/` | Create project |
| Projects | GET | `/projects/` | My projects |
| Projects | POST | `/projects/{id}/access` | Grant user access |
| Data | POST | `/data/upload/{id}` | Upload files |
| Data | POST | `/data/process/{id}` | Process & chunk files |
| NLP | POST | `/nlp/index/push/{id}` | Embed & index chunks |
| NLP | POST | `/nlp/index/answer/{id}` | Ask a question |
| NLP | POST | `/nlp/index/search/{id}` | Semantic search |
| Vision | POST | `/vision/explain-image` | Caption an image |

---

## License

Apache License 2.0 — see [LICENSE](./LICENSE).
