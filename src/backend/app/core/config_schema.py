from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    """Backend server configuration loaded from MEDIMAGE_* env vars."""

    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    service_name: str = "medimage-agent-backend"
    api_version: str = "0.1.0"
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "ServerConfig":
        raw_port = os.environ.get("MEDIMAGE_BACKEND_PORT", "8000")
        try:
            port = int(raw_port)
        except ValueError:
            port = 8000
        if port < 1 or port > 65535:
            port = 8000
        return cls(
            host=os.environ.get("MEDIMAGE_BACKEND_HOST", "127.0.0.1"),
            port=port,
            service_name=os.environ.get("MEDIMAGE_SERVICE_NAME", "medimage-agent-backend"),
            api_version=os.environ.get("MEDIMAGE_API_VERSION", "0.1.0"),
            log_level=os.environ.get("MEDIMAGE_LOG_LEVEL", "INFO"),
        )


class AppConfig(BaseModel):
    """Top-level configuration snapshot exposed by ConfigService."""

    server: ServerConfig
    project: dict[str, Any] | None = None
    project_config_path: str | None = None
