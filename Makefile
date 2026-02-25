.PHONY: install test lint format clean run-api init-db migrate

install:
	pip install -e .
	pip install -e ".[dev]"

test:
	pytest tests/ -v --cov=docagentline --cov-report=html

lint:
	ruff check docagentline/

format:
	ruff format docagentline/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache .coverage htmlcov/
	rm -f *.db *.db-shm *.db-wal

run-api:
	python scripts/run_api.py

init-db:
	python scripts/init_db.py

migrate:
	alembic upgrade head

docker-build:
	docker build -t docagentline:latest .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f api
