#!/usr/bin/env bash
set -e

echo "=== HALOCAS Production Startup Sequence ==="

# Normalize Render's postgres:// or postgresql:// connection strings to postgresql+asyncpg://
if [ -n "$DATABASE_URL" ]; then
    if [[ "$DATABASE_URL" == postgres://* ]]; then
        export DATABASE_URL="${DATABASE_URL/#postgres:\/\//postgresql+asyncpg:\/\/}"
        echo "Normalized DATABASE_URL dialect to postgresql+asyncpg://"
    elif [[ "$DATABASE_URL" == postgresql://* && "$DATABASE_URL" != *"+asyncpg"* ]]; then
        export DATABASE_URL="${DATABASE_URL/#postgresql:\/\//postgresql+asyncpg:\/\/}"
        echo "Normalized DATABASE_URL to include +asyncpg dialect"
    fi
fi

# Execute database migrations
echo "Executing database schema migrations (alembic upgrade head)..."
alembic upgrade head || echo "Warning: Alembic migration could not connect to database or was skipped; continuing startup..."
echo "Database migration step completed."

# Start Uvicorn ASGI server
PORT="${PORT:-8000}"
echo "Starting Uvicorn ASGI server on port ${PORT}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
