from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID

from backend.app.db.base import Base
from backend.app.domain.models import Decision, Status


class ReportORM(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image = Column(String(255), nullable=False)
    commit = Column(String(128), nullable=False)
    project = Column(String(128), nullable=False)
    pipeline_id = Column(String(128), nullable=False)
    decision = Column(
        Enum(
            Decision,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            name="decision",
        ),
        nullable=False,
    )
    status = Column(
        Enum(
            Status,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            name="status",
        ),
        nullable=False,
    )
    message = Column(String(512), nullable=False)
    report = Column(JSON, nullable=False)
    jira_issue_key = Column(String(64), nullable=False)
    recommendations_url = Column(String(512), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
