# Development Guide

This document covers everything you need to set up, run, test, and contribute to OnboardIQ locally.

---

## 1. Prerequisites

Before you begin, make sure you have the following installed:

- **Python 3.12+** -- the backend targets 3.12 features and type hints.
- **Node.js 20+** -- required for the React/Vite frontend.
- **Docker and Docker Compose** -- used to run PostgreSQL, Redis, and ChromaDB.

You will also need the following API keys:

| Variable | Required | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API key for all LLM calls. |
| `VOYAGE_API_KEY` | Yes (production) | Voyage AI embeddings. Optional in dev -- falls back to a local model. |
| `LANGSMITH_API_KEY` | No | Enables LangSmith tracing for debugging agent pipelines. |

---

## 2. Local Setup

### Full stack via Docker (recommended)

```bash
# Clone and enter the project
git clone https://github.com/YOUR_USERNAME/onboardiq.git
cd onboardiq

# Configure environment
cp .env.example .env
# Edit .env to add ANTHROPIC_API_KEY and VOYAGE_API_KEY

# Start all services (PostgreSQL, Redis, ChromaDB, backend, frontend)
docker compose up

# In another terminal, ingest the Stripe documentation into the vector store
cd backend
python -m scripts.ingest_stripe_docs

# Visit http://localhost:3000
```

### Running the backend outside Docker

If you prefer to run the FastAPI server directly on your machine (useful for faster reload cycles and debugger attachment):

```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

You will still need Docker running for PostgreSQL, Redis, and ChromaDB. Start only the infrastructure services with:

```bash
docker compose up postgres redis chromadb
```

---

## 3. Running Tests

All tests use pytest and live under `backend/tests/`, mirroring the source tree structure.

```bash
cd backend

# Run the full test suite
pytest

# Run a specific test module with verbose output
pytest tests/test_rag/test_chunking.py -v

# Run with coverage and generate an HTML report
pytest --cov=app --cov-report=html

# Run only RAG tests
pytest tests/test_rag/ -v

# Run only API tests
pytest tests/test_api/ -v
```

Coverage reports are written to `backend/htmlcov/`. Open `htmlcov/index.html` in a browser to inspect line-by-line coverage.

---

## 4. Code Quality

The project uses Ruff for linting and formatting, and mypy for static type checking. Configuration lives in `pyproject.toml` (target Python 3.12, line length 100, enabled rule sets: E, F, I, N, W, UP).

```bash
cd backend

# Lint with Ruff
ruff check .

# Auto-fix lint issues
ruff check . --fix

# Format with Ruff
ruff format .

# Type checking with mypy
mypy app/
```

Run all three before opening a pull request. CI will reject code that fails linting or type checking.

---

## 5. Adding a New Product

OnboardIQ currently ships with Stripe documentation. To add support for a new product:

1. **Create documentation files** in `backend/data/docs/{product_name}/`. Each file should include YAML frontmatter with metadata (title, category, etc.) that the ingestion pipeline uses for chunk enrichment.

2. **Run ingestion** to populate the vector store:
   ```bash
   python -m scripts.ingest_stripe_docs
   ```
   For a new product, generalize the existing script or create a dedicated one (e.g., `ingest_{product_name}_docs`).

3. **Register the product** by adding it to the `SupportedProduct` enum in `backend/app/models/schemas.py`.

4. **Add a product entry** in the `PRODUCTS` dict inside `backend/app/api/products.py`, including display name, description, and available roles.

5. **Verify retrieval** by hitting the debug endpoint:
   ```
   GET /api/products/debug/retrieve?query=test&product={product_name}
   ```

---

## 6. Adding a New Role

Roles determine how the guide content is adapted. To add a new role:

1. Add the role to the `UserRole` enum in `backend/app/models/schemas.py`.
2. Update the role profiler XML prompt in `backend/app/agents/prompts/role_profiler.xml` with descriptions and expectations for the new role.
3. Add golden dataset entries for the new role in `backend/app/evaluation/golden_dataset.json` so the evaluation pipeline can score guide quality.
4. Add the role to `available_roles` in the product registry entry (see `backend/app/api/products.py`).
5. Run the evaluation suite to verify that generated guides for the new role meet quality thresholds across all five dimensions.

---

## 7. Modifying Prompts

All agent prompts live in `backend/app/agents/prompts/` as XML files:

- `role_profiler.xml` -- analyzes the user's role and experience level.
- `content_curator.xml` -- selects and orders retrieved content.
- `guide_generator.xml` -- produces the onboarding guide sections.
- `quality_evaluator.xml` -- scores output on the 5-dimension rubric.

The XML format is intentional. Claude was trained on XML-structured data and performs measurably better with structured XML prompts compared to plain text or JSON.

After modifying any prompt:

1. Run the evaluation suite (`pytest tests/test_evaluation/`) to check for regressions.
2. Use LangSmith tracing to inspect the exact input/output for each agent node. This is the fastest way to debug prompt issues. Set `LANGSMITH_API_KEY` in your `.env` to enable tracing.

---

## 8. Database Migrations

The project uses Alembic with async SQLAlchemy. Migration files live in `backend/alembic/versions/`. The database URL is configured in `backend/app/config.py` via Pydantic settings.

```bash
cd backend

# Create a new migration (auto-detects model changes)
alembic revision --autogenerate -m "description of change"

# Apply all pending migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1

# View the current migration version
alembic current
```

Always review autogenerated migrations before committing. Alembic does not detect all changes (e.g., column renames, constraint modifications) and some operations may need manual adjustment.

---

## 9. Project Structure

```
onboardiq/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI route handlers (REST + SSE)
│   │   ├── models/           # Pydantic schemas + SQLAlchemy ORM models
│   │   ├── services/         # Business logic layer
│   │   ├── agents/           # LangGraph pipeline nodes + XML prompts
│   │   ├── rag/              # Ingestion, embeddings, vectorstore, retriever, reranker
│   │   ├── evaluation/       # LLM judge, RAGAS, golden dataset, metrics
│   │   ├── infrastructure/   # DB sessions, cache, LangSmith tracing
│   │   ├── config.py         # Pydantic settings (env vars, defaults)
│   │   └── main.py           # FastAPI app factory
│   ├── scripts/              # CLI tools (documentation ingestion)
│   ├── tests/                # pytest test suite (mirrors app/ structure)
│   ├── alembic/              # Database migration versions
│   └── data/docs/            # Product documentation source files
├── frontend/
│   └── src/
│       ├── components/       # React UI components
│       ├── hooks/            # useSSE, useGuideGeneration
│       ├── api/              # API client (Axios)
│       └── types/            # TypeScript types mirroring backend schemas
├── docs/                     # Architecture docs + ADRs
├── docker-compose.yml
└── CLAUDE.md
```

---

## Conventions

- **Python**: Ruff formatting, type hints on all function signatures, async/await throughout.
- **TypeScript**: Strict mode enabled, no `any` types.
- **Commits**: Follow conventional commits -- `feat:`, `fix:`, `docs:`, `test:`, `refactor:`.
- **Schemas**: All Pydantic models belong in `schemas.py` as the single source of truth.
- **SSE events**: Every agent node must emit `agent_start` and `agent_complete` events for frontend progress tracking.
- **Cost tracking**: Token usage and estimated cost must be recorded through the entire pipeline.
