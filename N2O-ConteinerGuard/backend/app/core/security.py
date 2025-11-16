from fastapi import HTTPException, Request, status

from backend.app.core.config import get_settings


class SecurityDependency:
    """FastAPI dependency enforcing simple token-based authentication."""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def __call__(self, request: Request) -> None:
        auth_mode = self.settings.auth_mode.lower()
        if auth_mode == "none":
            return None
        if auth_mode != "token":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unsupported auth mode",
            )

        expected_token = self.settings.guard_token
        if not expected_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Guard token not configured",
            )

        provided_token = request.headers.get("X-Auth-Token")
        if provided_token != expected_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )
