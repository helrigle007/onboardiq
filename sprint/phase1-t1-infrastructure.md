# Phase 1 — Terminal 1: Infrastructure & Project Scaffolding

## Overview
You are setting up the foundational project structure, Docker infrastructure, configuration system, database, and observability for OnboardIQ — an agentic RAG application. You run FIRST. The other 3 terminals will build on top of your scaffold.

## Pre-flight
```bash
git init
git checkout -b infra/scaffolding
```

## Task 1: Create Project Directory Structure

Create the entire directory skeleton. Other terminals will populate these files.

```
onboardiq/
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── .gitkeep
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── router.py
│   │   │   ├── guides.py
│   │   │   ├── products.py
│   │   │   ├── evaluations.py
│   │   │   └── health.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── database.py
│   │   │   └── schemas.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── guide_service.py
│   │   │   └── product_service.py
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── graph.py
│   │   │   ├── state.py
│   │   │   ├── role_profiler.py
│   │   │   ├── content_curator.py
│   │   │   ├── guide_generator.py
│   │   │   ├── quality_evaluator.py
│   │   │   └── prompts/
│   │   │       ├── role_profiler.xml
│   │   │       ├── content_curator.xml
│   │   │       ├── guide_generator.xml
│   │   │       └── quality_evaluator.xml
│   │   ├── rag/
│   │   │   ├── __init__.py
│   │   │   ├── ingestion.py
│   │   │   ├── embeddings.py
│   │   │   ├── vectorstore.py
│   │   │   ├── retriever.py
│   │   │   └── reranker.py
│   │   ├── evaluation/
│   │   │   ├── __init__.py
│   │   │   ├── llm_judge.py
│   │   │   ├── ragas_eval.py
│   │   │   ├── metrics.py
│   │   │   └── golden_dataset.json
│   │   └── infrastructure/
│   │       ├── __init__.py
│   │       ├── database.py
│   │       ├── cache.py
│   │       └── tracing.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_agents/
│   │   │   └── __init__.py
│   │   ├── test_rag/
│   │   │   └── __init__.py
│   │   ├── test_evaluation/
│   │   │   └── __init__.py
│   │   └── test_api/
│   │       └── __init__.py
│   └── data/
│       ├── docs/
│       │   └── stripe/
│       │       └── .gitkeep
│       └── chroma/
│           └── .gitkeep
├── frontend/
│   └── .gitkeep
├── docs/
│   ├── architecture.md
│   ├── deployment.md
│   ├── evaluation.md
│   ├── development.md
│   └── adr/
│       └── .gitkeep
├── .github/
│   ├── workflows/
│   │   └── .gitkeep
│   ├── ISSUE_TEMPLATE/
│   │   └── .gitkeep
│   └── pull_request_template.md
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── Makefile
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

For files in directories that other terminals will fully implement (agents/, rag/, evaluation/, frontend/), just create placeholder files with a docstring comment like:
```python
"""Placeholder — implemented by [stream name]."""
```

## Task 2: pyproject.toml

```toml
[project]
name = "onboardiq"
version = "0.1.0"
description = "Role-adaptive SaaS onboarding guide generator powered by agentic RAG"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.5.0",
    "sqlalchemy>=2.0.35",
    "alembic>=1.13.0",
    "asyncpg>=0.30.0",
    "redis>=5.1.0",
    "httpx>=0.27.0",
    "langchain>=0.3.0",
    "langchain-anthropic>=0.3.0",
    "langchain-community>=0.3.0",
    "langchain-chroma>=0.2.0",
    "langgraph>=0.2.0",
    "langsmith>=0.1.0",
    "chromadb>=0.5.0",
    "voyageai>=0.3.0",
    "sentence-transformers>=3.0.0",
    "rank-bm25>=0.2.2",
    "ragas>=0.2.0",
    "beautifulsoup4>=4.12.0",
    "markdownify>=0.13.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.6.0",
    "mypy>=1.11.0",
    "httpx>=0.27.0",
]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.mypy]
python_version = "3.12"
strict = false
warn_return_any = true
warn_unused_configs = true
```

## Task 3: Configuration System

```python
# backend/app/config.py

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # API Keys
    anthropic_api_key: str
    voyage_api_key: str = ""
    langsmith_api_key: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://onboardiq:onboardiq@localhost:5432/onboardiq"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8001

    # LangSmith
    langsmith_project: str = "onboardiq"
    langsmith_tracing: bool = True

    # Generation tuning
    eval_threshold: float = 0.7
    max_regenerations: int = 2
    guide_sections_count: int = 6
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retrieval_top_k: int = 20

    # Models
    generation_model: str = "claude-sonnet-4-20250514"
    evaluation_model: str = "claude-sonnet-4-20250514"
    fast_model: str = "claude-haiku-4-5-20251001"
    embedding_model: str = "voyage-3"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

## Task 4: FastAPI App Factory

```python
# backend/app/main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.router import api_router
from app.infrastructure.database import init_db, close_db
from app.infrastructure.tracing import setup_tracing


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await init_db()
    setup_tracing(settings)
    yield
    await close_db()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="OnboardIQ",
        description="Role-adaptive SaaS onboarding guide generator",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    return app


app = create_app()
```

## Task 5: Infrastructure Layer

### Database (SQLAlchemy async)
```python
# backend/app/infrastructure/database.py

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import get_settings

engine = None
async_session_factory = None


async def init_db():
    global engine, async_session_factory
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False, pool_size=5)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def close_db():
    global engine
    if engine:
        await engine.dispose()


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
```

### Cache (Redis)
```python
# backend/app/infrastructure/cache.py

import redis.asyncio as redis
from app.config import get_settings

_redis_client = None


async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def cache_get(key: str) -> str | None:
    r = await get_redis()
    return await r.get(key)


async def cache_set(key: str, value: str, ttl: int = 3600) -> None:
    r = await get_redis()
    await r.set(key, value, ex=ttl)
```

### Tracing (LangSmith)
```python
# backend/app/infrastructure/tracing.py

import os
from app.config import Settings


def setup_tracing(settings: Settings) -> None:
    """Configure LangSmith tracing via environment variables."""
    if settings.langsmith_api_key and settings.langsmith_tracing:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
```

## Task 6: Docker Compose

```yaml
# docker-compose.yml

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql+asyncpg://onboardiq:onboardiq@postgres:5432/onboardiq
      - REDIS_URL=redis://redis:6379
      - CHROMA_HOST=chroma
      - CHROMA_PORT=8000
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      chroma:
        condition: service_started
    volumes:
      - ./backend:/app
      - backend-data:/app/data

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - backend

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: onboardiq
      POSTGRES_USER: onboardiq
      POSTGRES_PASSWORD: onboardiq
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U onboardiq"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  chroma:
    image: chromadb/chroma:0.5.23
    ports:
      - "8001:8000"
    volumes:
      - chromadata:/chroma/chroma
    environment:
      - IS_PERSISTENT=TRUE
      - ANONYMIZED_TELEMETRY=FALSE

volumes:
  pgdata:
  chromadata:
  backend-data:
```

## Task 7: Dockerfiles

### Backend
```dockerfile
# Dockerfile.backend
FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml .
RUN pip install --no-cache-dir -e "."

COPY backend/ .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### Frontend
```dockerfile
# Dockerfile.frontend
FROM node:20-alpine AS base

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ .

EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
```

## Task 8: Alembic Setup

Configure alembic.ini and env.py for async SQLAlchemy. The initial migration should create the `guides` and `evaluation_runs` tables.

Use the models from this schema (create placeholder in database.py):

```python
# Minimal table definitions for the migration
# guides: id (String PK), product, role, experience_level, title, description,
#          sections (JSON), evaluation (JSON), metadata (JSON),
#          focus_areas (JSON), tech_stack (JSON), created_at (DateTime)
# evaluation_runs: id (String PK), guide_id (String, indexed), run_type,
#                  overall_score (Float), dimension_scores (JSON),
#                  section_scores (JSON), ragas_metrics (JSON),
#                  tokens_used (Int), cost_usd (Float),
#                  latency_seconds (Float), created_at (DateTime)
```

## Task 9: Makefile

```makefile
.PHONY: up down build dev test lint

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

dev:
	docker compose up

logs:
	docker compose logs -f

backend-shell:
	docker compose exec backend bash

db-migrate:
	docker compose exec backend alembic upgrade head

db-revision:
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

test:
	cd backend && pytest tests/ -v --cov=app

lint:
	cd backend && ruff check . && mypy app/ --ignore-missing-imports

format:
	cd backend && ruff format .
```

## Task 10: Environment & Git Config

### .env.example
```bash
# Required
ANTHROPIC_API_KEY=sk-ant-your-key-here
VOYAGE_API_KEY=voy-your-key-here

# Optional — LangSmith observability
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=onboardiq

# Tuning (defaults are fine)
EVAL_THRESHOLD=0.7
MAX_REGENERATIONS=2
GUIDE_SECTIONS_COUNT=6
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
RETRIEVAL_TOP_K=20
```

### .gitignore
```
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
.venv/
venv/

# Node
node_modules/
frontend/dist/

# Environment
.env
.env.local

# Data
backend/data/chroma/
backend/data/docs/stripe/*.md
*.db

# IDE
.vscode/
.idea/

# Docker
*.log

# OS
.DS_Store
Thumbs.db
```

### Minimal README.md
```markdown
# OnboardIQ

Role-adaptive SaaS onboarding guide generator powered by agentic RAG.

> Under construction — see [SPRINT-PLAN.md](SPRINT-PLAN.md) for status.

## Quick Start

```bash
cp .env.example .env
# Add your ANTHROPIC_API_KEY and VOYAGE_API_KEY to .env
docker compose up
```

## License
MIT
```

## Task 11: API Router Skeleton + Health Endpoint

```python
# backend/app/api/router.py
from fastapi import APIRouter
from app.api import guides, products, evaluations, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(guides.router, prefix="/api/guides", tags=["guides"])
api_router.include_router(products.router, prefix="/api/products", tags=["products"])
api_router.include_router(evaluations.router, prefix="/api/evaluations", tags=["evaluations"])
```

```python
# backend/app/api/health.py
from fastapi import APIRouter
from app.config import get_settings

router = APIRouter()

@router.get("/api/health")
async def health_check():
    settings = get_settings()
    return {
        "status": "healthy",
        "version": "0.1.0",
        "models": {
            "generation": settings.generation_model,
            "evaluation": settings.evaluation_model,
            "fast": settings.fast_model,
        },
    }
```

For the other API files (guides.py, products.py, evaluations.py), create stubs:
```python
from fastapi import APIRouter
router = APIRouter()
# Endpoints implemented by T3: Models + API stream
```

## Completion Criteria
- [ ] `git clone` + `docker compose up` boots all 5 services (backend, frontend, postgres, redis, chroma)
- [ ] `GET /api/health` returns 200 with model info
- [ ] `GET /docs` shows Swagger UI
- [ ] All directories exist with correct __init__.py files
- [ ] Alembic migration creates both tables in PostgreSQL
- [ ] .env.example documents all variables
- [ ] .gitignore covers Python, Node, env, data directories

## Final Steps
```bash
git add -A
git commit -m "feat: project scaffolding, Docker infrastructure, config system

- Docker Compose with backend, frontend, postgres, redis, chroma
- FastAPI app factory with CORS, lifespan management
- Pydantic Settings config with all env vars
- SQLAlchemy async + Alembic migrations
- Redis caching layer
- LangSmith tracing setup
- Health endpoint
- Full project directory structure"
```

**Do NOT merge to main yet.** Other terminals will branch from this commit.
