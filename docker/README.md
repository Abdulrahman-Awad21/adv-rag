# Docker Environment Setup

This directory contains the Docker Compose configuration to run the entire Adv-RAG application stack, including the backend, databases, and monitoring services. This is the recommended method for running the project.

## Services Managed by Docker Compose

-   **`fastapi`**: The main Python backend application running on Uvicorn.
-   **`nginx`**: A reverse proxy that serves the FastAPI application.
-   **`pgvector`**: PostgreSQL database with the `pgvector` extension for relational data and vector similarity search.
-   **`qdrant`**: An alternative vector database for high-performance similarity search.
-   **`prometheus`**: A metrics collection and time-series database.
-   **`grafana`**: A dashboard for visualizing metrics collected by Prometheus.
-   **`postgres-exporter`**: Exports PostgreSQL metrics for Prometheus.
-   **`node-exporter`**: Exports host system metrics (CPU, RAM, Disk) for Prometheus.

## Prerequisites

-   Docker Engine
-   Docker Compose

## Setup Instructions

1.  **Navigate to this Directory:**
    All commands should be run from within the `docker/` directory.
    ```bash
    cd docker
    ```

2.  **Configure Environment Variables:**
    The application's configuration is managed through environment files. Copy the example file to create your own configuration:
    ```bash
    cp ./env/.env.app.example ./env/.env.app
    cp ./env/.env.example.postgres ./env/.env.postgres
    cp ./env/.env.example.grafana ./env/.env.grafana
    cp ./env/.env.example.postgres-exporter ./env/.env.postgres-exporter
    ```
    Edit the newly created `./env/.env.app` file and provide the necessary credentials:
    -   `SECRET_KEY`: A unique, randomly generated 32-byte hex string.
    -   `INITIAL_ADMIN_EMAIL` & `INITIAL_ADMIN_PASSWORD`: Credentials for the first admin user.
    -   `FRONTEND_URL`: The URL for the frontend (default `http://localhost:8501`).
    -   API keys for your desired LLMs (`GROQ_API_KEY`, `COHERE_API_KEY`, etc.).
    -   SMTP credentials for sending emails (`SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, etc.).
    Also edit the variables in other .env files

3.  **Setup the Alembic configuration for the FastAPI application:** 

    ```bash
    cd docker/minirag
    cp alembic.example.ini alembic.ini
    cd ..
    ```
    
    

4.  **Build and Start Services:**
    Use Docker Compose to build the images and start all containers in detached mode.
    ```bash
    sudo docker compose up --build -d
    ```
    
    If you encounter connection issues, you may want to start the database services first and let them initialize before starting the application:

    ```bash
    # Start databases first
    docker compose up -d pgvector qdrant postgres-exporter
    # Wait for databases to be healthy
    sleep 30
    # Start the application services
    docker compose up fastapi nginx prometheus grafana node-exporter --build -d
    ```
    The `entrypoint.sh` script within the `fastapi` container will automatically run Alembic database migrations on startup, so there is no need to run them manually.

## Accessing Services

Once the stack is running, you can access the various services via your browser:

| Service               | URL                                   | Credentials                               |
| --------------------- | ------------------------------------- | ----------------------------------------- |
| **Frontend UI**       | `http://localhost:8501`               | Use initial admin or created user account |
| **Backend API Docs**  | `http://localhost:8000/docs`          | -                                         |
| **Grafana**           | `http://localhost:3000`               | `admin` / `admin_password` (from `.env`)  |
| **Prometheus**        | `http://localhost:9090`               | -                                         |
| **Qdrant Dashboard**  | `http://localhost:6333/dashboard`     | -                                         |

## Application Lifecycle Management

-   **Check Service Status:**
    ```bash
    sudo docker compose ps
    ```
-   **View Logs:**
    To view logs for a specific service (e.g., `fastapi`):
    ```bash
    sudo docker compose logs -f fastapi
    ```
-   **Stop All Services:**
    ```bash
    sudo docker compose down
    ```
-   **Stop and Remove Volumes (Full Reset):**
    **Warning:** This will delete all database data and stored files.
    ```bash
    sudo docker compose down -v
    ```
-   **Restart a Single Service:**
    ```bash
    sudo docker compose restart fastapi
    ```

## Monitoring

The included monitoring stack provides deep insights into the application's health.

1.  **Login to Grafana:** Navigate to [http://localhost:3000](http://localhost:3000).
2.  **Add Prometheus Data Source:**
    -   URL: `http://prometheus:9090`
    -   Access: `Server (default)`
3.  **Import Dashboards:**
    Use the "Import via grafana.com" feature with the following dashboard IDs:
    -   **FastAPI Observability:** `18739`
    -   **Node Exporter Full:** `1860`
    -   **Qdrant:** `23033`
    -   **PostgreSQL Exporter:** `12485`

## Troubleshooting

-   **Connection Refused Errors:** If the `fastapi` service fails to start due to database connection errors, it might be because the database wasn't fully initialized. The `depends_on` with `service_healthy` condition should prevent this, but if it occurs, try restarting the service: `sudo docker compose restart fastapi`.
-   **Permission Denied:** Ensure you are running `docker compose` with `sudo` or that your user is part of the `docker` group.