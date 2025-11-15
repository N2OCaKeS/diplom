from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class Status(str, Enum):
    PASS = "pass"
    WARN = "warn"
    MEDIUM = "medium"
    HIGH = "high"


class EvaluationRequest(BaseModel):
    image: str
    commit: str
    project: str
    pipeline_id: str
    report: dict[str, Any]


class EvaluationResponse(BaseModel):
    decision: Decision
    status: Status
    report_id: str
    jira_issue_key: str
    message: str
    recommendations_url: str


@dataclass(slots=True)
class Vulnerability:
    id: str
    severity: str
    title: str | None = None
    description: str | None = None
    recommendation: str | None = None
    url: str | None = None
    fixed_version: str | None = None
    package: str | None = None


@dataclass(slots=True)
class AnalysisResult:
    decision: Decision
    status: Status
    message: str
    vulnerabilities: list[Vulnerability]


@dataclass(slots=True)
class JiraIssue:
    key: str
    url: str
