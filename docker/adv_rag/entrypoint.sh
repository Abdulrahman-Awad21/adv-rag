#!/bin/bash
set -e

echo "Running database migrations..."

cd /app/models/db_schemes/adv_rag/
alembic upgrade head
echo "Alembic upgrade head finished."
cd /app

echo "Starting Uvicorn server..."
exec "$@"