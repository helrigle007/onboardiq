# CLAUDE.md — OnboardIQ Project Instructions

## What is this project?
OnboardIQ is a portfolio project: an AI-powered SaaS onboarding guide generator.
It ingests product documentation (Stripe) and generates personalized, role-adaptive
onboarding guides using a multi-agent LangGraph pipeline with a 5-dimension
LLM-as-judge evaluation system.

## Tech Stack
- **Frontend:** React 18 + TypeScript + Vite + Tailwind CSS + Recharts
- **Backend:** Python 3.12 + FastAPI + SQLAlchemy (async) + Alembic
- **AI/ML:** LangChain + LangGraph + Claude API (Anthropic) + Voyage AI embeddings
- **RAG:** ChromaDB (vector) + BM25 (keyword) + Cross-encoder reranker
- **Infra:** Docker Compose (PostgreSQL, Redis, ChromaDB)
- **Eval:** RAGAS + custom LLM-as-judge + LangSmith tracing

## Key Architecture Decisions
- Sequential section generation (not parallel) for progressive complexity
- ChromaDB for dev, pgvector migration path documented
- Hybrid retrieval: 70% vector / 30% BM25 with cross-encoder reranking
- Anthropic's Contextual Retrieval technique for chunk enrichment
- XML-structured prompts (Claude was trained on them)
- SSE streaming for real-time pipeline progress
- 5-dimension evaluation: completeness, role_relevance, actionability, clarity, progressive_complexity

## Project Structure
```
backend/app/
  api/         — FastAPI endpoints (REST + SSE)
  models/      — Pydantic schemas + SQLAlchemy models
  services/    — Business logic
  agents/      — LangGraph nodes (role_profiler, content_curator, guide_generator, quality_evaluator)
  rag/         — Ingestion, embeddings, vectorstore, retriever, reranker
  evaluation/  — LLM judge, RAGAS, golden dataset, metrics
  infrastructure/ — DB, cache, tracing
frontend/src/
  components/  — React components
  hooks/       — useSSE, useGuideGeneration
  types/       — TypeScript types mirroring backend schemas
  api/         — API client
```

## Commands
```bash
docker compose up          # Start all services
cd backend && pytest       # Run tests
cd backend && ruff check . # Lint
cd frontend && npm run dev # Frontend dev server
```

## Conventions
- Python: Ruff formatting, type hints everywhere, async/await
- TypeScript: Strict mode, no `any` types
- Commits: Conventional commits (feat:, fix:, docs:, test:)
- All Pydantic models in schemas.py — single source of truth
- All prompts in backend/app/agents/prompts/*.xml
- Tests mirror source structure in tests/

## Environment Variables (required)
- ANTHROPIC_API_KEY — Claude API key
- VOYAGE_API_KEY — Voyage AI embeddings

## Important Notes
- The evaluation pipeline (5-dimension LLM-as-judge) is the PORTFOLIO CENTERPIECE
- Don't skip error handling — production-readiness is the whole point
- Every agent node should emit SSE events (agent_start, agent_complete)
- Token usage and cost must be tracked through the entire pipeline
- Guide sections are generated sequentially, not in parallel (ADR-004)
