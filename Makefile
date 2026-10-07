.PHONY: help install dev lint type-check test run-api run-dashboard docker-up docker-down clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -e .

dev:  ## Install development dependencies
	pip install -e ".[dev]"
	pre-commit install

lint:  ## Run linter (ruff)
	ruff check .
	ruff format --check .

format:  ## Auto-format code
	ruff check --fix .
	ruff format .

type-check:  ## Run type checker (mypy)
	mypy api core preprocessing image_analytics nlp fusion risk db

test:  ## Run test suite
	pytest tests/ -v --cov=. --cov-report=term-missing

test-unit:  ## Run unit tests only
	pytest tests/unit/ -v

test-integration:  ## Run integration tests
	pytest tests/integration/ -v -m integration

run-api:  ## Start API server (development)
	uvicorn api.main:app --reload --port 8000

run-dashboard:  ## Start Streamlit dashboard
	streamlit run dashboard/app.py

docker-up:  ## Start all services via Docker Compose
	docker compose -f docker/docker-compose.yml up -d --build

docker-down:  ## Stop all Docker services
	docker compose -f docker/docker-compose.yml down

docker-logs:  ## View Docker logs
	docker compose -f docker/docker-compose.yml logs -f

migrate:  ## Run database migrations
	alembic upgrade head

migrate-create:  ## Create a new migration (usage: make migrate-create MSG="add foo")
	alembic revision --autogenerate -m "$(MSG)"

clean:  ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ *.egg-info
