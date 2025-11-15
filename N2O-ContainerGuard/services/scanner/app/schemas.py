from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class ImageScanRequest(BaseModel):
    ref: str = Field(
        ..., description="Ссылка на контейнерный образ, например ghcr.io/org/app:tag"
    )
    project: Optional[str] = None
    policy_name: Optional[str] = None  # на будущее: имя политики из БД/файла


class Finding(BaseModel):
    source: str = "trivy"
    vuln_id: str
    title: Optional[str] = None
    severity: str
    package: Optional[str] = None
    version: Optional[str] = None
    fixed_in: Optional[str] = None
    cvss: Optional[float] = None
    links: List[str] = []
    extra: Dict[str, Any] = {}


class ScanResult(BaseModel):
    artifact_type: str = "image"
    ref: str
    summary: Dict[str, int]
    findings: List[Finding]
    raw_path: str
    normalized_path: str
