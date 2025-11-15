from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class PolicySettings(BaseModel):
    block_on_severity: str = Field(default="CRITICAL")
    warn_on_severity: str = Field(default="HIGH")
    allow_unfixed: bool = Field(default=False)
    treat_unknown_as: str = Field(default="HIGH")

    def model_post_init(self, __context: Any) -> None:
        self.block_on_severity = self.block_on_severity.upper()
        self.warn_on_severity = self.warn_on_severity.upper()
        self.treat_unknown_as = self.treat_unknown_as.upper()


class PolicyConfig(BaseModel):
    default: PolicySettings = Field(default_factory=PolicySettings)
    projects: dict[str, PolicySettings] = Field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PolicyConfig":
        default_data = data.get("default", {})
        projects_data = data.get("projects", {})
        default = PolicySettings(**default_data)
        projects = {
            name: PolicySettings(**values)
            for name, values in projects_data.items()
        }
        return cls(default=default, projects=projects)

    def for_project(self, project: str | None) -> PolicySettings:
        if project and project in self.projects:
            return self.projects[project]
        return self.default


class Settings(BaseModel):
    auth_mode: str = Field(default="none")
    jwt_secret: str | None = Field(default=None)
    jwt_algorithm: str = Field(default="HS256")
    jwt_audience: str | None = Field(default=None)
    jwt_issuer: str | None = Field(default=None)
    auth_validation_url: str | None = Field(default=None)

    database_url: str = Field(default="postgresql+asyncpg://postgres:postgres@postgres:5432/guard")

    jira_url: str | None = None
    jira_browse_url: str | None = None
    jira_user: str | None = None
    jira_api_token: str | None = None
    jira_project_key: str | None = None

    policies_path: Path = Field(default=Path("policies.yml"))

    policies: PolicyConfig = Field(default_factory=PolicyConfig)

    def model_post_init(self, __context: Any) -> None:
        self.policies = self._load_policies()
        if not self.jira_browse_url and self.jira_url:
            self.jira_browse_url = self.jira_url.rstrip("/")

    def _load_policies(self) -> PolicyConfig:
        if not self.policies_path.exists():
            return PolicyConfig()
        with self.policies_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
        return PolicyConfig.from_dict(data)

    @classmethod
    def from_env(cls) -> "Settings":
        data: dict[str, Any] = {}
        for field in cls.model_fields:
            env_key = field.upper()
            if env_key in os.environ:
                data[field] = os.environ[env_key]
        return cls(**data)


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
