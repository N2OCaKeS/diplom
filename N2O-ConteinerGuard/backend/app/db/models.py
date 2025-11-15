from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import JSON, Column, DateTime, Enum, String

from app.db.base import Base
from app.domain.models import Decision, Status


class ReportORM(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    image = Column(String(255), nullable=False)
    commit = Column(String(128), nullable=False)
    project = Column(String(128), nullable=False)
    pipeline_id = Column(String(128), nullable=False)
    decision = Column(Enum(Decision), nullable=False)
    status = Column(Enum(Status), nullable=False)
    message = Column(String(512), nullable=False)
    report = Column(JSON, nullable=False)
    jira_issue_key = Column(String(64), nullable=False)
    recommendations_url = Column(String(512), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
