.PHONY: migrate generate-migration

migrate:
	docker compose exec backend poetry run alembic upgrade head

generate-migration:
	docker compose exec backend poetry run alembic revision --autogenerate -m "$(message)"
