# ==============================================================================
# Stage 1: Build & Dependency Compilation Stage
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

# Create virtual environment isolated from system python
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies into virtual environment
# Pre-install CPU wheels for PyTorch to optimize build times and container footprint
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# ==============================================================================
# Stage 2: Production Runtime Stage
# ==============================================================================
FROM python:3.11-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app"

WORKDIR /app

# Install minimal dynamic shared libraries required by OpenCV and PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-compiled virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create a non-root system user and group for hardened container execution
RUN groupadd -g 10001 halocas && \
    useradd -u 10001 -g halocas -s /bin/bash -m halocas

# Copy application package, migrations, models, and deployment startup script
COPY --chown=halocas:halocas app /app/app
COPY --chown=halocas:halocas alembic /app/alembic
COPY --chown=halocas:halocas alembic.ini /app/alembic.ini
COPY --chown=halocas:halocas yolov8n.pt /app/yolov8n.pt
COPY --chown=halocas:halocas render_start.sh /app/render_start.sh

# Ensure startup script has executable permissions
RUN chmod +x /app/render_start.sh

# Switch to unprivileged runtime user
USER halocas

# Expose default HTTP listening port
EXPOSE 8000

# Container health probe validating system availability
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Launch container via migration and server startup script
CMD ["/app/render_start.sh"]
