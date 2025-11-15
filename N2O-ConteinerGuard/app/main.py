from app.api.routers.health import router as health_router
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="N2O Container Guard API", version="0.1.0")

app.include_router(health_router, prefix="/api")

# чтобы не падать, если каталога ещё нет, либо создай папки в репо
app.mount("/out", StaticFiles(directory="app/static/out", check_dir=False), name="out")
