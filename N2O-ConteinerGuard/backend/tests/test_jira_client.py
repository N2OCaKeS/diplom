from __future__ import annotations

import httpx
import pytest

from backend.app.integrations.jira_client import DummyJiraClient, JiraClient


@pytest.mark.asyncio
async def test_jira_client_creates_issue() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/rest/api/3/issue"
        return httpx.Response(201, json={"key": "SEC-123"}, request=request)

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url="https://jira.example.com")
    client = JiraClient(
        base_url="https://jira.example.com",
        user="user",
        api_token="token",
        project_key="SEC",
        browse_url="https://jira.example.com",
        client=http_client,
    )
    issue = client.create_issue("summary", "description")
    assert issue.key == "SEC-123"
    assert issue.url == "https://jira.example.com/browse/SEC-123"
    client.close()


def test_dummy_jira_client_uses_configured_browse_url() -> None:
    client = DummyJiraClient(browse_url="https://jira.example.com")
    issue = client.create_issue("summary", "description")
    assert issue.url == "https://jira.example.com/browse/SEC-000"
