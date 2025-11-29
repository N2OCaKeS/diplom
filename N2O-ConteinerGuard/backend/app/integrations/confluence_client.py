from __future__ import annotations

from typing import Any

import httpx

from backend.app.core.config import Settings, get_settings
from backend.app.domain.models import ConfluencePage


class ConfluenceClient:
    def __init__(
        self,
        base_url: str,
        user: str,
        api_token: str,
        space_key: str,
        parent_page_id: str | None = None,
        browse_url: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.browse_url = (browse_url or self.base_url).rstrip("/")
        self.user = user
        self.api_token = api_token
        self.space_key = space_key
        self.parent_page_id = parent_page_id
        self._client = client or httpx.AsyncClient(
            base_url=self.base_url, auth=(self.user, self.api_token)
        )

    async def create_page(self, title: str, body: str) -> ConfluencePage:
        payload = {
            "type": "page",
            "title": title,
            "space": {"key": self.space_key},
            "body": {
                "storage": {
                    "value": body,
                    "representation": "storage",
                }
            },
        }
        if self.parent_page_id:
            payload["ancestors"] = [{"id": self.parent_page_id}]

        response = await self._client.post("/rest/api/content", json=payload)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        page_id = data.get("id", "0")
        return ConfluencePage(id=page_id, url=self._extract_page_url(data, page_id))

    async def close(self) -> None:
        await self._client.aclose()

    def _extract_page_url(self, payload: dict[str, Any], page_id: str) -> str:
        links = payload.get("_links") or {}
        base_link = links.get("base") or self.browse_url
        webui = links.get("webui")
        if base_link and webui:
            return f"{base_link.rstrip('/')}/{webui.lstrip('/')}"
        return f"{self.browse_url.rstrip('/')}/pages/{page_id}"

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "ConfluenceClient":
        settings = settings or get_settings()
        base_url = settings.confluence_url
        if not base_url:
            raise ValueError("Confluence URL must be configured")
        if not all(
            [
                settings.confluence_user,
                settings.confluence_api_token,
                settings.confluence_space_key,
            ]
        ):
            return DummyConfluenceClient(base_url=base_url)
        return cls(
            base_url=base_url,
            user=settings.confluence_user,
            api_token=settings.confluence_api_token,
            space_key=settings.confluence_space_key,
            parent_page_id=settings.confluence_parent_page_id,
            browse_url=base_url,
        )


class DummyConfluenceClient(ConfluenceClient):
    def __init__(self, base_url: str) -> None:  # type: ignore[super-init-not-called]
        self.base_url = base_url.rstrip("/")
        self.browse_url = self.base_url
        self.space_key = "SEC"

    async def create_page(
        self, title: str, body: str
    ) -> ConfluencePage:  # noqa: ARG002
        return ConfluencePage(
            id="0",
            url=f"{self.browse_url.rstrip('/')}/pages/SEC-REPORT",
        )

    async def close(self) -> None:
        return None
