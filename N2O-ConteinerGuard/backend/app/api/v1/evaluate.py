from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.security import SecurityDependency
from backend.app.db.repositories import ReportRepository
from backend.app.db.session import get_session
from backend.app.domain.analyzer import Analyzer
from backend.app.domain.models import (
    AnalysisResult,
    EvaluationRequest,
    EvaluationResponse,
)
from backend.app.domain.report_builder import (
    build_confluence_report,
    build_jira_description,
)
from backend.app.integrations.confluence_client import ConfluenceClient
from backend.app.integrations.jira_client import JiraClient

router = APIRouter(tags=["evaluation"])


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_image(
    payload: EvaluationRequest,
    _: None = Depends(SecurityDependency()),
    session: AsyncSession = Depends(get_session),
) -> EvaluationResponse:
    settings = get_settings()
    if not settings.jira_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Jira URL must be configured",
        )

    analyzer = Analyzer(settings.policies)
    analysis: AnalysisResult = analyzer.evaluate(payload.project, payload.report)

    jira_client: JiraClient | None = None
    confluence_client: ConfluenceClient | None = None
    try:
        jira_client = JiraClient.from_settings(settings)
        confluence_client = ConfluenceClient.from_settings(settings)
    except ValueError as exc:  # pragma: no cover
        if jira_client:
            await jira_client.close()
        if confluence_client:
            await confluence_client.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc

    assert jira_client is not None
    assert confluence_client is not None

    confluence_body = build_confluence_report(payload, analysis)
    confluence_title = _build_confluence_title(payload)
    try:
        confluence_page = await confluence_client.create_page(
            title=confluence_title,
            body=confluence_body,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create Confluence page",
        ) from exc
    finally:
        await confluence_client.close()

    jira_description = build_jira_description(payload, analysis, confluence_page.url)

    try:
        jira_issue = await jira_client.create_issue(
            summary=f"[ContainerGuard] Vulnerabilities in image {payload.image}",
            description=jira_description,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create Jira issue",
        ) from exc
    finally:
        await jira_client.close()

    repository = ReportRepository(session)
    report = await repository.create_report(
        request=payload,
        analysis=analysis,
        jira_issue_key=jira_issue.key,
        recommendations_url=confluence_page.url,
    )

    return EvaluationResponse(
        decision=analysis.decision,
        status=analysis.status,
        report_id=str(report.id),
        jira_issue_key=jira_issue.key,
        message=analysis.message,
        recommendations_url=confluence_page.url,
    )


def _build_confluence_title(request: EvaluationRequest) -> str:
    parts = [
        "Report",
        _sanitize_title_part(request.image),
        _sanitize_title_part(request.commit),
    ]
    pipeline_part = _sanitize_title_part(request.pipeline_id)
    if pipeline_part != "unknown":
        parts.append(pipeline_part)
    return "_".join(parts)


def _sanitize_title_part(value: str | None) -> str:
    if not value:
        return "unknown"
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", value)
    normalized = normalized.strip("_")
    return normalized or "unknown"
