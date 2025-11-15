from __future__ import annotations

from fastapi import FastAPI

from app.api.v1.evaluate import router as evaluate_router

app = FastAPI(title="N2O ContainerGuard")

app.include_router(evaluate_router, prefix="/api/v1")


@app.get("/health", tags=["health"])  # type: ignore[misc]
def health_check() -> dict[str, str]:
    """Simple health check endpoint used by container orchestrators."""
    return {"status": "ok"}
