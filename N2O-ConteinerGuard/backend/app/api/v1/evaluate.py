from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import SecurityDependency
from app.db.repositories import ReportRepository
from app.db.session import get_session
from app.domain.analyzer import Analyzer
from app.domain.models import AnalysisResult, EvaluationRequest, EvaluationResponse
from app.domain.report_builder import build_jira_description
from app.integrations.jira_client import JiraClient

router = APIRouter(tags=["evaluation"])


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_image(
    payload: EvaluationRequest,
    _: None = Depends(SecurityDependency()),
    session: AsyncSession = Depends(get_session),
) -> EvaluationResponse:
    settings = get_settings()

    analyzer = Analyzer(settings.policies)
    analysis: AnalysisResult = analyzer.evaluate(payload.project, payload.report)

    jira_client = JiraClient.from_settings(settings)
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
