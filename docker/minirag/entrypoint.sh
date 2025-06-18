#!/bin/bash
set -e

echo "Running database migrations..."
cd /app/models/db_schemes/minirag/
alembic upgrade head
echo "Alembic upgrade head finished."
cd /app

echo "Starting Uvicorn server..."
exec "$@"