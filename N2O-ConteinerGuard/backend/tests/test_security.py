from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from backend.app.core.security import SecurityDependency


def make_request(token: str | None = None) -> Request:
    headers = []
    if token is not None:
        headers.append((b"x-auth-token", token.encode()))
    scope = {"type": "http", "headers": headers}
    return Request(scope)


def test_security_allows_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "none")
    dependency = SecurityDependency()

    asyncio.run(dependency(make_request()))


def test_security_accepts_valid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "token")
    monkeypatch.setenv("GUARD_TOKEN", "secret")
    dependency = SecurityDependency()

    asyncio.run(dependency(make_request("secret")))


def test_security_rejects_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "token")
    monkeypatch.setenv("GUARD_TOKEN", "secret")
    dependency = SecurityDependency()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(dependency(make_request()))

    assert exc_info.value.status_code == 401


def test_security_rejects_wrong_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "token")
    monkeypatch.setenv("GUARD_TOKEN", "secret")
    dependency = SecurityDependency()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(dependency(make_request("other")))

    assert exc_info.value.status_code == 401


def test_security_requires_configured_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "token")
    monkeypatch.delenv("GUARD_TOKEN", raising=False)
    dependency = SecurityDependency()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(dependency(make_request("secret")))

    assert exc_info.value.status_code == 500


def test_security_rejects_unsupported_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "jwt")
    monkeypatch.setenv("GUARD_TOKEN", "secret")
    dependency = SecurityDependency()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(dependency(make_request("secret")))

    assert exc_info.value.status_code == 500
