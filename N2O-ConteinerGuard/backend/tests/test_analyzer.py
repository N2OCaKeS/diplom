from __future__ import annotations

from backend.app.core.config import PolicyConfig, PolicySettings
from backend.app.domain.analyzer import Analyzer
from backend.app.domain.models import Decision, Status


def make_report(severity: str, fixed_version: str | None = "1.0.1") -> dict:
    return {
        "Results": [
            {
                "Vulnerabilities": [
                    {
                        "VulnerabilityID": "CVE-000",
                        "Severity": severity,
                        "PkgName": "libssl",
                        "FixedVersion": fixed_version,
                    }
                ]
            }
        ]
    }


def test_analyzer_blocks_on_severity() -> None:
    policies = PolicyConfig(default=PolicySettings(block_on_severity="HIGH"))
    analyzer = Analyzer(policies)

    result = analyzer.evaluate("service", make_report("CRITICAL"))

    assert result.status is Status.HIGH
    assert result.decision is Decision.DENY
    assert result.message == "Blocking vulnerability threshold reached"


def test_analyzer_blocks_unfixed_when_policy_disallows() -> None:
    policies = PolicyConfig(
        default=PolicySettings(block_on_severity="HIGH", allow_unfixed=False)
    )
    analyzer = Analyzer(policies)

    result = analyzer.evaluate("service", make_report("HIGH", fixed_version=None))

    assert result.status is Status.HIGH
    assert result.decision is Decision.DENY
    assert result.message == "Blocking vulnerabilities without fixes detected"


def test_analyzer_warns_on_medium() -> None:
    policies = PolicyConfig(
        default=PolicySettings(block_on_severity="CRITICAL", warn_on_severity="MEDIUM")
    )
    analyzer = Analyzer(policies)

    result = analyzer.evaluate("service", make_report("MEDIUM"))

    assert result.status is Status.MEDIUM
    assert result.decision is Decision.ALLOW
    assert result.message == "Vulnerabilities require attention"


def test_analyzer_handles_no_vulnerabilities() -> None:
    policies = PolicyConfig(default=PolicySettings())
    analyzer = Analyzer(policies)

    result = analyzer.evaluate("service", {"Results": []})

    assert result.status is Status.PASS
    assert result.decision is Decision.ALLOW
    assert result.message == "No vulnerabilities detected"
