import pytest
import jwt
from fastapi import HTTPException

from app.core.config import Settings
from app.core.security import ensure_authorized


class DummyResponse:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def stub_async_client(response, captured):
    class _Client:
        def __init__(self, *_, **__):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            captured["url"] = url
            captured["json"] = json
            return response

    return _Client


@pytest.mark.asyncio
async def test_ensure_authorized_success(monkeypatch):
    captured = {}
    response = DummyResponse(
        200, {"valid": True, "allowed": True, "identity": "user-123"}
    )
    monkeypatch.setattr(
        "app.core.security.httpx.AsyncClient", stub_async_client(response, captured)
    )

    settings = Settings(
        auth_api_url="https://auth.local/verify",
        auth_api_timeout=1.0,
        auth_service_name="n2o-guard",
    )

    result = await ensure_authorized("Bearer token-abc", settings=settings)

    assert captured["url"] == "https://auth.local/verify"
    assert captured["json"]["token"] == "token-abc"
    assert captured["json"]["service"] == "n2o-guard"
    assert result["identity"] == "user-123"


@pytest.mark.asyncio
async def test_ensure_authorized_forbidden(monkeypatch):
    response = DummyResponse(200, {"valid": True, "allowed": False})
    monkeypatch.setattr(
        "app.core.security.httpx.AsyncClient", stub_async_client(response, {})
    )

    settings = Settings(auth_api_url="https://auth.local/verify", auth_api_timeout=1.0)

    with pytest.raises(HTTPException) as exc:
        await ensure_authorized("Bearer deny-me", settings=settings)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_ensure_authorized_missing_header():
    settings = Settings(auth_api_url="https://auth.local/verify", auth_api_timeout=1.0)

    with pytest.raises(HTTPException) as exc:
        await ensure_authorized(None, settings=settings)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_ensure_authorized_local_jwt_success():
    settings = Settings(jwt_secret="secret-key")
    token = jwt.encode({"sub": "user-1"}, settings.jwt_secret, algorithm="HS256")

    result = await ensure_authorized(f"Bearer {token}", settings=settings)

    assert result["claims"]["sub"] == "user-1"


@pytest.mark.asyncio
async def test_ensure_authorized_local_jwt_invalid():
    settings = Settings(jwt_secret="secret-key")

    with pytest.raises(HTTPException):
        await ensure_authorized("Bearer invalid.token", settings=settings)
