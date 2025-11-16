from __future__ import annotations

import pytest

from backend.app.core.config import get_settings
from backend.app.integrations.jira_client import DummyJiraClient, JiraClient


def test_settings_load_policies_from_custom_file(tmp_path, monkeypatch) -> None:
    policies_file = tmp_path / "policies.yml"
    policies_file.write_text(
        "default:\n"
        "  block_on_severity: CRITICAL\n"
        "  warn_on_severity: MEDIUM\n"
        "projects:\n"
        "  payments:\n"
        "    block_on_severity: HIGH\n"
        "    treat_unknown_as: HIGH\n"
    )
    monkeypatch.setenv("POLICIES_PATH", str(policies_file))
    get_settings.cache_clear()

    settings = get_settings()
    project_policy = settings.policies.for_project("payments")

    assert project_policy.block_on_severity == "HIGH"
    assert project_policy.treat_unknown_as == "HIGH"


def test_jira_client_from_settings_returns_dummy(monkeypatch) -> None:
    monkeypatch.setenv("JIRA_URL", "https://jira.test")
    monkeypatch.setenv("JIRA_USER", "")
    monkeypatch.setenv("JIRA_API_TOKEN", "")
    monkeypatch.setenv("JIRA_PROJECT_KEY", "")
    get_settings.cache_clear()

    client = JiraClient.from_settings()

    assert isinstance(client, DummyJiraClient)


@pytest.mark.asyncio
async def test_jira_client_from_settings_builds_real_client(monkeypatch) -> None:
    monkeypatch.setenv("JIRA_URL", "https://jira.api")
    monkeypatch.setenv("JIRA_USER", "api-user")
    monkeypatch.setenv("JIRA_API_TOKEN", "token")
    monkeypatch.setenv("JIRA_PROJECT_KEY", "SEC")
    get_settings.cache_clear()

    client = JiraClient.from_settings()

    try:
        assert isinstance(client, JiraClient)
        assert client.project_key == "SEC"
        assert client.base_url == "https://jira.api"
    finally:
        await client.close()


def test_jira_client_from_settings_requires_jira_url(monkeypatch) -> None:
    monkeypatch.setenv("JIRA_URL", "")
    get_settings.cache_clear()

    with pytest.raises(ValueError):
        JiraClient.from_settings()
