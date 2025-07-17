# Advanced RAG System for Structured & Unstructured Data

This is a full-stack, enterprise-ready RAG (Retrieval-Augmented Generation) system designed to query diverse data sources—including documents, images, and SQL databases—using natural language. It features a modular architecture, robust user management, and a complete containerized environment for easy deployment.

---

## 🚀 Key Features

- **Hybrid RAG Pipeline**: Intelligently queries text, images, and structured data from CSV/XLSX files to synthesize comprehensive answers.
- **Multi-Modal Understanding**: Utilizes vision models to understand and caption images.
- **Pluggable Architecture**: Employs a factory pattern to seamlessly integrate multiple LLM providers and vector databases.
- **Robust User & Project Management**: Full JWT authentication, role-based access control (Admin, Uploader, Chatter), and per-project user permissions.
- **Containerized & Local Setup**: Supports both a one-command Docker setup and a detailed local development environment.
- **Email Notifications**: Automatically alerts project owners of RAG model failures for a continuous feedback loop.

---

## 🏗️ Architecture Overview

- **Backend (FastAPI)**: Python-based RESTful API for ingestion, processing, RAG, and user management.
- **Frontend (Streamlit)**: Interactive web app for managing projects, users, and chatting with the RAG system.
- **Databases**:
  - **PostgreSQL (with pgvector)**: Stores metadata, user info, and vector embeddings.
  - **Qdrant**: Optional high-performance vector DB alternative.

---

## 🧰 Technology Stack

- **Backend**: FastAPI, Python >= 3.9, SQLAlchemy, Alembic
- **Frontend**: Streamlit
- **Databases**: PostgreSQL (pgvector), Qdrant
- **Containerization**: Docker, Docker Compose
- **Core Libraries**: LangChain, Pydantic, Passlib, PyJWT

---

## ⚙️ Getting Started

#### 🔧 Prerequisites

- Python >= 3.9
- Miniconda installed
- PostgreSQL installed and running
- Build dependencies (for Ubuntu/Debian):


#### Install Dependencies

```bash
sudo apt update
```

#### Install Python using MiniConda

1) Download and install MiniConda from [here](https://docs.anaconda.com/free/miniconda/#quick-command-line-install)
2) Create a new environment using the following command:
```bash
$ conda create -n adv-rag python=3.9
```
3) Activate the environment:
```bash
$ conda activate adv-rag
```

### (Optional) Setup you command line interface for better readability

```bash
export PS1="\[\033[01;32m\]\u@\h:\w\n\[\033[00m\]\$ "
```
You can run the project using Docker (recommended for production) or locally (ideal for development).

### 🐳 Option 1: Docker Setup (Recommended)

Get all services (backend, frontend, databases) up with a single command.

> **See the [Docker README](./docker/README.md) for detailed instructions.**

---

### 🧑‍💻 Option 2: Local Development Setup

Ideal for developers working on the backend or frontend.

## Installation


### 🪜 Step 1: Clone the Repository

```bash
git clone https://github.com/abdulrahman-awad21/adv-rag.git
cd adv-rag
```
### 🪄 Step 2: Configure and Run the Backend

#### Navigate to the Backend Directory:

```bash
cd src
```

#### Make sure you are on the conda environment:

```bash
conda activate adv-rag
```

### Install the required packages

```bash
$ pip install -r requirements.txt
```
#### Install Dependencies:

```bash
pip install -r requirements.txt
```

#### Configure Environment Variables:

```bash
cp .env.example .env
```

Edit `.env` and set:

- `POSTGRES_*`: Your local DB credentials  
- `SECRET_KEY`: Generate one via `openssl rand -hex 32`  
- LLM API keys: `GROQ_API_KEY`, `COHERE_API_KEY`, etc.  
- Admin credentials: `INITIAL_ADMIN_EMAIL`, `INITIAL_ADMIN_PASSWORD`  
- SMTP credentials  
- `FRONTEND_URL`: Set to `http://localhost:8501`

#### Run Database Migrations:
Navigate to the Alembic configuration directory:

From the project root
```bash
cd src/models/db_schemes/minirag
```

Make a copy of the Alembic config and update it with your PostgreSQL connection string from your .env file.
```bash
cp alembic.ini.example alembic.ini
```

```bash
alembic upgrade head
```

## Run the FastAPI server


Navigate back to the src directory:
From your current location in .../minirag
```bash
cd ../../../
```
Make sure you are on /src and run Run Uvicorn:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API will be live at: [http://localhost:8000](http://localhost:8000)

---

### 🎨 Step 3: Run the Frontend

The frontend is a Streamlit app. See the [`Frontend README`](./frontend/README.md) for setup.

- Frontend: [http://localhost:8501](http://localhost:8501)  
- Backend Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🔐 First-Time Login

Use the credentials from `.env` to log in:

- **Email**: `INITIAL_ADMIN_EMAIL`
- **Password**: `INITIAL_ADMIN_PASSWORD`

---

## 🧪 Making API Requests with Postman

A Postman collection is available at `src/assets/mini-rag-app.postman_collection.json`.

### 1. Import the Collection

- Import into Postman.
- Set the `api` collection variable to:  
  `http://localhost:8000/api/v1`

### 2. Get an Auth Token

Create a POST request to:

```
{{api}}/token
```

#### Body (form-data):

```
username: your_admin_email@example.com
password: your_admin_password
```

#### Tests Script:

```javascript
const response = pm.response.json();
if (response.access_token) {
    pm.collectionVariables.set("authToken", response.access_token);
    console.log("Auth Token saved.");
}
```

### 3. Make an Authenticated Request

Use the saved token:

- **Authorization Type**: Bearer Token  
- **Token**: `{{authToken}}`

Example:  
GET `{{api}}/projects/`

---

## 📜 License

This project is licensed under the Apache License 2.0.  
See the [LICENSE](./LICENSE) file for details.

