from __future__ import annotations

from typing import Any

import httpx

from backend.app.core.config import Settings, get_settings
from backend.app.domain.models import JiraIssue


class JiraClient:
    def __init__(
        self,
        base_url: str,
        user: str,
        api_token: str,
        project_key: str,
        browse_url: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.browse_url = (browse_url or self.base_url).rstrip("/")
        self.user = user
        self.api_token = api_token
        self.project_key = project_key
        self._client = client or httpx.AsyncClient(
            base_url=self.base_url, auth=(self.user, self.api_token)
        )

    async def create_issue(self, summary: str, description: str) -> JiraIssue:
        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": "Task"},
            }
        }

        response = await self._client.post("/rest/api/3/issue", json=payload)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        key = data.get("key", "SEC-0")
        return JiraIssue(key=key, url=f"{self.browse_url}/browse/{key}")

    async def close(self) -> None:
        await self._client.aclose()

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "JiraClient":
        settings = settings or get_settings()
        browse_url = settings.jira_browse_url
        if not browse_url:
            raise ValueError("Jira browse URL must be configured")
        if not all(
            [
                settings.jira_url,
                settings.jira_user,
                settings.jira_api_token,
                settings.jira_project_key,
            ]
        ):
            # Return a dummy client that mimics Jira responses without network calls.
            return DummyJiraClient(browse_url=browse_url)
        return cls(
            base_url=settings.jira_url,
            user=settings.jira_user,
            api_token=settings.jira_api_token,
            project_key=settings.jira_project_key,
            browse_url=browse_url,
        )


class DummyJiraClient(JiraClient):
    def __init__(
        self, browse_url: str | None = None
    ) -> None:  # type: ignore[super-init-not-called]
        self.browse_url = (browse_url or "https://jira.example.com").rstrip("/")
        self.base_url = self.browse_url
        self.project_key = "SEC"

    async def create_issue(
        self, summary: str, description: str
    ) -> JiraIssue:  # noqa: ARG002
        return JiraIssue(key="SEC-000", url=f"{self.browse_url}/browse/SEC-000")

    async def close(self) -> None:
        return None
