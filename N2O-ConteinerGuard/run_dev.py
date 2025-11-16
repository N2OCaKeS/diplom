from alembic import command
from alembic.config import Config
from pathlib import Path
from backend.app.core.config import get_settings
import uvicorn

BASE_DIR = Path(__file__).resolve().parent
ALEMBIC_INI = BASE_DIR / "backend" / "alembic.ini"


def run_migrations():
    settings = get_settings()
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(BASE_DIR / "backend" / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(cfg, "head")


if __name__ == "__main__":
    run_migrations()
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8001, reload=True)


# docker run --name my-postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=guard -p 5432:5432 -d postgres:16
