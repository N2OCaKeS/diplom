from __future__ import annotations

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
from backend.app.domain.report_builder import build_jira_description
from backend.app.integrations.jira_client import JiraClient

router = APIRouter(tags=["evaluation"])


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_image(
    payload: EvaluationRequest,
    _: None = Depends(SecurityDependency()),
    session: AsyncSession = Depends(get_session),
) -> EvaluationResponse:
    settings = get_settings()
    if not settings.jira_browse_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Jira browse URL must be configured",
        )

    analyzer = Analyzer(settings.policies)
    analysis: AnalysisResult = analyzer.evaluate(payload.project, payload.report)

    try:
        jira_client = JiraClient.from_settings(settings)
    except ValueError as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc
    jira_description = build_jira_description(payload, analysis)

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
        recommendations_url=jira_issue.url,
    )

    return EvaluationResponse(
        decision=analysis.decision,
        status=analysis.status,
        report_id=str(report.id),
        jira_issue_key=jira_issue.key,
        message=analysis.message,
        recommendations_url=jira_issue.url,
    )
