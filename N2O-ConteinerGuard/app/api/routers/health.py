from fastapi import APIRouter
from datetime import datetime

router = APIRouter(tags=["health"])

@router.get("/health")
def health():
    return {"status": "ok", "ts": datetime.now().isoformat() + "Z"}

@router.get("/version")
def version():
    return {"name": "n2o-container-guard", "version": "0.1.0"}
