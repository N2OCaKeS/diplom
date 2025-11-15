from app.api.routers.health import router as health_router
from app.core.config import get_settings
from app.core.security import ensure_authorized
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

settings = get_settings()

API_PREFIX = "/api"
PUBLIC_API_PATHS = {f"{API_PREFIX}/health", f"{API_PREFIX}/version"}

app = FastAPI(title="N2O Container Guard API", version="0.1.0")

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
        expose_headers=["*"],
    )

app.include_router(health_router, prefix=API_PREFIX)


@app.middleware("http")
async def authorization_middleware(request: Request, call_next):
    """Reject requests that are not authorized via the configured strategy."""

    if settings.auth_mode == "disabled":
        return await call_next(request)

    path = request.url.path.rstrip("/") or "/"
    if not path.startswith(API_PREFIX):
        return await call_next(request)
    if path in PUBLIC_API_PATHS:
        return await call_next(request)

    auth_context = await ensure_authorized(
        request.headers.get("Authorization"), settings=settings
    )
    request.state.auth_context = auth_context
    return await call_next(request)


# �ؑ'�?�+�< �?�� �����?���'�?, ��?�>�� ����'���>�?�?�� ��%�' �?��', �>��+�? �?�?���?���� ��������� �? �?����?
app.mount("/out", StaticFiles(directory="app/static/out", check_dir=False), name="out")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.app_port, reload=False)
