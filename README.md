# HALOCAS - Halo Collision Avoidance System

[![CI Pipeline](https://github.com/Augmencord/halocas-production/actions/workflows/ci.yml/badge.svg)](https://github.com/Augmencord/halocas-production/actions/workflows/ci.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](#)

> **HALOCAS** is a real-time, production-grade Collision Avoidance System (CAS) and Proximity Detection System (PDS) engineered for heavy surface and underground mining safety.

---

## 🏗️ System Architecture

HALOCAS monitors the dynamic spatial proximity between workers on foot and heavy machinery (haul trucks, excavators, loaders) in real time:

- **Computer Vision & Detection**: YOLOv8 neural detection for personnel, machines, and safety perimeter estimation.
- **Biometric Identification**: DeepFace (Facenet512) feature embedding for instant worker recognition and authorization verification.
- **FastAPI Core Engine**: High-throughput async backend handling video streams, distance calculations, and websocket broadcasts.
- **Automated Alerting**: Immediate supervisor notification dispatch via Resend API and websocket channels with automatic 60-second cooldown per pair.
- **Cloud Storage**: Automatic capture and upload of 5-second incident clips directly to Cloudflare R2 object storage.
- **Data Persistence**: Async PostgreSQL (Neon) with SQLAlchemy 2.0 and Alembic migrations.

---

## 📁 Repository Structure

```
halocas-production/
+-- backend/
|   +-- app/
|   |   +-- __init__.py          # Package initializer
|   |   +-- main.py              # FastAPI ASGI entrypoint & lifespan
|   |   +-- config.py            # Pydantic-settings configuration
|   |   +-- models/              # SQLAlchemy 2.0 ORM models
|   |   |   +-- __init__.py
|   |   |   +-- base.py
|   |   +-- api/                 # REST & WebSocket API endpoints
|   |   |   +-- __init__.py
|   |   |   +-- router.py
|   |   +-- core/                # Logging, security, telemetry
|   |   |   +-- __init__.py
|   |   |   +-- logging.py
|   |   +-- services/            # Vision, distance, alert services
|   |       +-- __init__.py
|   +-- tests/                   # Async test suite
|   |   +-- __init__.py
|   |   +-- conftest.py
|   |   +-- test_health.py
|   |   +-- test_config.py
|   +-- alembic/                 # Database schema migrations
|   |   +-- versions/
|   |   +-- env.py
|   |   +-- script.py.mako
|   +-- alembic.ini              # Alembic database configuration
|   +-- requirements.txt         # Production backend dependencies
|   +-- requirements-dev.txt     # Development and testing dependencies
|   +-- Dockerfile               # Multi-stage container build (Python 3.11-slim)
+-- frontend/                    # Next.js frontend application (upcoming)
|   +-- README.md
+-- .github/
|   +-- workflows/
|       +-- ci.yml               # Automated CI (pytest, ruff, mypy)
+-- .env.example                 # Environment configuration template
+-- .gitignore                   # Git ignore filters
+-- docker-compose.yml           # Local multi-container development environment
+-- pyproject.toml               # Hatchling build specification & tool configs
+-- render.yaml                  # Render cloud deployment blueprint
+-- README.md                    # Project documentation
```

---

## 🚀 Quickstart & Local Setup

### 1. Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or standard `pip`
- Docker and Docker Compose

### 2. Clone & Environment Setup
```bash
git clone https://github.com/Augmencord/halocas-production.git
cd halocas-production

# Copy environment variables
cp .env.example .env
```

### 3. Install Dependencies (using `uv` or `pip`)
Using `uv`:
```bash
uv venv .venv --python 3.11
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
uv pip install -r backend/requirements.txt -r backend/requirements-dev.txt
```

Using standard `pip`:
```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
```

### 4. Running with Docker Compose
To start the entire local stack (Postgres, Redis, and FastAPI Backend):
```bash
docker-compose up -d
```
The API documentation will be accessible at:
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

### 5. Running the Backend Locally
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🧪 Testing & Code Quality

HALOCAS enforces zero-placeholder production rigor. Every check must pass cleanly before merging:

```bash
# Linting with Ruff
ruff check .

# Format checking
ruff format --check .

# Static type checking with Mypy
mypy .

# Execute test suite with coverage
pytest
```

---

## ☁️ Deployment

### Backend on Render
1. Connect the GitHub repository `Augmencord/halocas-production` in your [Render Dashboard](https://dashboard.render.com/).
2. Select **Blueprint** to automatically provision services using `render.yaml`.
3. Provide production environment secrets:
   - `DATABASE_URL`: Neon PostgreSQL async connection string
   - `R2_ENDPOINT`, `R2_ACCESS_KEY`, `R2_SECRET_KEY`, `R2_BUCKET`: Cloudflare R2 bucket details
   - `RESEND_API_KEY`: API key from [Resend](https://resend.com)

### Frontend on Vercel
The frontend directory is configured for zero-configuration continuous deployment on Vercel:
- **Framework Preset**: Next.js
- **Root Directory**: `frontend/`
- Set `NEXT_PUBLIC_API_URL` to your Render backend URL.
