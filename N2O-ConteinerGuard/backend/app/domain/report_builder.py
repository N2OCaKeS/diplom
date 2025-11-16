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
        f"*Контейнерное изображение:* `{request.image}`\n"
        f"*Проект:* `{request.project}`\n"
        f"*ID пайплайна:* `{request.pipeline_id}`\n"
        f"*Коммит:* `{request.commit}`\n"
        f"*Решение:* {analysis.decision.value}\n"
        f"*Статус:* {analysis.status.value}\n"
        f"*Комментарий:* {analysis.message}\n\n"
    )

    if not analysis.vulnerabilities:
        return header + "Сканер не сообщил об уязвимостях."

    grouped = _group_by_severity(analysis.vulnerabilities)
    sections = [
        header,
        "Ниже приведены уязвимости, обнаруженные Trivy (отсортированы по уровню риска):",
        "",
    ]
    for severity, vulns in grouped.items():
        sections.append(f"h3. {severity} ({len(vulns)})")
        sections.append(
            "|| Идентификатор || Пакет || Рекомендуемая версия || Ссылка || Рекомендации ||"
        )
        for vuln in vulns:
            recommendation = _format_recommendation(vuln)
            link = f"[Подробнее|{vuln.url}]" if vuln.url else "-"
            sections.append(
                "| "
                f"{vuln.id} | "
                f"{vuln.package or '-'} | "
                f"{vuln.fixed_version or 'нет данных'} | "
                f"{link} | "
                f"{recommendation} |"
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


def _format_recommendation(vulnerability: Vulnerability) -> str:
    base_recommendation = (
        vulnerability.recommendation
        or "Проверьте детали отчета сканера или рекомендации поставщика"
    )
    if vulnerability.fixed_version:
        return (
            f"{base_recommendation}. "
            f"Обновите пакет до версии {vulnerability.fixed_version} или выше."
        )
    return f"{base_recommendation}. Исправленная версия не указана."
