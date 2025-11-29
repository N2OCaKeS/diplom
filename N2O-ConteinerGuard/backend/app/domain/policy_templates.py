from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

from backend.app.core.config import PolicyConfig

DEFAULT_TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "policy_templates"


@dataclass(slots=True)
class PolicyTemplate:
    name: str
    path: Path
    config: PolicyConfig


class PolicyTemplateLoader:
    """Load policy templates stored as YAML files."""

    def __init__(self, directory: Path | None = None) -> None:
        base = directory or DEFAULT_TEMPLATES_DIR
        self._directory = base.resolve()

    def list_templates(self) -> list[PolicyTemplate]:
        templates: list[PolicyTemplate] = []
        for path in self._iter_template_files():
            templates.append(self._build_template(path))
        return templates

    def get_template(self, name: str) -> PolicyTemplate:
        for path in self._iter_template_files():
            if path.stem == name:
                return self._build_template(path)
        raise FileNotFoundError(f"Policy template '{name}' not found")

    def _build_template(self, path: Path) -> PolicyTemplate:
        config = self._load_config(path)
        return PolicyTemplate(name=path.stem, path=path, config=config)

    def _iter_template_files(self) -> Iterable[Path]:
        directory = self._directory
        if not directory.exists():
            return []
        candidates: set[Path] = set()
        for pattern in ("*.yml", "*.yaml"):
            for file in directory.glob(pattern):
                if file.is_file():
                    candidates.add(file.resolve())
        return sorted(candidates)

    def _load_config(self, path: Path) -> PolicyConfig:
        with path.open("r", encoding="utf-8") as file:
            data: dict[str, Any] | None = yaml.safe_load(file)
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ValueError(f"Policy template {path} must contain a mapping")
        return PolicyConfig.from_dict(data)
