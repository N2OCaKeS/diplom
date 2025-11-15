from __future__ import annotations

from collections.abc import Awaitable, Callable

import httpx
import jwt
from fastapi import HTTPException, status
from starlette.requests import Request

from app.core.config import Settings, get_settings


def get_security_dependency(
    settings: Settings | None = None,
    http_client_factory: Callable[[], httpx.Client] | None = None,
) -> Callable[[Request], Awaitable[None]]:
    async def dependency(request: Request) -> None:
        resolved_settings = settings or get_settings()
        auth_mode = resolved_settings.auth_mode.lower()
        if auth_mode == "none":
            return None

        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

        token = auth_header.split(" ", 1)[1]

        if auth_mode == "jwt_static":
            _validate_static_jwt(resolved_settings, token)
            return None

        if auth_mode == "jwt_external":
            _validate_external_jwt(resolved_settings, token, http_client_factory)
            return None

        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unsupported auth mode")

    return dependency


def _validate_static_jwt(settings: Settings, token: str) -> None:
    secret = settings.jwt_secret
    if not secret:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="JWT secret not configured")

    options = {"verify_aud": bool(settings.jwt_audience)}
    try:
        jwt.decode(
            token,
            secret,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options=options,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid JWT token") from exc


def _validate_external_jwt(
    settings: Settings,
    token: str,
    http_client_factory: Callable[[], httpx.Client] | None,
) -> None:
    validation_url = settings.auth_validation_url
    if not validation_url:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Validation endpoint not configured")

    client = http_client_factory() if http_client_factory else httpx.Client()
    try:
        response = client.post(validation_url, headers={"Authorization": f"Bearer {token}"})
        if response.status_code == status.HTTP_401_UNAUTHORIZED:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="JWT token rejected")
        response.raise_for_status()
    except HTTPException:
        raise
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Authorization service error") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Authorization service unreachable") from exc
    finally:
        if http_client_factory is None:
            client.close()
