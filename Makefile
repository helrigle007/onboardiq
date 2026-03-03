.PHONY: up down build dev test lint format eval ingest clean logs shell

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

shell:
	docker compose exec backend bash

# Database
db-migrate:
	docker compose exec backend alembic upgrade head

db-revision:
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

# Testing
test:
	cd backend && pytest tests/ -v --cov=app --cov-report=term-missing

test-fast:
	cd backend && pytest tests/ -x -q

# Code quality
lint:
	cd backend && ruff check . && mypy app/ --ignore-missing-imports
	cd frontend && npm run lint && npx tsc --noEmit

format:
	cd backend && ruff format .

# Data
ingest:
	cd backend && python -m scripts.ingest_stripe_docs

eval:
	cd backend && python -m app.evaluation.ragas_eval --all

# Cleanup
clean:
	docker compose down -v
	rm -rf backend/data/chroma/*
	rm -rf frontend/dist
