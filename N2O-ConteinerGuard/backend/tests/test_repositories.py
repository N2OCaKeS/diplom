from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.db.base import Base
from backend.app.db.models import ReportORM
from backend.app.db.repositories import ReportRepository
from backend.app.domain.models import (
    AnalysisResult,
    Decision,
    EvaluationRequest,
    Status,
    Vulnerability,
)


def _make_request() -> EvaluationRequest:
    return EvaluationRequest(
        image="registry.example.com/project/app:sha",
        commit="abcdef",
        project="sample",
        pipeline_id="42",
        report={"Results": []},
    )


def _make_analysis() -> AnalysisResult:
    return AnalysisResult(
        decision=Decision.ALLOW,
        status=Status.PASS,
        message="All good",
        vulnerabilities=[
            Vulnerability(id="CVE-1", severity="LOW", package="libssl"),
        ],
    )


def test_report_repository_persists_with_sync_session(session) -> None:
    repository = ReportRepository(session)

    stored = asyncio.run(
        repository.create_report(
            request=_make_request(),
            analysis=_make_analysis(),
            jira_issue_key="SEC-101",
            recommendations_url="https://confluence.example.com/pages/SEC-101",
        )
    )

    fetched = session.get(ReportORM, stored.id)
    assert fetched is not None
    assert fetched.image == "registry.example.com/project/app:sha"
    assert fetched.jira_issue_key == "SEC-101"
    assert fetched.report["Results"] == []


@pytest.mark.asyncio
async def test_report_repository_handles_async_session() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        async with async_session() as db_session:
            repository = ReportRepository(db_session)
            report = await repository.create_report(
                request=_make_request(),
                analysis=_make_analysis(),
                jira_issue_key="SEC-202",
                recommendations_url="https://confluence.example.com/pages/SEC-202",
            )

            result = await db_session.execute(select(ReportORM))
            stored = result.scalar_one()
            assert stored.id == report.id
            assert stored.message == "All good"
    finally:
        await engine.dispose()
