from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from backend.app.core.config import get_settings


api_key_header = APIKeyHeader(
    name="X-Auth-Token",
    description="Static token issued by ContainerGuard",
    auto_error=False,
)


class SecurityDependency:
    """FastAPI dependency enforcing simple token-based authentication."""

    async def __call__(self, token: str | None = Depends(api_key_header)) -> None:
        settings = get_settings()
        auth_mode = (settings.auth_mode or "none").lower()
        if auth_mode == "none":
            return None
        if auth_mode != "token":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unsupported auth mode",
            )

        expected_token = settings.guard_token
        if not expected_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Guard token not configured",
            )

        if token != expected_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )


def get_security_dependency() -> SecurityDependency:
    """Compatibility helper for tests and router wiring."""
    return SecurityDependency()
