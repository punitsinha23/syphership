.PHONY: up down api install test logs

up:
	docker compose up -d

down:
	docker compose down

api:
	cd services/api && .venv/bin/python -m uvicorn main:app --reload --port 8000

install:
	cd services/api && .venv/bin/pip install -r requirements.txt

test:
	cd services/api && .venv/bin/python -m pytest

logs:
	docker compose logs -f