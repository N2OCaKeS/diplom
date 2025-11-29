from __future__ import annotations

import json

import httpx
import pytest

from backend.app.integrations.confluence_client import (
    ConfluenceClient,
    DummyConfluenceClient,
)


@pytest.mark.asyncio
async def test_confluence_client_creates_page() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/wiki/rest/api/content"
        payload = json.loads(request.content.decode())
        assert payload["title"] == "Vulnerability report"
        assert payload["space"]["key"] == "SEC"
        assert payload["body"]["storage"]["representation"] == "storage"
        assert payload["ancestors"][0]["id"] == "123"
        return httpx.Response(
            status_code=200,
            json={
                "id": "321",
                "_links": {
                    "base": "https://confluence.example.com/wiki",
                    "webui": "/spaces/SEC/pages/321/Vulnerability+report",
                },
            },
            request=request,
        )

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(
        transport=transport, base_url="https://confluence.example.com/wiki"
    )
    client = ConfluenceClient(
        base_url="https://confluence.example.com/wiki",
        user="user",
        api_token="token",
        space_key="SEC",
        parent_page_id="123",
        client=http_client,
    )

    page = await client.create_page("Vulnerability report", "<p>Body</p>")
    assert page.id == "321"
    assert (
        page.url
        == "https://confluence.example.com/wiki/spaces/SEC/pages/321/Vulnerability+report"
    )
    await client.close()


@pytest.mark.asyncio
async def test_dummy_confluence_client_returns_stubbed_page() -> None:
    client = DummyConfluenceClient(base_url="https://confluence.example.com/wiki")
    page = await client.create_page("Any", "<p>Body</p>")
    assert page.url == "https://confluence.example.com/wiki/pages/SEC-REPORT"
