from __future__ import annotations

from typing import Any, Iterable

from app.core.config import PolicyConfig, PolicySettings
from app.domain.models import AnalysisResult, Decision, Status, Vulnerability

SEVERITY_RANKING = {
    "UNKNOWN": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}


class Analyzer:
    """Apply configured policies to a Trivy report and produce risk decisions."""

    def __init__(self, policies: PolicyConfig) -> None:
        self._policies = policies

    def evaluate(self, project: str, report: dict[str, Any]) -> AnalysisResult:
        policy = self._policies.for_project(project)
        vulnerabilities = list(self._extract_vulnerabilities(report))
        status, decision, message = self._compute_outcome(vulnerabilities, policy)
        return AnalysisResult(
            decision=decision,
            status=status,
            message=message,
            vulnerabilities=vulnerabilities,
        )

    def _extract_vulnerabilities(self, report: dict[str, Any]) -> Iterable[Vulnerability]:
        results = report.get("Results", [])
        for result in results:
            for vulnerability in result.get("Vulnerabilities", []) or []:
                yield Vulnerability(
                    id=vulnerability.get("VulnerabilityID") or vulnerability.get("ID", "unknown"),
                    severity=(vulnerability.get("Severity") or "UNKNOWN").upper(),
                    title=vulnerability.get("Title"),
                    description=vulnerability.get("Description"),
                    recommendation=vulnerability.get("PrimaryURL") or vulnerability.get("Recommendation"),
                    url=vulnerability.get("PrimaryURL"),
                    fixed_version=vulnerability.get("FixedVersion"),
                    package=vulnerability.get("PkgName"),
                )

    def _compute_outcome(
        self,
        vulnerabilities: list[Vulnerability],
        policy: PolicySettings,
    ) -> tuple[Status, Decision, str]:
        if not vulnerabilities:
            return Status.PASS, Decision.ALLOW, "No vulnerabilities detected"

        highest_severity = self._determine_highest_severity(vulnerabilities, policy)

        if self._severity_meets_threshold(highest_severity, policy.block_on_severity):
            return Status.HIGH, Decision.DENY, "Blocking vulnerability threshold reached"

        if self._severity_meets_threshold(highest_severity, policy.warn_on_severity):
            return Status.MEDIUM, Decision.ALLOW, "Vulnerabilities require attention"

        return Status.WARN, Decision.ALLOW, "Low severity vulnerabilities present"

    def _determine_highest_severity(self, vulnerabilities: list[Vulnerability], policy: PolicySettings) -> str:
        highest = "UNKNOWN"
        for vulnerability in vulnerabilities:
            severity = vulnerability.severity or "UNKNOWN"
            if severity == "UNKNOWN":
                severity = policy.treat_unknown_as.upper()
            if self._severity_rank(severity) > self._severity_rank(highest):
                highest = severity
        return highest

    def _severity_rank(self, severity: str) -> int:
        return SEVERITY_RANKING.get(severity.upper(), SEVERITY_RANKING["UNKNOWN"])

    def _severity_meets_threshold(self, severity: str, threshold: str) -> bool:
        return self._severity_rank(severity) >= self._severity_rank(threshold)
