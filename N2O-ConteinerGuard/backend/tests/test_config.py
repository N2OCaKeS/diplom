from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.core.config import get_settings
from backend.app.integrations.confluence_client import (
    ConfluenceClient,
    DummyConfluenceClient,
)
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
    monkeypatch.setenv("POLICIES_STORAGE_PATH", str(tmp_path / "missing"))
    get_settings.cache_clear()

    settings = get_settings()
    project_policy = settings.policies.for_project("payments")

    assert project_policy.block_on_severity == "HIGH"
    assert project_policy.treat_unknown_as == "HIGH"


def test_settings_load_policies_from_storage_directory(tmp_path, monkeypatch) -> None:
    storage = tmp_path / "policies"
    nested = storage / "nested"
    nested.mkdir(parents=True)
    base_file = storage / "base.yml"
    projects_file = nested / "projects.yaml"
    base_file.write_text(
        "default:\n" "  block_on_severity: HIGH\n" "  warn_on_severity: HIGH\n"
    )
    projects_file.write_text("projects:\n" "  api:\n" "    warn_on_severity: LOW\n")

    monkeypatch.setenv("POLICIES_STORAGE_PATH", str(storage))
    monkeypatch.setenv("POLICIES_PATH", str(tmp_path / "policies.yml"))
    get_settings.cache_clear()

    settings = get_settings()
    policy = settings.policies.for_project("api")

    assert policy.warn_on_severity == "LOW"
    assert {Path(source).name for source in settings.policy_sources} == {
        "base.yml",
        "projects.yaml",
    }


def test_settings_reload_policies_updates_sources(tmp_path, monkeypatch) -> None:
    storage = tmp_path / "policies"
    storage.mkdir()
    base_file = storage / "base.yml"
    base_file.write_text(
        "default:\n" "  block_on_severity: CRITICAL\n" "  warn_on_severity: HIGH\n"
    )

    monkeypatch.setenv("POLICIES_STORAGE_PATH", str(storage))
    get_settings.cache_clear()

    settings = get_settings()
    assert settings.policies.default.warn_on_severity == "HIGH"

    base_file.write_text(
        "default:\n" "  block_on_severity: CRITICAL\n" "  warn_on_severity: LOW\n"
    )

    settings.reload_policies()
    assert settings.policies.default.warn_on_severity == "LOW"


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


def test_confluence_client_from_settings_returns_dummy(monkeypatch) -> None:
    monkeypatch.setenv("CONFLUENCE_URL", "https://confluence.test/wiki")
    monkeypatch.setenv("CONFLUENCE_USER", "")
    monkeypatch.setenv("CONFLUENCE_API_TOKEN", "")
    monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "")
    get_settings.cache_clear()

    client = ConfluenceClient.from_settings()
    assert isinstance(client, DummyConfluenceClient)


@pytest.mark.asyncio
async def test_confluence_client_from_settings_builds_real_client(monkeypatch) -> None:
    monkeypatch.setenv("CONFLUENCE_URL", "https://confluence.test/wiki")
    monkeypatch.setenv("CONFLUENCE_USER", "api-user")
    monkeypatch.setenv("CONFLUENCE_API_TOKEN", "token")
    monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "SEC")
    monkeypatch.setenv("CONFLUENCE_PARENT_PAGE_ID", "123")
    get_settings.cache_clear()

    client = ConfluenceClient.from_settings()

    try:
        assert isinstance(client, ConfluenceClient)
        assert client.space_key == "SEC"
        assert client.parent_page_id == "123"
    finally:
        await client.close()


def test_confluence_client_requires_url(monkeypatch) -> None:
    monkeypatch.setenv("CONFLUENCE_URL", "")
    get_settings.cache_clear()

    with pytest.raises(ValueError):
        ConfluenceClient.from_settings()
