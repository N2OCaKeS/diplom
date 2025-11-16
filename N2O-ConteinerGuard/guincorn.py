from __future__ import annotations

import multiprocessing
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from loguru import logger

from backend.app.core.config import get_settings

BASE_DIR = Path(__file__).resolve().parent
ALEMBIC_INI = BASE_DIR / "backend" / "alembic.ini"

settings = get_settings()

# --- Gunicorn configuration -------------------------------------------------
wsgi_app = "backend.app.main:app"
worker_class = "uvicorn.workers.UvicornWorker"
workers = int(os.getenv("WEB_CONCURRENCY", (multiprocessing.cpu_count() * 2) + 1))
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
timeout = int(os.getenv("GUNICORN_TIMEOUT", "60"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))
preload_app = True


def _alembic_config() -> Config:
    """Create Alembic configuration bound to the current settings."""
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(BASE_DIR / "backend" / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    return cfg


def run_migrations() -> None:
    """Apply migrations before accepting requests (start & reload)."""
    try:
        logger.info("Applying Alembic migrations...")
        command.upgrade(_alembic_config(), "head")
        logger.info("Alembic migrations applied successfully")
    except Exception:
        logger.exception("Alembic migrations failed")
        raise


def on_starting(server) -> None:  # pragma: no cover - gunicorn hook
    run_migrations()


def on_reload(server) -> None:  # pragma: no cover - gunicorn hook
    run_migrations()
