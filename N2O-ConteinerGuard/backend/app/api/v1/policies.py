from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from backend.app.core.config import PolicyConfig, get_settings
from backend.app.core.security import SecurityDependency
from backend.app.domain.policy_templates import PolicyTemplateLoader


class PolicyState(BaseModel):
    policies: PolicyConfig
    sources: list[str]


class PolicyOperationResponse(PolicyState):
    detail: str


class PolicyUpdateRequest(BaseModel):
    template: str | None = None
    policy: dict[str, Any] | None = None

    def ensure_payload(self) -> None:
        if not self.template and self.policy is None:
            raise ValueError("Either 'template' or 'policy' must be provided")


router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("", response_model=PolicyState)
async def get_policies(_: None = Depends(SecurityDependency())) -> PolicyState:
    settings = get_settings()
    return PolicyState(
        policies=settings.policies,
        sources=list(settings.policy_sources),
    )


@router.post("/reload", response_model=PolicyOperationResponse)
async def reload_policies(
    _: None = Depends(SecurityDependency()),
) -> PolicyOperationResponse:
    settings = get_settings()
    settings.reload_policies()
    return PolicyOperationResponse(
        detail="Policies reloaded",
        policies=settings.policies,
        sources=list(settings.policy_sources),
    )


@router.post("/update", response_model=PolicyOperationResponse)
async def update_policies(
    payload: PolicyUpdateRequest,
    _: None = Depends(SecurityDependency()),
) -> PolicyOperationResponse:
    settings = get_settings()
    try:
        payload.ensure_payload()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    if payload.template:
        loader = PolicyTemplateLoader(settings.policy_templates_path)
        try:
            template = loader.get_template(payload.template)
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        config = template.config
        sources = [template.path]
        detail = f"Policies updated from template '{template.name}'"
    else:
        try:
            config = PolicyConfig.from_dict(payload.policy or {})
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid policy payload",
            ) from exc
        sources = ["request"]
        detail = "Policies updated from request"

    settings.apply_policy_config(config, sources)

    return PolicyOperationResponse(
        detail=detail,
        policies=settings.policies,
        sources=list(settings.policy_sources),
    )


@router.post("/upload", response_model=PolicyOperationResponse)
async def upload_policy_file(
    policy_file: UploadFile = File(...),
    _: None = Depends(SecurityDependency()),
) -> PolicyOperationResponse:
    settings = get_settings()
    storage_dir = settings.policies_storage_path
    if storage_dir is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="POLICIES_STORAGE_PATH must be configured to upload policies",
        )

    filename = (policy_file.filename or "").strip()
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required"
        )
    target_name = Path(filename).name
    extension = Path(target_name).suffix.lower()
    if extension not in {".yml", ".yaml"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Policy file must be .yml or .yaml",
        )

    try:
        raw_content = await policy_file.read()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file",
        ) from exc

    if not raw_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty"
        )

    try:
        data = yaml.safe_load(raw_content) or {}
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid YAML: {exc}",
        ) from exc
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Policy file must contain a mapping",
        )

    try:
        PolicyConfig.from_dict(data)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid policy structure: {exc}",
        ) from exc

    storage_dir = storage_dir.resolve()
    storage_dir.mkdir(parents=True, exist_ok=True)
    target_path = storage_dir / target_name
    target_path.write_bytes(raw_content)

    settings.reload_policies()

    return PolicyOperationResponse(
        detail=f"Policy file '{target_name}' uploaded",
        policies=settings.policies,
        sources=list(settings.policy_sources),
    )
