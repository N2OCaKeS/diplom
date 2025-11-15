# -------- stage: builder --------
FROM python:3.12-slim AS builder

ENV POETRY_VERSION=1.8.3 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_HOME=/opt/poetry \
    POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update && apt-get install -y --no-install-recommends curl build-essential \
    && curl -sSL https://install.python-poetry.org | python - --version $POETRY_VERSION \
    && ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry

WORKDIR /app
COPY pyproject.toml ./
# Если используешь lock — добавь: COPY poetry.lock ./
RUN poetry install --only main --no-interaction --no-ansi

# -------- stage: runtime --------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Копируем установленные зависимости из builder слоя
COPY --from=builder /usr/local /usr/local

# Копируем исходники
COPY app ./app

EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
