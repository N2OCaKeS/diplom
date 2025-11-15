from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.domain.models import JiraIssue


class JiraClient:
    def __init__(
        self,
        base_url: str,
        user: str,
        api_token: str,
        project_key: str,
        browse_url: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.user = user
        self.api_token = api_token
        self.project_key = project_key
        self.browse_url = (browse_url or self.base_url).rstrip("/")
        self._client = client or httpx.Client(
            base_url=self.base_url,
            auth=(self.user, self.api_token),
        )
        self._owns_client = client is None

    def create_issue(self, summary: str, description: str) -> JiraIssue:
        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": "Task"},
            }
        }

        response = self._client.post("/rest/api/3/issue", json=payload)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        key = data.get("key", "SEC-0")
        return JiraIssue(key=key, url=f"{self.browse_url}/browse/{key}")

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "JiraClient":
        settings = settings or get_settings()
        browse_url = (settings.jira_browse_url or settings.jira_url)
        if not browse_url:
            raise RuntimeError("Jira browse URL must be configured")
        if not all([settings.jira_url, settings.jira_user, settings.jira_api_token, settings.jira_project_key]):
            return DummyJiraClient(browse_url=browse_url)
        return cls(
            base_url=settings.jira_url,
            user=settings.jira_user,
            api_token=settings.jira_api_token,
            project_key=settings.jira_project_key,
            browse_url=browse_url,
        )


class DummyJiraClient(JiraClient):
    def __init__(self, browse_url: str) -> None:  # type: ignore[super-init-not-called]
        self.browse_url = browse_url.rstrip("/")
        self.project_key = "SEC"

    def create_issue(self, summary: str, description: str) -> JiraIssue:  # noqa: ARG002
        return JiraIssue(key="SEC-000", url=f"{self.browse_url}/browse/SEC-000")

    def close(self) -> None:
        return None
