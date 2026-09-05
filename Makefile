.PHONY: up down logs migrate backend-test backend-check frontend-test frontend-check verify

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	docker compose run --rm backend alembic upgrade head

backend-test:
	docker compose run --rm --no-deps backend pytest

backend-check:
	docker compose run --rm --no-deps backend sh -c "ruff check . && ruff format --check . && mypy app"

frontend-test:
	docker compose run --rm --no-deps frontend npm run test

frontend-check:
	docker compose run --rm --no-deps frontend sh -c "npm run lint && npm run typecheck && npm run build"

verify: backend-check backend-test frontend-check frontend-test

