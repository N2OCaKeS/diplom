from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import ReportORM
from backend.app.domain.models import AnalysisResult, EvaluationRequest


class ReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_report(
        self,
        request: EvaluationRequest,
        analysis: AnalysisResult,
        jira_issue_key: str,
        recommendations_url: str,
    ) -> ReportORM:
        report = ReportORM(
            image=request.image,
            commit=request.commit,
            project=request.project,
            pipeline_id=request.pipeline_id,
            decision=analysis.decision,
            status=analysis.status,
            message=analysis.message,
            report=request.report,
            jira_issue_key=jira_issue_key,
            recommendations_url=recommendations_url,
        )
        self._session.add(report)
        await self._session.commit()
        await self._session.refresh(report)
        return report
