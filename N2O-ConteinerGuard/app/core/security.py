from __future__ import annotations

from typing import Any, Optional

import httpx
import jwt
from fastapi import HTTPException, status
from jwt import ExpiredSignatureError, InvalidTokenError
from loguru import logger

from app.core.config import Settings, get_settings


def _extract_bearer_token(header_value: Optional[str]) -> str:
    """Pull the bearer token from the Authorization header."""
    if not header_value:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header"
        )

    scheme, _, token = header_value.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header"
        )
    return token.strip()


async def ensure_authorized(
    authorization_header: Optional[str],
    settings: Optional[Settings] = None,
) -> dict[str, Any]:
    """
    Validate the provided token via an external service.

    The external service is expected to respond with a JSON object containing at
    least the `valid` and `allowed` flags. Any other payload is ignored but
    returned to the caller for additional context (e.g., claims).
    """

    cfg = settings or get_settings()
    if cfg.auth_mode == "disabled":
        return {}

    token = _extract_bearer_token(authorization_header)

    if cfg.auth_mode == "external":
        return await _verify_with_external_api(token, cfg)
    if cfg.auth_mode == "jwt":
        return _verify_local_jwt(token, cfg)

    raise HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Authorization strategy is misconfigured",
    )


async def _verify_with_external_api(token: str, cfg: Settings) -> dict[str, Any]:
    payload: dict[str, Any] = {"token": token}
    if cfg.auth_service_name:
        payload["service"] = cfg.auth_service_name

    try:
        async with httpx.AsyncClient(timeout=cfg.auth_api_timeout) as client:
            response = await client.post(str(cfg.auth_api_url), json=payload)
    except httpx.TimeoutException as exc:
        logger.warning("Authorization API timeout: {}", exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authorization service unavailable",
        ) from exc
    except httpx.HTTPError as exc:
        logger.exception("Authorization API request failed: {}", exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authorization service error",
        ) from exc

    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )
    if response.status_code == status.HTTP_403_FORBIDDEN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Access forbidden")
    if response.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authorization service unavailable",
        )
    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Token rejected by authorization API"
        )

    try:
        body = response.json()
    except ValueError as exc:
        logger.error("Authorization API returned invalid JSON: {}", exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authorization service error",
        ) from exc

    if body.get("valid") is not True:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")
    if body.get("allowed") is not True:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Access forbidden")

    return body


def _verify_local_jwt(token: str, cfg: Settings) -> dict[str, Any]:
    secret = cfg.jwt_secret
    if not secret:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT secret is not configured",
        )

    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"])
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        ) from exc
    except InvalidTokenError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Invalid access token"
        ) from exc

    return {"valid": True, "allowed": True, "claims": claims}
