from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.app.db.models import ReportORM
from backend.app.domain.models import AnalysisResult, EvaluationRequest


class ReportRepository:
    def __init__(self, session: AsyncSession | Session) -> None:
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
        if isinstance(self._session, AsyncSession):
            await self._session.commit()
            await self._session.refresh(report)
        else:
            self._session.commit()
            self._session.refresh(report)
        return report
