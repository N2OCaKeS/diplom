from __future__ import annotations

from collections import Counter, defaultdict
from html import escape
from typing import Iterable

from backend.app.domain.models import AnalysisResult, EvaluationRequest, Vulnerability

SEVERITY_ORDER = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
    "UNKNOWN": 4,
}


def build_jira_description(
    request: EvaluationRequest,
    analysis: AnalysisResult,
    report_url: str,
) -> str:
    header = [
        f"*Image:* `{request.image}`",
        f"*Project:* `{request.project}`",
        f"*Pipeline ID:* `{request.pipeline_id}`",
        f"*Commit:* `{request.commit}`",
        f"*Decision:* {analysis.decision.value}",
        f"*Status:* {analysis.status.value}",
        f"*Message:* {analysis.message}",
        "",
    ]

    if not analysis.vulnerabilities:
        header.append("No vulnerabilities detected in the latest scan.")
        header.append(f"[Detailed report in Confluence|{report_url}]")
        return "\n".join(header)

    header.append("*Vulnerability summary:*")
    counts = _count_by_severity(analysis.vulnerabilities)
    for severity in SEVERITY_ORDER:
        header.append(f"- {severity}: {counts.get(severity, 0)}")
    additional = sorted(
        severity for severity in counts if severity not in SEVERITY_ORDER
    )
    for severity in additional:
        header.append(f"- {severity}: {counts.get(severity, 0)}")
    header.append("")
    header.append(f"[Detailed report in Confluence|{report_url}]")
    return "\n".join(header)


def build_confluence_report(
    request: EvaluationRequest, analysis: AnalysisResult
) -> str:
    sections: list[str] = [
        "<p><strong>Container image:</strong> "
        f"{escape(request.image)}<br/>"
        f"<strong>Project:</strong> {escape(request.project)}<br/>"
        f"<strong>Pipeline ID:</strong> {escape(request.pipeline_id)}<br/>"
        f"<strong>Commit:</strong> {escape(request.commit)}<br/>"
        f"<strong>Decision:</strong> {escape(analysis.decision.value)}<br/>"
        f"<strong>Status:</strong> {escape(analysis.status.value)}<br/>"
        f"<strong>Message:</strong> {escape(analysis.message)}</p>"
    ]

    if not analysis.vulnerabilities:
        sections.append("<p>No vulnerabilities detected in this analysis.</p>")
        return "\n".join(sections)

    grouped = _group_by_severity(analysis.vulnerabilities)
    for severity, vulnerabilities in grouped.items():
        sections.append(f"<h3>{escape(severity)} ({len(vulnerabilities)})</h3>")
        sections.append(_render_severity_table(vulnerabilities))
    return "\n".join(sections)


def _render_severity_table(vulnerabilities: Iterable[Vulnerability]) -> str:
    rows = [
        "<table>",
        "<thead>",
        "<tr>"
        "<th>ID</th>"
        "<th>Package</th>"
        "<th>Fixed Version</th>"
        "<th>Link</th>"
        "<th>Recommendation</th>"
        "</tr>",
        "</thead>",
        "<tbody>",
    ]
    for vulnerability in vulnerabilities:
        rows.append(
            "<tr>"
            f"<td>{escape(vulnerability.id or '-')}</td>"
            f"<td>{escape(vulnerability.package or '-')}</td>"
            f"<td>{escape(vulnerability.fixed_version or 'Not provided')}</td>"
            f"<td>{_render_link(vulnerability.url)}</td>"
            f"<td>{_format_recommendation(vulnerability)}</td>"
            "</tr>"
        )
    rows.extend(["</tbody>", "</table>"])
    return "\n".join(rows)


def _render_link(url: str | None) -> str:
    if not url:
        return "-"
    safe_url = escape(url, quote=True)
    return f'<a href="{safe_url}">Advisory</a>'


def _count_by_severity(vulnerabilities: Iterable[Vulnerability]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for vulnerability in vulnerabilities:
        counts[vulnerability.severity] += 1
    return counts


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


def _format_recommendation(vulnerability: Vulnerability) -> str:
    recommendation = vulnerability.recommendation or (
        "Review the vendor advisory and apply the recommended remediation steps."
    )
    if vulnerability.fixed_version:
        recommendation = f"{recommendation} Update to {escape(vulnerability.fixed_version)} when possible."
    safe_recommendation = escape(recommendation)
    return safe_recommendation.replace("\n", "<br/>")
