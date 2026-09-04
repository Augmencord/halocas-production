#!/usr/bin/env bash
set -e

echo "=== HALOCAS Production Startup Sequence ==="

# Limit memory usage for resource-constrained containers (e.g. Render 512MB RAM)
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export TF_ENABLE_ONEDNN_OPTS=0
export TF_CPP_MIN_LOG_LEVEL=3
export SKIP_FACE_WARMUP=1
export MALLOC_ARENA_MAX=2

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

# Execute database migrations only if a remote database URL is configured
if [ -n "$DATABASE_URL" ] && [[ "$DATABASE_URL" != *"localhost"* ]]; then
    echo "Executing database schema migrations (alembic upgrade head)..."
    alembic upgrade head || echo "Warning: Alembic migration could not connect to database or was skipped; continuing startup..."
    echo "Database migration step completed."
else
    echo "No remote DATABASE_URL configured. Skipping database migrations on startup."
fi

# Start Uvicorn ASGI server
PORT="${PORT:-8000}"
echo "Starting Uvicorn ASGI server on port ${PORT}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
