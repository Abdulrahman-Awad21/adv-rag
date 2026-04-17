# Docker Environment Setup

This directory contains the Docker Compose configuration to run the full application stack. All services — backend, frontend, databases, and monitoring — are orchestrated with a single command.

---

## Services

| Service | Image | Port | Description |
|---------|-------|------|-------------|
| `fastapi` | Built from `docker/adv_rag/Dockerfile` | 8000 | FastAPI backend; runs Alembic migrations on startup |
| `frontend` | Built from `frontend/Dockerfile` | 8501 | Streamlit UI |
| `pgvector` | `pgvector/pgvector:0.8.0-pg17` | 5432 | PostgreSQL 17 with vector extension |
| `qdrant` | `qdrant/qdrant:v1.13.6` | 6333 / 6334 | High-performance vector DB (alternative to pgvector) |
| `prometheus` | `prom/prometheus:v3.3.0` | 9090 | Metrics collection |
| `grafana` | `grafana/grafana:11.6.0-ubuntu` | 3000 | Metrics dashboards |
| `node-exporter` | `prom/node-exporter:v1.9.1` | 9100 | Host system metrics (CPU, RAM, disk) |
| `postgres-exporter` | `prometheuscommunity/postgres-exporter:v0.17.1` | 9187 | PostgreSQL metrics for Prometheus |

---

## Prerequisites

- Docker Engine
- Docker Compose

---

## Setup Instructions

All commands should be run from the `docker/` directory:

```bash
cd docker
```

### 1. Configure Environment Variables

Copy the example environment files and fill in your credentials:

```bash
cp ./env/.env.app.example ./env/.env.app
cp ./env/.env.example.postgres ./env/.env.postgres
cp ./env/.env.example.grafana ./env/.env.grafana
cp ./env/.env.example.postgres-exporter ./env/.env.postgres-exporter
```

Edit `./env/.env.app` and set the required values:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Generate with `openssl rand -hex 32` |
| `INITIAL_ADMIN_EMAIL` | Email for the auto-created admin account |
| `INITIAL_ADMIN_PASSWORD` | Password for the admin account |
| `FRONTEND_URL` | Set to `http://localhost:8501` |
| `GENERATION_BACKEND` | LLM provider for text generation (e.g. `GROQ`) |
| `EMBEDDING_BACKEND` | LLM provider for embeddings (e.g. `COHERE`) |
| `VISION_BACKEND` | LLM provider for image captioning (e.g. `MISTRAL_VISION`) |
| `GENERATION_MODEL_ID` | Model ID for generation |
| `EMBEDDING_MODEL_ID` | Model ID for embeddings |
| `EMBEDDING_MODEL_SIZE` | Embedding vector dimension |
| `GROQ_API_KEY` / `COHERE_API_KEY` / etc. | API keys for your chosen providers |
| `VECTOR_DB_BACKEND` | `PGVECTOR` (default) or `QDRANT` |
| `SMTP_*` | SMTP credentials for email failure notifications |

Also fill in `./env/.env.postgres`, `./env/.env.grafana`, and `./env/.env.postgres-exporter` with the relevant credentials.

### 2. Configure Alembic

```bash
cp ./adv_rag/alembic.example.ini ./adv_rag/alembic.ini
```

The `entrypoint.sh` script inside the `fastapi` container will automatically run `alembic upgrade head` on startup — no manual migration step needed.

### 3. Build and Start All Services

```bash
sudo docker compose up --build -d
```

If the `fastapi` service fails on first start due to the database not being ready, start the databases first:

```bash
# Start databases first and wait for them to initialize
sudo docker compose up -d pgvector qdrant postgres-exporter
sleep 30

# Then start the remaining services
sudo docker compose up -d fastapi frontend nginx prometheus grafana node-exporter
```

---

## Accessing Services

Once the stack is running:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend UI** | `http://localhost:8501` | Admin credentials from `.env.app` |
| **Backend API Docs** | `http://localhost:8000/docs` | — |
| **Grafana** | `http://localhost:3000` | `admin` / value from `.env.grafana` |
| **Prometheus** | `http://localhost:9090` | — |
| **Qdrant Dashboard** | `http://localhost:6333/dashboard` | — |

---

## Application Lifecycle

```bash
# Check service status
sudo docker compose ps

# View logs for a specific service
sudo docker compose logs -f fastapi
sudo docker compose logs -f frontend

# Restart a single service
sudo docker compose restart fastapi

# Stop all services (data preserved)
sudo docker compose down

# Stop and remove all volumes (full reset — deletes all data)
sudo docker compose down -v
```

---

## Monitoring Setup

The monitoring stack is pre-configured and starts automatically.

### Grafana Dashboard Setup

1. Navigate to `http://localhost:3000` and log in.
2. Add a Prometheus data source:
   - URL: `http://prometheus:9090`
   - Access: **Server (default)**
3. Import dashboards using the following IDs from grafana.com:

| Dashboard | ID |
|-----------|----|
| FastAPI Observability | `18739` |
| Node Exporter Full | `1860` |
| Qdrant | `23033` |
| PostgreSQL Exporter | `12485` |

---

## Volumes

| Volume | Contents |
|--------|----------|
| `fastapi_data` | Uploaded files and project assets |
| `pgvector` | PostgreSQL data |
| `qdrant_data` | Qdrant vector storage |
| `prometheus_data` | Prometheus time-series data |
| `grafana_data` | Grafana configuration and dashboards |

---

## Troubleshooting

**`fastapi` fails to connect to the database on startup:**
The `depends_on` with `service_healthy` should prevent this, but if it occurs:
```bash
sudo docker compose restart fastapi
```

**Permission denied running docker commands:**
Either prefix with `sudo` or add your user to the `docker` group:
```bash
sudo usermod -aG docker $USER
```
Then log out and back in.

**Port already in use:**
Check which process is using the port and stop it, or edit the port mapping in `docker-compose.yml`.
