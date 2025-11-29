from __future__ import annotations

from pathlib import Path

from backend.app.core.config import get_settings


def test_get_policies_returns_current_state(client) -> None:
    response = client.get("/api/v1/policies")

    assert response.status_code == 200
    data = response.json()
    assert data["policies"]["default"]["warn_on_severity"] == "HIGH"
    sources = {Path(path).name for path in data["sources"]}
    assert "base.yml" in sources
    assert "example-service.yml" in sources


def test_reload_policies_endpoint_returns_sources(client) -> None:
    response = client.post("/api/v1/policies/reload")

    assert response.status_code == 200
    data = response.json()
    assert data["detail"] == "Policies reloaded"
    sources = {Path(path).name for path in data["sources"]}
    assert "base.yml" in sources
    assert "example-service.yml" in sources


def test_update_policies_with_template_overrides_config(client) -> None:
    response = client.post("/api/v1/policies/update", json={"template": "relaxed"})

    assert response.status_code == 200
    data = response.json()
    assert "relaxed.yml" in {Path(path).name for path in data["sources"]}
    assert data["policies"]["default"]["warn_on_severity"] == "LOW"

    settings = get_settings()
    assert settings.policies.default.warn_on_severity == "LOW"
    assert settings.policies.default.allow_unfixed is True


def test_update_policies_with_payload(client) -> None:
    response = client.post(
        "/api/v1/policies/update",
        json={"policy": {"default": {"block_on_severity": "LOW"}}},
    )

    assert response.status_code == 200
    settings = get_settings()
    assert settings.policies.default.block_on_severity == "LOW"
    assert settings.policy_sources == ("request",)


def test_update_policies_requires_payload(client) -> None:
    response = client.post("/api/v1/policies/update", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "Either 'template' or 'policy' must be provided"


def test_upload_policy_file_updates_storage(tmp_path, monkeypatch, client) -> None:
    storage = tmp_path / "policies"
    monkeypatch.setenv("POLICIES_STORAGE_PATH", str(storage))
    get_settings.cache_clear()

    content = (
        "default:\n"
        "  block_on_severity: LOW\n"
        "  warn_on_severity: LOW\n"
        "projects:\n"
        "  api:\n"
        "    warn_on_severity: LOW\n"
    )

    response = client.post(
        "/api/v1/policies/upload",
        files={"policy_file": ("custom.yml", content, "text/yaml")},
    )

    assert response.status_code == 200
    data = response.json()
    assert Path(data["sources"][0]).name == "custom.yml"
    assert data["policies"]["default"]["block_on_severity"] == "LOW"
    assert (storage / "custom.yml").exists()

    settings = get_settings()
    assert settings.policies.for_project("api").warn_on_severity == "LOW"
