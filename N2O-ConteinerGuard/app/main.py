from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.routers.health import router as health_router

app = FastAPI(title="N2O Container Guard API", version="0.1.0")

# роуты
app.include_router(health_router, prefix="/api")

# раздача статических отчётов (понадобится позже)
app.mount("/out", StaticFiles(directory="app/static/out"), name="out")
