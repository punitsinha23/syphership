.PHONY: up down api worker workers workers-stop workers-logs install test logs

WORKERS ?= 2

up:
	docker compose up -d

down:
	docker compose down

api:
	cd services/api && .venv/bin/python -m uvicorn main:app --reload --port 8000

# One worker on this machine, logs in the terminal.
worker:
	cd services/api && .venv/bin/python -m worker

# Workers in Docker. Pick how many with: make workers WORKERS=3
workers:
	docker compose --profile workers up -d --build --scale worker=$(WORKERS)

workers-stop:
	docker compose --profile workers stop worker

workers-logs:
	docker compose --profile workers logs -f worker

install:
	cd services/api && .venv/bin/pip install -r requirements.txt

test:
	cd services/api && .venv/bin/python -m pytest

logs:
	docker compose logs -f