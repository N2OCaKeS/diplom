from __future__ import annotations

import asyncio
import httpx
import jwt
import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core.security import get_security_dependency


def make_request(token: str | None = None) -> Request:
    headers = []
    if token is not None:
        headers.append((b"authorization", f"Bearer {token}".encode()))
    scope = {
        "type": "http",
        "headers": headers,
    }
    return Request(scope)


def test_security_allows_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "none")
    dependency = get_security_dependency()

    asyncio.run(dependency(make_request()))


def test_security_validates_static_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "jwt_static")
    monkeypatch.setenv("JWT_SECRET", "secret")
    token = jwt.encode({"sub": "ci"}, "secret", algorithm="HS256")

    dependency = get_security_dependency()

    asyncio.run(dependency(make_request(token)))


def test_security_rejects_invalid_static_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "jwt_static")
    monkeypatch.setenv("JWT_SECRET", "secret")
    dependency = get_security_dependency()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(dependency(make_request("invalid")))

    assert exc_info.value.status_code == 401


def test_security_requires_bearer_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "jwt_static")
    monkeypatch.setenv("JWT_SECRET", "secret")
    dependency = get_security_dependency()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(dependency(make_request(None)))

    assert exc_info.value.status_code == 401


class DummyAuthClient:
    def __init__(self, response_status: int) -> None:
        self.response_status = response_status

    def post(self, url: str, headers: dict[str, str]) -> httpx.Response:  # noqa: ARG002
        return httpx.Response(status_code=self.response_status, request=httpx.Request("POST", url))

    def close(self) -> None:
        return None


def test_security_validates_external_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "jwt_external")
    monkeypatch.setenv("AUTH_VALIDATION_URL", "https://auth/validate")
    dependency = get_security_dependency(http_client_factory=lambda: DummyAuthClient(response_status=200))

    asyncio.run(dependency(make_request("token")))


def test_security_external_rejects_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "jwt_external")
    monkeypatch.setenv("AUTH_VALIDATION_URL", "https://auth/validate")
    dependency = get_security_dependency(http_client_factory=lambda: DummyAuthClient(response_status=401))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(dependency(make_request("token")))

    assert exc_info.value.status_code == 401


def test_security_external_handles_service_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "jwt_external")
    monkeypatch.setenv("AUTH_VALIDATION_URL", "https://auth/validate")
    dependency = get_security_dependency(http_client_factory=lambda: DummyAuthClient(response_status=500))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(dependency(make_request("token")))

    assert exc_info.value.status_code == 502
