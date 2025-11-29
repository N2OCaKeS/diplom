from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
            name: PolicySettings(**values) for name, values in projects_data.items()
        }
        return cls(default=default, projects=projects)

    def for_project(self, project: str | None) -> PolicySettings:
        if project and project in self.projects:
            return self.projects[project]
        return self.default


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="allow"
    )

    auth_mode: str = Field(default="none")
    guard_token: str | None = Field(default=None)

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@postgres:5432/guard"
    )

    jira_url: str | None = None
    jira_user: str | None = None
    jira_api_token: str | None = None
    jira_project_key: str | None = None

    confluence_url: str | None = None
    confluence_user: str | None = None
    confluence_api_token: str | None = None
    confluence_space_key: str | None = None
    confluence_parent_page_id: str | None = None

    policies_path: Path = Field(default=Path("policies.yml"))
    policies_storage_path: Path | None = Field(default=None)
    policy_templates_path: Path = Field(
        default=Path(__file__).resolve().parents[2] / "policy_templates"
    )

    policies: PolicyConfig = Field(default_factory=PolicyConfig)
    policy_sources: tuple[str, ...] = Field(default_factory=tuple)

    def model_post_init(self, __context: Any) -> None:
        self.policies = self._load_policies()

    def _load_policies(self) -> PolicyConfig:
        loader = PolicyLoader(self.policies_path, self.policies_storage_path)
        config, sources = loader.load()
        return self.apply_policy_config(config, sources)

    def reload_policies(self) -> PolicyConfig:
        self.policies = self._load_policies()
        return self.policies

    def apply_policy_config(
        self, config: PolicyConfig, sources: Iterable[str | Path]
    ) -> PolicyConfig:
        self.policies = config
        self.policy_sources = tuple(str(source) for source in sources)
        return self.policies


@lru_cache
def get_settings() -> Settings:
    return Settings()


class PolicyLoader:
    def __init__(self, file_path: Path, storage_path: Path | None) -> None:
        self._file_path = file_path
        self._storage_path = storage_path

    def load(self) -> tuple[PolicyConfig, list[Path]]:
        sources = self._collect_sources()
        if not sources:
            return PolicyConfig(), []
        merged = self._merge_sources(sources)
        return PolicyConfig.from_dict(merged), sources

    def _collect_sources(self) -> list[Path]:
        files: list[Path] = []
        storage = self._storage_path
        if storage:
            storage_path = storage
            if storage_path.exists():
                files = self._find_storage_files(storage_path)
        if not files and self._file_path and self._file_path.exists():
            files = [self._file_path.resolve()]
        return files

    def _find_storage_files(self, storage: Path) -> list[Path]:
        candidates: list[Path] = []
        for pattern in ("*.yml", "*.yaml"):
            candidates.extend(storage.rglob(pattern))
        unique_candidates = sorted(
            {path.resolve() for path in candidates if path.is_file()}
        )
        return unique_candidates

    def _merge_sources(self, paths: Iterable[Path]) -> dict[str, Any]:
        merged_default: dict[str, Any] = {}
        merged_projects: dict[str, dict[str, Any]] = {}
        for path in paths:
            with path.open("r", encoding="utf-8") as file:
                data = yaml.safe_load(file) or {}
            if not isinstance(data, dict):
                continue
            default_data = data.get("default") or {}
            if isinstance(default_data, dict):
                merged_default.update(default_data)
            projects_data = data.get("projects") or {}
            if isinstance(projects_data, dict):
                for name, values in projects_data.items():
                    if not isinstance(values, dict):
                        continue
                    project = merged_projects.setdefault(name, {})
                    project.update(values)
        return {"default": merged_default, "projects": merged_projects}
