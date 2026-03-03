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
