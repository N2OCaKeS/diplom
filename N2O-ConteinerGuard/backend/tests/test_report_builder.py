from __future__ import annotations

from backend.app.domain.models import (
    AnalysisResult,
    Decision,
    EvaluationRequest,
    Status,
    Vulnerability,
)
from backend.app.domain.report_builder import (
    build_confluence_report,
    build_jira_description,
)


def _make_request() -> EvaluationRequest:
    return EvaluationRequest(
        image="registry.example.com/project/app:tag",
        commit="abcdef",
        project="sample",
        pipeline_id="99",
        report={},
    )


def _make_analysis() -> AnalysisResult:
    return AnalysisResult(
        decision=Decision.ALLOW,
        status=Status.MEDIUM,
        message="Vulnerabilities require attention",
        vulnerabilities=[
            Vulnerability(
                id="CVE-1",
                severity="HIGH",
                package="openssl",
                fixed_version=None,
                url="https://cve.example.com/CVE-1",
                recommendation="Update",
            ),
            Vulnerability(
                id="CVE-2",
                severity="LOW",
                package="glibc",
                fixed_version="1.2",
                recommendation=None,
            ),
        ],
    )


def test_jira_description_lists_summary_and_link() -> None:
    description = build_jira_description(
        _make_request(), _make_analysis(), "https://confluence.test/pages/SEC-1"
    )

    assert "*Vulnerability summary:*" in description
    assert "- HIGH: 1" in description
    assert "- LOW: 1" in description
    assert "Detailed report in Confluence" in description


def test_confluence_report_contains_table() -> None:
    report = build_confluence_report(_make_request(), _make_analysis())

    assert "<table>" in report
    assert "<th>ID</th>" in report
    assert "CVE-1" in report
    assert "Advisory" in report


def test_confluence_report_without_vulnerabilities() -> None:
    empty_analysis = AnalysisResult(
        decision=Decision.ALLOW,
        status=Status.PASS,
        message="No vulnerabilities detected",
        vulnerabilities=[],
    )

    report = build_confluence_report(_make_request(), empty_analysis)
    assert "No vulnerabilities detected" in report
