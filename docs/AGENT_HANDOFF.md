# HALOCAS: Master Agent Operational Blueprint & System Handoff

> **Document Type:** Production Agent Architecture Specification & System State Handoff  
> **Target Audience:** Successor AI Coding Agents, Autonomous Orchestrators, Systems Engineers  
> **Last Updated:** September 2026  
> **Repository Root:** `C:\Users\augme\.gemini\antigravity-ide\scratch\halocas-production`  
> **Active Branch:** `main`  
> **Primary Stack:** Python 3.13 (FastAPI, SQLAlchemy 2.0 Async, PyTorch, YOLOv8, DeepFace RetinaFace/Facenet512, OpenCV 5.0), Next.js 14 (React 18, TypeScript 5, Tailwind CSS, Recharts, Lucide Icons)

---

## 1. Executive Summary & System Mission

**HALOCAS** (Heavy-machinery Autonomous Localization & Operational Collision Avoidance System) is an enterprise edge-computing and cloud safety platform designed to prevent fatal struck-by and caught-in-between heavy machinery collisions in open-pit mines, industrial excavation, and warehouse logistics facilities.

The platform provides:
1. **Real-time Computer Vision Inference:** Sub-50ms inference on monocular camera streams (front/rear vehicle cameras) detecting workers and industrial machines (excavators, dump trucks, bulldozers, wheel loaders, forklifts).
2. **Dynamic 2D Proximity & Closing-Velocity Telemetry:** Continuous evaluation of monocular pixel-to-meter distance, tracking safety breaches across **Safe** (>10m), **Warning** (3m–10m), and **Critical** (<3m or rapid closing velocity) zones.
3. **DeepFace Biometric Identification:** Instant extraction of 512-dimensional facial feature vectors using RetinaFace and Facenet512 to identify non-compliant personnel without relying on RFID tags or transponders.
4. **Automated Incident Capture & Cloudflare R2 Upload:** Cyclic in-memory frame buffering exporting 5-second incident MP4 video clips directly to Cloudflare R2 object storage with presigned streaming URLs.
5. **Real-Time Next.js 14 Mission Control:** A dark glassmorphic industrial dashboard with 60 FPS live MJPEG camera streams, interactive 2D telemetry radar sweep, time-series infraction frequency charts, and biometrics enrollment.

---

## 2. Core Execution Protocol & Operating Principles

Every successor agent must strictly adhere to the following execution sequence to eliminate hallucination, shallow edits, or regressions:

### Step 1: Prompt Ingestion & Requirement Decomposition
- Deconstruct the user prompt into deterministic, verifiable components.
- Identify all affected services (API routes, database schemas, CV engines, frontend UI, data ingestion scripts).
- Highlight any external API dependencies (e.g., Pexels API, Resend Email API, Cloudflare R2) and prepare fully functional offline fallbacks.

### Step 2: Workspace & Environment Reconnaissance
- Always inspect the runtime environment before writing code.
- Check installed packages and exact versions (`pip list`, `package.json`).
- Verify operating system quirks (Windows paths, PowerShell quoting rules, Unicode console encoding).
- Examine existing database schemas (`backend/app/db/models/`) and configuration settings (`backend/app/config.py`).

### Step 3: Zero Placeholders Directive
- **Strict Prohibition:** Outputting `pass`, `// TODO`, `NotImplementedError`, or ungrounded mock stubs is **strictly forbidden**.
- Every function, method, class, and component must have complete, functional, production-ready logic.
- Implement exhaustive try/except blocks catching specific exceptions, strict type hinting (`mypy` compliant), and structured logging.

### Step 4: Formal Implementation Planning
- When modifying architectural components, draft an `implementation_plan.md` artifact detailing proposed file modifications, additions, and test strategies.
- Request user review and wait for explicit confirmation before executing major changes.

### Step 5: Autonomous Verification & Self-Correction Loop
- Never consider a task complete without executing terminal verification:
  - **Backend Linting:** `python -m ruff check backend/ --fix`
  - **Static Type Checking:** `python -m mypy backend/`
  - **Unit & Integration Tests:** `python -m pytest backend/tests/ -v`
  - **Frontend Linting:** `npm --prefix frontend run lint`
  - **Frontend Production Compilation:** `npm --prefix frontend run build`
- If any check returns a non-zero exit code, read the stack trace, diagnose the root cause, and autonomously fix the code until all checks pass cleanly.

---

## 3. Directory Layout & Architecture Walkthrough

```text
halocas-production/
├── .github/
│   └── workflows/
│       └── ci.yml               # Automated GitHub Actions CI (Backend tests, linting, frontend build)
├── backend/
│   ├── alembic/                 # Database schema migrations
│   │   ├── versions/            # Versioned migration scripts
│   │   └── env.py               # Async SQLAlchemy Alembic migration runner
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py          # FastApi Dependency Injection (DB session, JWT auth, singletons)
│   │   │   └── routes/
│   │   │       ├── auth.py      # /api/v1/auth (JWT login, admin registration)
│   │   │       ├── incidents.py # /api/v1/incidents (CRUD, clip presigned redirects, stats)
│   │   │       ├── machines.py  # /api/v1/machines (Heavy machinery fleet management)
│   │   │       ├── stream.py    # /api/v1/stream (MJPEG live camera streaming endpoints)
│   │   │       ├── telemetry.py # /api/v1/ws/telemetry (WebSocket real-time radar feed)
│   │   │       └── workers.py   # /api/v1/workers (Personnel directory, face enrollment)
│   │   ├── core/
│   │   │   ├── buffer.py        # Cyclic in-memory frame buffer (pre/post incident clip exporter)
│   │   │   ├── detector.py      # YOLOv8 object detection wrapper (person vs machinery)
│   │   │   ├── distance.py      # Monocular camera geometric distance estimator
│   │   │   ├── face_verifier.py # DeepFace RetinaFace/Facenet512 512-D biometric engine
│   │   │   ├── logging.py       # JSON/structured logging engine
│   │   │   ├── pipeline.py      # Central PipelineOrchestrator tying CV, DB, and alerts
│   │   │   ├── security.py      # Password hashing (bcrypt) and JWT token generation
│   │   │   └── state_machine.py # Proximity state machine (Safe -> Warning -> Critical transitions)
│   │   ├── db/
│   │   │   ├── base.py          # SQLAlchemy declarative Base class
│   │   │   ├── session.py       # Async SQLAlchemy engine and session factory
│   │   │   └── models/
│   │   │       ├── incident.py  # Incident table (machine_id, worker_id, severity, clip_url)
│   │   │       ├── machine.py   # Machine table (type, serial, status, camera_ids)
│   │   │       ├── safety_zone.py # Dynamic safety zones and radius configurations
│   │   │       ├── user.py      # System administrative users table
│   │   │       └── worker.py    # Worker table (name, role, face_embedding, authorization)
│   │   ├── services/
│   │   │   ├── notification.py  # Resend email alerting with throttled cooldowns
│   │   │   └── storage.py       # Boto3 S3/Cloudflare R2 video clip uploader & presigned URLs
│   │   ├── config.py            # Pydantic v2 BaseSettings configuration
│   │   └── main.py              # FastAPI application root, CORS, router mounts, lifespan
│   ├── demo_data/
│   │   ├── faces/               # Extracted unique worker face crops (*.jpg, manifest.json)
│   │   │   └── embeddings/      # 512-dimensional Facenet512 biometric vectors (*.npy)
│   │   └── videos/              # Downloaded HD industrial demo videos (*.mp4)
│   ├── scripts/
│   │   ├── __init__.py
│   │   ├── download_demo_videos.py # Pexels API video downloader with resilient fallbacks
│   │   └── extract_faces.py     # Frame sampler, RetinaFace detector, Facenet512 embedder
│   ├── tests/                   # Comprehensive pytest test suite (100% passing)
│   ├── requirements.txt         # Core production dependencies
│   └── requirements-dev.txt     # Test and linting dependencies (pytest, ruff, mypy)
├── docs/
│   └── AGENT_HANDOFF.md         # This master operational document
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── incidents/       # /incidents (Table, filters, CSV export, incident detail modal)
    │   │   ├── machines/        # /machines (Fleet status, machine cards, camera bindings)
    │   │   ├── monitoring/      # /monitoring (Multi-camera live surveillance wall)
    │   │   ├── settings/        # /settings (Distance thresholds, notification webhooks)
    │   │   ├── workers/         # /workers (Directory, KPI banner, search, grid/table view)
    │   │   │   └── [id]/        # /workers/[id] (Biometric profile, alert frequency, incident log)
    │   │   ├── layout.tsx       # Root layout with dark theme and sidebar navigation
    │   │   └── page.tsx         # / (Main dashboard: live stream, radar, KPI cards, recent alerts)
    │   ├── components/
    │   │   ├── common/          # Header, Sidebar, StatCard, Badge
    │   │   ├── dashboard/       # CameraFeed, ProximityRadar, AlertList, TrendChart
    │   │   ├── incidents/       # IncidentFilters, IncidentTable, IncidentDetailModal
    │   │   ├── workers/         # WorkerGrid, WorkerTable, WorkerFilters, AddWorkerModal
    │   │   └── VideoPlayer.tsx  # High-performance HTML5/R2 video player with frame stepping
    │   └── lib/
    │       ├── api.ts           # Axios/Fetch API client with offline fallback mock dataset
    │       └── types.ts         # TypeScript interface definitions mirroring backend models
    ├── tailwind.config.ts       # HALOCAS custom design system palette (dark/cyan/red/amber/green)
    ├── next.config.js           # Next.js 14 configuration with API reverse proxy
    └── package.json             # Frontend dependencies
```

---

## 4. Environment Peculiarities & Critical Gotchas

Any agent continuing work on this codebase **must** be aware of the following low-level system behaviors discovered and solved in this environment:

### 1. OpenCV Version 5.0 (`opencv-python 5.0.0.93`)
- **Gotcha:** `cv2.CascadeClassifier` does **NOT** exist in this OpenCV 5.0 build! Calling `cv2.CascadeClassifier(...)` raises an `AttributeError`.
- **Solution:** DeepFace must **never** be called with `detector_backend="opencv"`. Always configure DeepFace to use `detector_backend="retinaface"` or `detector_backend="skip"` when passing pre-cropped regions.

### 2. Windows UTF-8 Terminal Encoding
- **Gotcha:** TensorFlow and DeepFace log output contain Unicode emojis and special symbols (e.g. `\U0001f517`). On standard Windows PowerShell consoles running under code page 1252, this causes `UnicodeEncodeError: 'charmap' codec can't encode character`.
- **Solution:** Always invoke Python scripts with `sys.stdout.reconfigure(encoding='utf-8')` or ensure `PYTHONIOENCODING=utf-8` is passed in process environments.

### 3. Wikimedia Commons Automated Rate Limiting (HTTP 429)
- **Gotcha:** When downloading public domain fallback videos from Wikimedia Commons (`upload.wikimedia.org`), sending requests with generic or missing User-Agents triggers an immediate `429 Client Error: Too Many Requests`.
- **Solution:** Wikimedia strictly requires a contact email in the User-Agent header:
  ```python
  headers = {
      "User-Agent": "HALOCAS-Safety-Research/1.0 (safety-dev@halocas.org; mailto:safety-dev@halocas.org)",
      "Accept": "*/*",
  }
  ```

### 4. Pexels API Integration
- The script `backend/scripts/download_demo_videos.py` supports:
  - Command-line argument: `--api-key <KEY>`
  - Environment variable: `PEXELS_API_KEY`
  - Automatic parsing from local `.env`
- If no key is supplied, the script autonomously transitions to the verified open-access repository fallback, downloads the corresponding industrial videos, and standardizes them via OpenCV into valid HD MP4 files.

### 5. Python Virtual Environment Path
- Always use the workspace virtual environment:
  - Windows: `.\.venv\Scripts\python.exe`
- When executing pip or modules:
  - `.\.venv\Scripts\python.exe -m pip ...`
  - `.\.venv\Scripts\python.exe -m pytest ...`

---

## 5. Machine Learning & Biometric Pipeline Details

### YOLOv8 Object Detection & Monocular Distance
- **Model:** `yolov8n.pt` (cached locally).
- **Target Classes:** Person (class 0), and industrial vehicles (trucks, buses, cars mapped to excavators, dozers, dump trucks, forklifts).
- **Distance Estimation Formula:**
  $$\text{Distance (m)} = \frac{f_{\text{norm}} \times H_{\text{real}}}{h_{\text{bbox}}}$$
  Where $H_{\text{real}} = 1.75\text{m}$ for humans, and $h_{\text{bbox}}$ is pixel height normalized by camera calibration factor ($20.0\text{ px/m}$).

### Proximity State Machine (`backend/app/core/state_machine.py`)
- Tracks dynamic distance and closing velocity between every worker-machine pair:
  - **SAFE:** $D > 10.0\text{m}$
  - **WARNING:** $3.0\text{m} < D \le 10.0\text{m}$
  - **CRITICAL:** $D \le 3.0\text{m}$ OR $D \le 5.0\text{m}$ with closing velocity $> 1.5\text{m/s}$.
- Includes hysteresis cooldown to prevent oscillating alert spam.

### DeepFace Biometrics (`backend/app/core/face_verifier.py`)
- **Detector:** `retinaface` (robust to industrial dust, partial angles, hardhat shadows).
- **Embedder:** `Facenet512` producing normalized 512-dimensional float32 vectors.
- **Verification Metric:** Cosine similarity:
  $$\text{Sim}(v_1, v_2) = \frac{v_1 \cdot v_2}{\|v_1\|_2 \|v_2\|_2}$$
  Threshold: $0.40$ for matching active camera crops in industrial conditions, $0.65$ for strict photo-id enrollment deduplication.

---

## 6. Frontend Design System & Architecture

- **Color Tokens (Tailwind):**
  - Background Dark: `#111827` (`bg-gray-900`)
  - Panel Surface: `#1f2937` (`bg-gray-800`)
  - Border Subdued: `#374151` (`border-gray-700`)
  - Accent Cyan: `#00FFFF` (Heavy machinery indicators, telemetry sweeps)
  - Hazard Red: `#FF3B30` (Critical proximity violations, emergency alerts)
  - Warning Amber: `#F59E0B` (Advisory warning zones)
  - Safety Green: `#10B981` (Authorized personnel, safe clearance)
- **High-Performance VideoPlayer (`frontend/src/components/VideoPlayer.tsx`):**
  - Plays Cloudflare R2 presigned video URLs.
  - Controls: play/pause, seek scrub bar, speed multiplier (0.5x, 1x, 1.5x, 2x), volume slider, fullscreen.
  - Proximity Violation Timeline Marker: Displays a glowing red marker on the timeline at the exact moment of proximity infraction ($t=2.5\text{s}$).
  - Stepping Controls: Exact frame-by-frame stepping (`-1 Frame`, `+1 Frame` at 30 fps).
  - Direct download button for investigative archiving.

---

## 7. Current System State & Verified Deliverables

### A. Demo Video Ingestion (`backend/demo_data/videos/`)
All 5 HD industrial demo videos have been downloaded, standardized, and validated with OpenCV:
| Filename | Scenario Description | Resolution | Duration | Frames | File Size | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `01_construction_worker_excavator.mp4` | Construction worker near excavator | 1920x1080 | 17.7s | 530 | 28.4 MB | **VERIFIED** |
| `02_mining_heavy_machinery.mp4` | Open-pit mining haulage equipment | 1280x720 | 45.0s | 1348 | 4.9 MB | **VERIFIED** |
| `03_worker_near_bulldozer.mp4` | Earthmoving bulldozer operations | 1280x720 | 39.3s | 1178 | 39.7 MB | **VERIFIED** |
| `04_industrial_site_safety.mp4` | Site safety & construction workers | 1280x720 | 45.0s | 1348 | 8.7 MB | **VERIFIED** |
| `05_warehouse_forklift_worker.mp4` | Warehouse logistics forklift operations | 1920x1080 | 45.0s | 1350 | 15.5 MB | **VERIFIED** |

### B. Biometric Facial Extraction (`backend/demo_data/faces/`)
Extracted using DeepFace RetinaFace detection and Facenet512 embedding:
- **Unique Faces Enrolled:** 6 unique biometric identities
- **Manifest Path:** `backend/demo_data/faces/manifest.json`
- **Manifest Breakdown:**
  1. `face_0001`: `04_industrial_site_safety.mp4` (Frame 330, $t=11.0\text{s}$, conf=1.000)
  2. `face_0002`: `04_industrial_site_safety.mp4` (Frame 720, $t=24.0\text{s}$, conf=1.000)
  3. `face_0003`: `04_industrial_site_safety.mp4` (Frame 1320, $t=44.0\text{s}$, conf=1.000)
  4. `face_0004`: `05_warehouse_forklift_worker.mp4` (Frame 30, $t=1.0\text{s}$, conf=1.000)
  5. `face_0005`: `05_warehouse_forklift_worker.mp4` (Frame 270, $t=9.0\text{s}$, conf=1.000)
  6. `face_0006`: `05_warehouse_forklift_worker.mp4` (Frame 390, $t=13.0\text{s}$, conf=1.000)
- **Face Crops:** `backend/demo_data/faces/face_0001.jpg` through `face_0006.jpg`
- **Embeddings:** `backend/demo_data/faces/embeddings/face_0001.npy` through `face_0006.npy` (512 float32 vectors)

### C. Background Task Execution Status
- **Active Background Tasks:** `0` (None running; all background tasks completed successfully with exit code 0).
- **Execution Log References:**
  - `task-2131` (`download_demo_videos.py`): Completed (exit code 0).
  - `task-2137` (`extract_faces.py`): Completed (exit code 0).
  - `task-2195` (`pytest backend/tests/`): Completed (exit code 0, 113/113 passed).

### D. Automated Quality Verification Results
- **Pytest:** `113 passed, 1 warning in 6.41s` (100% pass rate)
- **Ruff:** `All checks passed!` across all backend modules and scripts
- **Mypy:** `Success: no issues found in 5 source files`
- **GitHub Actions CI:** Fully green on `main` branch.

### E. Production Database Seeding (`backend/scripts/seed_production.py`)
The production database seeding script establishes core operational personnel and equipment:
- **Database Target:** Asynchronous PostgreSQL (`halocas_db` on `localhost:5432`)
- **Seeded Workers (5 Verified Personnel):**
  1. **Rajesh Kumar** (ID=1): Drill Operator (`Drill & Blast`), Supervisor: `mine_supervisor@halocas.demo`, 512-D Facenet512 vector, Hazard Zone: Alarm (`is_authorized=False`)
  2. **Amit Sharma** (ID=2): Loader Driver (`Operations`), Supervisor: `mine_supervisor@halocas.demo`, 512-D Facenet512 vector, Hazard Zone: Alarm (`is_authorized=False`)
  3. **Priya Singh** (ID=3): Safety Inspector (Authorized Mechanic, `Health & Safety`), Supervisor: `safety_head@halocas.demo`, 512-D Facenet512 vector, Hazard Zone: Authorized Clear (`is_authorized=True`)
  4. **Suresh Patel** (ID=4): General Worker (`Operations`), Supervisor: `mine_supervisor@halocas.demo`, 512-D Facenet512 vector, Hazard Zone: Alarm (`is_authorized=False`)
  5. **Neha Gupta** (ID=5): Blasting Technician (`Drill & Blast`), Supervisor: `safety_head@halocas.demo`, 512-D Facenet512 vector, Hazard Zone: Alarm (`is_authorized=False`)
- **Seeded Heavy Equipment Fleet (3 Verified Assets):**
  1. **CAT 793F Haul Truck** (ID=1): Type `haul_truck`, Zone `pit_a`, Status `active`
  2. **Komatsu PC2000 Excavator** (ID=2): Type `excavator`, Zone `pit_a`, Status `active`
  3. **Atlas Copco SmartROC D65 Drill** (ID=3): Type `drill`, Zone `underground_b`, Status `active`
- **Biometrics & Storage Persistence:**
  - Facial embeddings loaded from `.npy` files and persisted as 512-float arrays in the `workers.face_embedding` column.
  - Portraits referenced via canonical Cloudflare R2 URLs (`workers/photos/{slug}_{face_id}.jpg`).

### F. End-to-End Demo Pipeline Runner (`backend/scripts/run_demo_pipeline.py`)
- **Execution Mandate:** Sequentially loads all 5 industrial demo videos, executing full real-time CV tracking, spatial state machine physics, biometric matching, cyclic buffer export, R2 storage upload, and PostgreSQL incident persistence.
- **Execution Run Statistics:**
  - **Total Frames Processed:** 5,754 frames across 5 videos
  - **Throughput:** 21.0 FPS steady-state processing
  - **Hazard Breaches Evaluated:** 34 Critical events, 97 Warning events
  - **Incidents Logged in PostgreSQL:** 4 verified incidents (Requirement: $\ge 3$)
  - **Annotated Videos Output:** 5 high-definition MP4 videos saved in `backend/demo_data/annotated/` (155.96 MB total)
    1. `annotated_01_construction_worker_excavator.mp4` (24.00 MB, 530 frames)
    2. `annotated_02_mining_heavy_machinery.mp4` (11.71 MB, 1,348 frames)
    3. `annotated_03_worker_near_bulldozer.mp4` (48.25 MB, 1,178 frames)
    4. `annotated_04_industrial_site_safety.mp4` (14.55 MB, 1,348 frames)
    5. `annotated_05_warehouse_forklift_worker.mp4` (24.32 MB, 1,350 frames)

### G. GitHub Actions CI Pipeline Diagnosis & Resolution
- **Failing Run Identified:** Run ID `33906966949` (`feat(scripts): add seed_production.py...`)
- **Root Cause Diagnosis:**
  - `backend/tests/test_config.py:11: error: Unexpected keyword argument "_env_file" for "Settings" [call-arg]`
  - Pydantic-settings `BaseSettings` handles `_env_file` at runtime, but the Mypy Pydantic plugin generates strict constructor signatures that flag private kwargs.
- **Remediation Implemented:**
  - Added `# type: ignore[call-arg]` on line 11 of `backend/tests/test_config.py`.
  - Audited and verified `mypy .` and `ruff check .` from repo root: 65 source files checked with 0 errors.
  - Verified full test suite: 113/113 pytest tests passing (84% code coverage).

### H. Comprehensive Unit Testing & Code Coverage Expansion (88% Target Achieved)
- **Requirement:** Ensure every module has comprehensive unit tests with $\ge 85\%$ code coverage across all 10 target files:
  1. `tests/test_config.py` (100% coverage)
  2. `tests/test_detector.py` (98% coverage)
  3. `tests/test_face_verifier.py` (88% coverage)
  4. `tests/test_state_machine.py` (97% coverage)
  5. `tests/test_buffer.py` (96% coverage)
  6. `tests/test_notification.py` (87% coverage)
  7. `tests/test_storage.py` (97% coverage)
  8. `tests/test_pipeline.py` (86% coverage)
  9. `tests/test_models.py` (100% coverage across all models, base, and user)
  10. `tests/test_auth.py` (100% coverage across security, deps, routes/auth, and 90% session)
- **New Unit Test Implementation:**
  - Authored `backend/tests/test_auth.py` with comprehensive unit test cases covering bcrypt hashing, corrupted hash handling, JWT encoding/decoding, expired token errors, custom claims, async database session generators, dependency injection, and RBAC authorization.
  - Enhanced `backend/tests/test_models.py` with user representation and generic declarative base representation tests.
  - Enhanced `backend/tests/test_health.py` with application lifespan verification and global 500 unhandled exception handling.
- **Verification Results:**
  - `pytest --cov=app --cov-report=term-missing`: **141/141 passed in 14.54s**
  - **Overall Code Coverage:** **88%** (2,102 statements, 245 missed = 88.34%) exceeding the $\ge 85\%$ threshold.
  - `ruff check`: All checks passed.
  - `mypy`: Success, no issues found in 58 source files.
- **Active Background Tasks:** `0` (all test runs and background tasks exited cleanly with code 0).


