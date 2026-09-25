# Developer shortcuts. The README lists the raw commands too.
BACKEND := backend
PY := $(BACKEND)/.venv/bin

.PHONY: help install seed api web dev test test-pg lint check clean

help:
	@echo "make install   create the venv, install backend + frontend dependencies"
	@echo "make seed      (re)create the SQLite demo database with ~100 days of history"
	@echo "make api       FastAPI on :8000 (scheduler runs in-process)"
	@echo "make web       Next.js on :3000"
	@echo "make dev       api + web together"
	@echo "make test      backend test suite on SQLite"
	@echo "make test-pg   the same suite on PostgreSQL (TEST_DATABASE_URL=postgresql+asyncpg://...)"
	@echo "make check     lint, format check, typecheck, tests, production build"

install:
	python3 -m venv $(BACKEND)/.venv
	$(PY)/pip install -r $(BACKEND)/requirements-dev.txt
	cd frontend && npm ci

seed:
	cd $(BACKEND) && .venv/bin/python -m app.seed

api:
	cd $(BACKEND) && .venv/bin/uvicorn app.main:app --reload --port 8000

web:
	cd frontend && npm run dev

dev:
	$(MAKE) -j2 api web

test:
	cd $(BACKEND) && .venv/bin/python -m pytest

test-pg:
	cd $(BACKEND) && TEST_DATABASE_URL=$${TEST_DATABASE_URL:?set TEST_DATABASE_URL} .venv/bin/python -m pytest

lint:
	cd $(BACKEND) && .venv/bin/ruff check . && .venv/bin/ruff format --check .
	cd frontend && npm run lint && npm run typecheck

check: lint test
	cd frontend && npm run build

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -f $(BACKEND)/*.db $(BACKEND)/*.db-wal $(BACKEND)/*.db-shm
