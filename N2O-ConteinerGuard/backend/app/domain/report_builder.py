from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from backend.app.domain.models import AnalysisResult, EvaluationRequest, Vulnerability

SEVERITY_ORDER = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
    "UNKNOWN": 4,
}


def build_jira_description(request: EvaluationRequest, analysis: AnalysisResult) -> str:
    header = (
        f"*Image:* `{request.image}`\n"
        f"*Project:* `{request.project}`\n"
        f"*Pipeline ID:* `{request.pipeline_id}`\n"
        f"*Commit:* `{request.commit}`\n"
        f"*Decision:* {analysis.decision.value}\n"
        f"*Status:* {analysis.status.value}\n"
        f"*Message:* {analysis.message}\n\n"
    )

    if not analysis.vulnerabilities:
        return header + "No vulnerabilities were reported by the scanner."

    grouped = _group_by_severity(analysis.vulnerabilities)
    sections = [header]
    for severity, vulns in grouped.items():
        sections.append(f"h3. {severity} ({len(vulns)})")
        sections.append("|| ID || Package || Fixed Version || Recommendation ||")
        for vuln in vulns:
            recommendation = vuln.recommendation or "See scanner details"
            sections.append(
                f"| {vuln.id} | {vuln.package or '-'} | {vuln.fixed_version or '-'} | {recommendation} |"
            )
        sections.append("")
    return "\n".join(sections)


def _group_by_severity(
    vulnerabilities: Iterable[Vulnerability],
) -> dict[str, list[Vulnerability]]:
    grouped: dict[str, list[Vulnerability]] = defaultdict(list)
    for vulnerability in vulnerabilities:
        grouped[vulnerability.severity].append(vulnerability)
    return dict(
        sorted(
            grouped.items(),
            key=lambda item: SEVERITY_ORDER.get(item[0], len(SEVERITY_ORDER)),
        )
    )
