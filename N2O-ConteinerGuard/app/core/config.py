from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field
from urllib.parse import urlsplit

# Load variables from a local .env file if it exists. This is a no-op when the
# file is missing, but it allows developers to configure the API without
# exporting variables manually.
load_dotenv()


class Settings(BaseModel):
    """Runtime configuration loaded from environment variables."""

    auth_api_url: Optional[AnyHttpUrl] = Field(
        default=None,
        description="External authorization endpoint used to validate access tokens.",
    )
    auth_api_timeout: float = Field(
        default=3.0,
        description="Timeout (in seconds) for requests to the external auth API.",
    )
    auth_service_name: Optional[str] = Field(
        default=None,
        description="Identifier of this service passed to the external authorization API.",
    )
    jwt_secret: Optional[str] = Field(
        default=None,
        description="Fallback shared secret for validating JWT tokens locally.",
    )
    app_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Port uvicorn should bind to when launching via `python -m app.main`.",
    )
    public_base_url: Optional[AnyHttpUrl] = Field(
        default=None,
        description="Public base URL used for configuring CORS and absolute links.",
    )

    model_config = ConfigDict(str_strip_whitespace=True)

    @property
    def auth_mode(self) -> str:
        """Return selected authorization strategy."""
        if self.auth_api_url:
            return "external"
        if self.jwt_secret:
            return "jwt"
        return "disabled"

    @property
    def cors_origins(self) -> list[str]:
        """Return list of allowed CORS origins derived from PUBLIC_BASE_URL."""
        if not self.public_base_url:
            return []
        parsed = urlsplit(str(self.public_base_url))
        origin = f"{parsed.scheme}://{parsed.netloc}"
        return [origin]


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance populated from env variables."""
    return Settings(
        auth_api_url=os.getenv("AUTH_API_URL") or None,
        auth_api_timeout=os.getenv("AUTH_API_TIMEOUT")
        or Settings.model_fields["auth_api_timeout"].default,
        auth_service_name=os.getenv("AUTH_SERVICE_NAME") or None,
        jwt_secret=os.getenv("JWT_SECRET") or None,
        app_port=os.getenv("APP_PORT") or Settings.model_fields["app_port"].default,
        public_base_url=os.getenv("PUBLIC_BASE_URL") or None,
    )
