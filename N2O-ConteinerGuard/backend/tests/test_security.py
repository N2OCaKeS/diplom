from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from backend.app.core.security import SecurityDependency


def test_security_allows_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "none")
    dependency = SecurityDependency()

    asyncio.run(dependency(None))


def test_security_accepts_valid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "token")
    monkeypatch.setenv("GUARD_TOKEN", "secret")
    dependency = SecurityDependency()

    asyncio.run(dependency("secret"))


def test_security_rejects_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "token")
    monkeypatch.setenv("GUARD_TOKEN", "secret")
    dependency = SecurityDependency()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(dependency(None))

    assert exc_info.value.status_code == 401


def test_security_rejects_wrong_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "token")
    monkeypatch.setenv("GUARD_TOKEN", "secret")
    dependency = SecurityDependency()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(dependency("other"))

    assert exc_info.value.status_code == 401


def test_security_requires_configured_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "token")
    monkeypatch.setenv("GUARD_TOKEN", "")
    dependency = SecurityDependency()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(dependency("secret"))

    assert exc_info.value.status_code == 500


def test_security_rejects_unsupported_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "jwt")
    monkeypatch.setenv("GUARD_TOKEN", "secret")
    dependency = SecurityDependency()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(dependency("secret"))

    assert exc_info.value.status_code == 500
