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
                "description": self._format_description(description),
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

    def _format_description(self, text: str) -> dict[str, Any]:
        """Convert a plain text description into Atlassian Document Format."""
        paragraphs: list[dict[str, Any]] = []
        for paragraph in text.split("\n\n"):
            content: list[dict[str, Any]] = []
            lines = paragraph.split("\n")
            for idx, line in enumerate(lines):
                content.append({"type": "text", "text": line})
                if idx < len(lines) - 1:
                    content.append({"type": "hardBreak"})
            if not content:
                content.append({"type": "text", "text": ""})
            paragraphs.append({"type": "paragraph", "content": content})

        if not paragraphs:
            paragraphs.append(
                {"type": "paragraph", "content": [{"type": "text", "text": ""}]}
            )

        return {"type": "doc", "version": 1, "content": paragraphs}

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "JiraClient":
        settings = settings or get_settings()
        base_url = settings.jira_url
        if not base_url:
            raise ValueError("Jira URL must be configured")
        if not all(
            [
                settings.jira_user,
                settings.jira_api_token,
                settings.jira_project_key,
            ]
        ):
            # Return a dummy client that mimics Jira responses without network calls.
            return DummyJiraClient(browse_url=base_url)
        return cls(
            base_url=base_url,
            user=settings.jira_user,
            api_token=settings.jira_api_token,
            project_key=settings.jira_project_key,
            browse_url=base_url,
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
