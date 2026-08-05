from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Query

from src.backend.app.api._errors import raise_api_error
from src.backend.app.core.exceptions import ConfigError
from src.backend.app.runtime.path_safety import read_safe_text_file
from src.backend.app.version import APP_VERSION

router = APIRouter()


@router.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "medimage-agent-api",
        "status": "healthy",
        "version": APP_VERSION,
    }


@router.get("/api/project-config")
def get_project_config(
    path: str = Query(default="examples/project_config_dataset.yaml"),
) -> dict[str, Any]:
    try:
        data = read_safe_text_file(path)
        parsed = yaml.safe_load(data["content"]) or {}
        return {
            "ok": True,
            "path": data["relative_path"],
            "config": parsed,
        }
    except Exception as exc:
        raise_api_error(exc, error_cls=ConfigError)


def _load_project_config(path: str) -> dict[str, Any]:
    """Load and validate a project config YAML file."""
    from src.backend.app.config import ProjectSettings

    try:
        ProjectSettings.from_yaml(path)
    except FileNotFoundError as exc:
        raise ConfigError(str(exc)) from exc
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc

    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Project config not found: {path}")
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise ConfigError(f"Failed to parse project config: {exc}") from exc
