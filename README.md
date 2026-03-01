# VoidFill

**Voice-first AI co-pilot that fills your free time with purpose.**

> "You don't lack goals. You lack a system that uses your free time for them."

---

## Live Demo

🔗 **[https://void-fill-production.up.railway.app](https://void-fill-production.up.railway.app)**

## GitHub

[https://github.com/The-FOOL-00/Void-Fill](https://github.com/The-FOOL-00/Void-Fill)

---

## What It Does

VoidFill automatically detects free gaps in your schedule and fills them with actions that move your real goals forward. When a void is found it suggests 2–3 contextual activities via voice — you pick one by speaking or tapping, and it lands on your calendar instantly. Over time the system learns your habits, energy patterns, and goal priorities so suggestions get sharper every week. The Phase 15 autonomy engine goes one step further: it can schedule your best next action *without being asked*, turning dead time into momentum on autopilot.

---

## Tech Stack

### Current Build (deployed)

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Vite 6 + CSS Modules |
| Voice I/O | Web Speech API / MediaRecorder (browser) |
| Backend | FastAPI + Python 3.11 + SQLAlchemy 2 + Pydantic v2 |
| Auth | JWT (python-jose) + bcrypt — Bearer token, register/login with demo-skip |
| Database | Neon PostgreSQL 17 + pgvector (cloud, semantic search enabled) |
| Transcription | faster-whisper (CTranslate2) |
| LLM | Google Gemini 2.5 Pro |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2, 384-dim) |
| Queue | Redis + background workers |
| Deployment | Railway · Docker · nginx · supervisord |

### AMD Production Vision

| Component | Target |
|-----------|--------|
| Transcription | Whisper running on AMD Ryzen AI NPU via ONNX Runtime |
| LLM | Mistral 7B served by Ollama on-device (ROCm) |
| Personalisation | Reinforcement-learning loop on RDNA GPU |
| Privacy | Zero cloud dependency — zero data leaves the device |

---

## Authentication

VoidFill uses JWT-based authentication.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/register` | POST | Create account → returns `access_token` |
| `/api/v1/auth/login` | POST | Sign in → returns `access_token` |
| `/api/v1/auth/login/token` | POST | OAuth2 form login (for `/docs`) |

All protected endpoints require `Authorization: Bearer <token>`. The frontend also supports **"Continue without account"** which runs in demo mode using a shared demo user ID.

---

## Local Setup

### 1. Clone & configure

```bash
git clone https://github.com/The-FOOL-00/Void-Fill.git
cd Void-Fill
cp .env.example backend/.env
# Edit backend/.env — set GEMINI_API_KEY, SECRET_KEY, and database credentials
```

### 2. Start the stack

```bash
docker compose up --build
```

This launches **Backend API** (`:8000`), **Voice Worker** (faster-whisper), **PostgreSQL** + pgvector, and **Redis**.

> **Cloud option**: Set `DATABASE_URL` to a Neon connection string (with `sslmode=require`) — the app strips incompatible asyncpg parameters automatically and enables SSL.

### 3. Install frontend dependencies

```bash
cd frontend
npm install
```

### 4. Run the frontend dev server

```bash
npm run dev
```

Opens at `http://localhost:3000` — Vite proxies `/api` to the backend automatically.

### 5. Open the app

Navigate to `http://localhost:3000`. Register an account or tap **Continue without account** to explore in demo mode.

---

## Environment Variables

All variables live in `backend/.env`. Copy from [.env.example](.env.example) and fill in secrets.

| Variable | Purpose | Default |
|----------|---------|---------|
| `APP_NAME` | Application display name | `VoidFill` |
| `APP_VERSION` | Semantic version | `1.0.0` |
| `DEBUG` | Enable debug mode | `false` |
| `ENVIRONMENT` | `production` / `development` | `production` |
| `HOST` | Server bind address | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `WORKERS` | Uvicorn worker count | `1` |
| `DATABASE_URL` | Full async DB URL (overrides individual POSTGRES_* vars) | — |
| `POSTGRES_HOST` | PostgreSQL hostname | `postgres` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_USER` | Database user | `voidfill` |
| `POSTGRES_PASSWORD` | Database password | *(required)* |
| `POSTGRES_DB` | Database name | `voidfill` |
| `REDIS_HOST` | Redis hostname | `redis` |
| `REDIS_PORT` | Redis port | `6379` |
| `REDIS_DB` | Redis database index | `0` |
| `REDIS_PASSWORD` | Redis password (blank for local) | — |
| `SECRET_KEY` | JWT signing key | *(required in prod)* |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token TTL | `60` |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `EMBEDDING_MODEL` | sentence-transformers model name | `all-MiniLM-L6-v2` |
| `EMBEDDING_DIMENSION` | Vector dimension for pgvector | `384` |
| `GEMINI_API_KEY` | Google Gemini API key — also accepts `GOOGLE_API_KEY` | *(required)* |
| `VOICE_UPLOAD_DIR` | Temp path for audio uploads | `/tmp/voidfill_voice` |
| `MAX_VOICE_FILE_SIZE_MB` | Max upload size | `25` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `LOG_FORMAT` | Log format (`json` / `console`) | `json` |

---

## Architecture

VoidFill was built across 17 phases: **Phases 1–6** laid the backend foundation — FastAPI skeleton, PostgreSQL + pgvector models, repository layer, and core services. **Phases 7–10** introduced the AI engines — Gemini-powered LLM service, voice transcription pipeline (faster-whisper → Redis worker), embedding service for semantic retrieval, and the suggestion/void-detection loop. **Phases 11–15** added intelligence layers — goal memory, habit tracking, weekly reflection analytics, and the Phase 15 autonomy engine that schedules actions without user intervention. **Phase 16** delivered the full React 18 frontend — onboarding, voice-first home screen, goals, reflection, settings, and the autonomy dashboard. **Phase 17** hardened everything for production — JWT auth, Neon pgvector cloud, Railway deployment, security audit, and documentation.

```
frontend/              React 18 · Vite · TypeScript · CSS Modules
backend/
  app/
    api/v1/            FastAPI route handlers (auth, voice, goals, schedule, suggestions, void, notes)
    services/          Business logic — LLM, voice, autonomy engine, embeddings, scheduling
    repositories/      SQLAlchemy ORM data-access layer
    models/            Database models with pgvector embedding columns
    workers/           Background voice transcription (faster-whisper via Redis queue)
    schemas/           Pydantic v2 request / response models
    core/              Config, database, Redis, security (JWT + bcrypt), structured logging
```

---

## Team

Team: **VoidFill**

---

Built for **AMD Slingshot 2026** — *Future of Work & Productivity* track.
