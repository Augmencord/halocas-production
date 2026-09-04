# ==============================================================================
# HALOCAS Production Dockerfile (Repository Root Context)
# ==============================================================================
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install compilation toolchains and build libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin"

# Install dependencies into virtual environment
COPY backend/requirements.txt requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# ==============================================================================
# Stage 2: Production Runtime Stage
# ==============================================================================
FROM python:3.11-slim AS runner

# Install minimal dynamic shared libraries required by OpenCV and PostgreSQL BEFORE modifying PATH
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin" \
    PYTHONPATH="/app" \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    TF_ENABLE_ONEDNN_OPTS=0 \
    TF_CPP_MIN_LOG_LEVEL=3 \
    SKIP_FACE_WARMUP=1 \
    MALLOC_ARENA_MAX=2

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

# Create a non-root system user and group
RUN groupadd -g 10001 halocas && \
    useradd -u 10001 -g halocas -s /bin/bash -m halocas

# Copy application package, migrations, models, and startup script
COPY --chown=halocas:halocas backend/app /app/app
COPY --chown=halocas:halocas backend/alembic /app/alembic
COPY --chown=halocas:halocas backend/alembic.ini /app/alembic.ini
RUN curl -fsSL https://github.com/ultralytics/assets/releases/download/v8.1.0/yolov8n.pt -o /app/yolov8n.pt && \
    chown halocas:halocas /app/yolov8n.pt
COPY --chown=halocas:halocas backend/render_start.sh /app/render_start.sh
RUN chmod +x /app/render_start.sh

USER halocas
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

CMD ["/app/render_start.sh"]
