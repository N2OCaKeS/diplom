from __future__ import annotations

import pytest
from sqlalchemy import select

from backend.app.db.models import ReportORM


def build_payload(severity: str, fixed_version: str | None = "1.0.0") -> dict:
    return {
        "image": "registry.example.com/project/app:sha",
        "commit": "abcdef",
        "project": "sample",
        "pipeline_id": "42",
        "report": {
            "Results": [
                {
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-1",
                            "Severity": severity,
                            "PkgName": "openssl",
                            "FixedVersion": fixed_version,
                        }
                    ]
                }
            ]
        },
    }


def auth_headers(token: str = "secret") -> dict[str, str]:
    return {"X-Auth-Token": token}


def test_evaluate_allows_deployment(
    monkeypatch: pytest.MonkeyPatch, client, session
) -> None:
    monkeypatch.setenv("AUTH_MODE", "token")
    monkeypatch.setenv("GUARD_TOKEN", "secret")

    response = client.post(
        "/api/v1/evaluate",
        json=build_payload("LOW"),
        headers=auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "allow"
    assert data["status"] == "warn"
    assert data["jira_issue_key"] == "SEC-000"
    assert data["recommendations_url"].startswith("https://jira.test/browse/")

    result = session.execute(select(ReportORM))
    stored = result.scalar_one()
    assert stored.decision.value == "allow"
    assert stored.image == "registry.example.com/project/app:sha"


def test_evaluate_denies_on_blocking(
    monkeypatch: pytest.MonkeyPatch, client, session
) -> None:
    monkeypatch.setenv("AUTH_MODE", "token")
    monkeypatch.setenv("GUARD_TOKEN", "secret")

    response = client.post(
        "/api/v1/evaluate",
        json=build_payload("CRITICAL", fixed_version=None),
        headers=auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "deny"
    assert data["status"] == "high"
    assert data["message"] == "Blocking vulnerabilities without fixes detected"


def test_evaluate_requires_jira_configuration(
    monkeypatch: pytest.MonkeyPatch, client
) -> None:
    monkeypatch.setenv("JIRA_BROWSE_URL", "")
    monkeypatch.setenv("AUTH_MODE", "token")
    monkeypatch.setenv("GUARD_TOKEN", "secret")

    response = client.post(
        "/api/v1/evaluate",
        json=build_payload("LOW"),
        headers=auth_headers(),
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Jira browse URL must be configured"
