from __future__ import annotations

from backend.app.domain.models import (
    AnalysisResult,
    Decision,
    EvaluationRequest,
    Status,
    Vulnerability,
)
from backend.app.domain.report_builder import build_jira_description


def test_report_builder_groups_by_severity() -> None:
    request = EvaluationRequest(
        image="registry.example.com/project/app:tag",
        commit="abcdef",
        project="sample",
        pipeline_id="99",
        report={},
    )
    analysis = AnalysisResult(
        decision=Decision.ALLOW,
        status=Status.MEDIUM,
        message="Vulnerabilities require attention",
        vulnerabilities=[
            Vulnerability(
                id="CVE-1",
                severity="HIGH",
                package="openssl",
                fixed_version=None,
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

    description = build_jira_description(request, analysis)

    assert "h3. HIGH (1)" in description
    assert "h3. LOW (1)" in description
    assert "CVE-2" in description
    assert "Проверьте детали отчета сканера" in description
    assert (
        "|| Идентификатор || Пакет || Рекомендуемая версия || Ссылка || Рекомендации ||"
        in description
    )


def test_report_builder_handles_empty_vulnerabilities() -> None:
    request = EvaluationRequest(
        image="registry.example.com/project/app:tag",
        commit="abcdef",
        project="sample",
        pipeline_id="99",
        report={},
    )
    analysis = AnalysisResult(
        decision=Decision.ALLOW,
        status=Status.PASS,
        message="No vulnerabilities detected",
        vulnerabilities=[],
    )

    description = build_jira_description(request, analysis)

    assert "Сканер не сообщил об уязвимостях" in description
