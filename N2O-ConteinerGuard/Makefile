# ===== Makefile (Poetry) =====
PY ?= python
APP_MODULE ?= app.main:app
UVICORN_HOST ?= 0.0.0.0
UVICORN_PORT ?= 8001
DOCKER_IMAGE ?= n2o-guard:dev

.PHONY: install dev lint test run docker-build docker-run clean help

install:
	# Инсталлим Poetry локально (если нет) и зависимости проекта
	$(PY) -m pip install --upgrade pip pipx >/dev/null 2>&1 || true
	pipx install poetry >/dev/null 2>&1 || true
	poetry config virtualenvs.in-project true
	poetry install --no-interaction

dev:
	poetry run uvicorn $(APP_MODULE) --host $(UVICORN_HOST) --port $(UVICORN_PORT) --reload

lint:
	poetry run ruff check app tests

test:
	poetry run pytest -q

run:
	poetry run uvicorn $(APP_MODULE) --host $(UVICORN_HOST) --port $(UVICORN_PORT)

docker-build:
	docker build -t $(DOCKER_IMAGE) .

docker-run:
	docker run --rm -p 8001:8001 $(DOCKER_IMAGE)

clean:
	-@rm -rf .venv .pytest_cache .ruff_cache __pycache__ */__pycache__ app/static/out/raw/* app/static/out/normalized/* app/static/out/html/*

help:
	@echo "make install|dev|lint|test|run|docker-build|docker-run|clean"
