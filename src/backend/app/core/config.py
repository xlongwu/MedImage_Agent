from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BackendSettings:
    host: str = "127.0.0.1"
    port: int = 8000
    service_name: str = "medimage-agent-backend"
    api_version: str = "0.1.0"


def get_backend_settings() -> BackendSettings:
    raw_port = os.environ.get("MEDIMAGE_BACKEND_PORT", "8000")
    try:
        port = int(raw_port)
    except ValueError:
        port = 8000
    return BackendSettings(
        host=os.environ.get("MEDIMAGE_BACKEND_HOST", "127.0.0.1"),
        port=port,
    )

