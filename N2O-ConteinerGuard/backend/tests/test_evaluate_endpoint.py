from __future__ import annotations

import jwt
import pytest
from sqlalchemy import select

from app.db.models import ReportORM


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


def test_evaluate_allows_deployment(monkeypatch: pytest.MonkeyPatch, client, session) -> None:
    monkeypatch.setenv("AUTH_MODE", "jwt_static")
    monkeypatch.setenv("JWT_SECRET", "secret")
    token = jwt.encode({"sub": "ci"}, "secret", algorithm="HS256")

    response = client.post(
        "/api/v1/evaluate",
        json=build_payload("LOW"),
        headers={"Authorization": f"Bearer {token}"},
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


def test_evaluate_denies_on_blocking(monkeypatch: pytest.MonkeyPatch, client, session) -> None:
    monkeypatch.setenv("AUTH_MODE", "jwt_static")
    monkeypatch.setenv("JWT_SECRET", "secret")
    token = jwt.encode({"sub": "ci"}, "secret", algorithm="HS256")

    response = client.post(
        "/api/v1/evaluate",
        json=build_payload("CRITICAL", fixed_version=None),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "deny"
    assert data["status"] == "high"
    assert data["message"] == "Blocking vulnerabilities without fixes detected"


def test_evaluate_requires_jira_configuration(monkeypatch: pytest.MonkeyPatch, client) -> None:
    monkeypatch.delenv("JIRA_BROWSE_URL", raising=False)
    monkeypatch.setenv("AUTH_MODE", "jwt_static")
    monkeypatch.setenv("JWT_SECRET", "secret")
    token = jwt.encode({"sub": "ci"}, "secret", algorithm="HS256")

    response = client.post(
        "/api/v1/evaluate",
        json=build_payload("LOW"),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Jira browse URL must be configured"
