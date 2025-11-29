FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential \
    && rm -rf /var/lib/apt/lists/*

# -------- stage: builder --------
FROM base AS builder

ENV POETRY_VERSION=2.2.1 \
    POETRY_HOME=/opt/poetry \
    POETRY_VIRTUALENVS_CREATE=false

RUN curl -sSL https://install.python-poetry.org | python - --version "$POETRY_VERSION" \
    && ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-interaction --no-ansi --without development

# -------- stage: runtime --------
FROM base AS runtime

ENV PYTHONPATH=/app

WORKDIR /app

COPY --from=builder /usr/local /usr/local
COPY backend ./backend
COPY backend/policies.yml ./policies.yml
COPY backend/policies_storage ./policies_storage
COPY guincorn.py ./guincorn.py

EXPOSE 8001
CMD ["gunicorn", "-c", "guincorn.py"]
