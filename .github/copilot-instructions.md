# Project Guidelines - Void-Fill Backend

This workspace contains a modern, asynchronous FastAPI application that powers an AI-driven "Void-Fill" system. It follows a clean, layered architecture and integrates with LLMs, transcription services, and vector databases.

## Code Style
- **Asynchronous First**: Use `async/await` for all I/O-bound operations (API endpoints, DB queries, service calls).
- **Type Safety**: Use Python 3.10+ type hints for all function signatures and complex variables.
- **Pydantic v2**: Use Pydantic models in [backend/app/schemas/](backend/app/schemas/) for request/response validation and configuration management.
- **Structured Logging**: Use `structlog` for application logs as configured in [backend/app/core/logging.py](backend/app/core/logging.py).

## Architecture
This project follows a **Domain-Driven Design (DDD) inspired layered architecture**:
- **API (v1)**: [backend/app/api/v1/](backend/app/api/v1/) defines routes and handles dependency injection for DB sessions.
- **Service Layer**: [backend/app/services/](backend/app/services/) contains business logic and orchestrates between multiple repositories and external AI APIs.
- **Repository Layer**: [backend/app/repositories/](backend/app/repositories/) encapsulates SQLAlchemy ORM operations.
- **Models**: [backend/app/models/](backend/app/models/) defines SQLAlchemy tables, including `pgvector` support for embeddings.
- **Workers**: [backend/app/workers/](backend/app/workers/) handles asynchronous background tasks (transcription, intelligence processing).

## Build and Test
- **Docker Compose**: The primary way to run the entire stack is via `docker-compose up --build`.
- **Backend Setup**:
  1. `cd backend`
  2. `pip install -r requirements.txt` (or use a virtualenv)
  3. Set up `.env` from `.env.example`.
- **Database**: Uses PostgreSQL with the `pgvector` extension for semantic search.

## Project Conventions
- **Lifecycle Management**: Application startup/shutdown is managed via the `lifespan` handler in [backend/app/main.py](backend/app/main.py).
- **Dependency Injection**: Use FastAPI `Depends()` for database sessions and configuration objects.
- **Error Handling**: Use custom exceptions defined in [backend/app/core/exceptions.py](backend/app/core/exceptions.py).
- **Vector Search**: Use `pgvector` in models like `VoiceIntelligence` for semantic retrieval.

## Integration Points
- **LLM/AI**: Integrates with Google Generative AI and `sentence-transformers` for embeddings.
- **Transcription**: Uses `faster-whisper` for processing audio in the worker.
- **Cache/Queue**: Redis is used for communication between the API and background workers.

## Security
- **CORS**: Configured in [backend/app/main.py](backend/app/main.py) to allow cross-origin requests.
- **Custom Auth**: Check [backend/app/core/security.py](backend/app/core/security.py) (if present) for authentication patterns and `AuthenticationError` handling.
