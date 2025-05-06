.PHONY: migrate generate-migration test lint format typecheck lock

migrate:
	docker compose exec backend poetry run alembic upgrade head

generate-migration:
	docker compose exec backend poetry run alembic revision --autogenerate -m "$(message)"

test:
	docker compose exec backend poetry run pytest

lint:
	docker compose exec backend poetry run flake8 app tests

format:
	docker compose exec backend poetry run black app tests
	docker compose exec backend poetry run isort app tests

typecheck:
	docker compose exec backend poetry run mypy app

lock:
	docker compose exec backend poetry run poetry lock
