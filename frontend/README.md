# Frontend (Streamlit) Application

This directory contains the Streamlit application that serves as the user interface for the Adv-RAG system.

## Overview

The frontend provides a comprehensive and user-friendly interface for all major system functionalities, with views dynamically rendered based on the logged-in user's role.

## Features

-   **Secure User Authentication:** Login page, password-setting workflow for new users, and "Forgot Password" functionality.
-   **Role-Based Dashboards:**
    -   **Admin View:** Full control over user management, project oversight, and system-level actions.
    -   **Uploader View:** Can create projects, upload data, manage settings, and grant/revoke access.
    -   **Chatter View:** Can interact with projects they have access to via a dedicated chat interface.
-   **Project Management Panel:**
    -   Create projects, upload various file types, and trigger the data processing pipeline.
    -   Configure project settings like chat history and "thinking" mode visibility.
    -   Manage user access on a per-project basis.
-   **Interactive Chat Interface:**
    -   Real-time conversation with the RAG model for a specific project.
    -   Optional collapsible "Show thought process" expander to view the model's reasoning.

## Running the Frontend

There are two primary ways to run the frontend.

### Method 1: Using Docker (Recommended)

If you have followed the Docker setup in the main project [README](../README.md), the frontend is already running.

-   **URL:** [http://localhost:8501](http://localhost:8501)

No further setup is required.

### Method 2: Local Development

Run the frontend locally for development purposes, which is useful for making rapid UI changes.

#### Prerequisites

-   Python >= 3.9
-   Access to a running instance of the FastAPI backend (either running locally or via Docker).

#### Setup

1.  **Navigate to the Frontend Directory:**
    ```bash
    cd frontend
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    Install the required Python packages.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file from the example:
    ```bash
    cp .env.example .env
    ```
    Open the `.env` file and ensure `API_BASE_URL` points to your running backend API (e.g., `http://localhost:8000/api/v1`).

5.  **Run the Application:**
    Start the Streamlit server:
    ```bash
    streamlit run app.py
    ```
    The application will be available at `http://localhost:8501` by default.