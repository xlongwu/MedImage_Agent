from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_SPM_DIR = "./third_party/spm12"
DEFAULT_DPABI_DIR = "./third_party/DPABI_V8.2_240510"


def _paths_overlap(first: Path, second: Path) -> bool:
    try:
        first.relative_to(second)
        return True
    except ValueError:
        pass

    try:
        second.relative_to(first)
        return True
    except ValueError:
        return False


def write_project_config(
    project_id: str,
    project_name: str,
    project_dir: str | Path,
    rawdata_dir: str | Path,
    dataset_index_path: str | Path | None = None,
    spm_dir: str = DEFAULT_SPM_DIR,
    dpabi_dir: str = DEFAULT_DPABI_DIR,
    matlab_command: str = "matlab",
) -> Path:
    """Write a minimal ProjectSettings-compatible config inside project_dir."""
    project_path = Path(project_dir).resolve()
    rawdata_path = Path(rawdata_dir).resolve()
    if _paths_overlap(project_path, rawdata_path):
        raise ValueError("project_dir and rawdata_dir must not overlap")

    project_path.mkdir(parents=True, exist_ok=True)
    dataset_index = (
        Path(dataset_index_path).resolve()
        if dataset_index_path
        else (project_path / "data" / "dataset_index.json").resolve()
    )
    try:
        dataset_index.relative_to(project_path)
    except ValueError as exc:
        raise ValueError("dataset_index_path must be inside project_dir") from exc

    config: dict[str, Any] = {
        "project": {
            "name": project_name,
            "project_id": project_id,
            "root_dir": str(project_path),
        },
        "data": {
            "copy_mode": "reference",
            "rawdata_dir": str(rawdata_path),
            "dataset_index": str(dataset_index),
        },
        "third_party": {
            "spm_dir": spm_dir or DEFAULT_SPM_DIR,
            "dpabi_dir": dpabi_dir or DEFAULT_DPABI_DIR,
        },
        "runtime": {
            "matlab_command": matlab_command or "matlab",
            "work_dir": str(project_path / "work"),
            "log_dir": str(project_path / "logs"),
            "report_dir": str(project_path / "reports"),
            "derivatives_dir": str(project_path / "derivatives"),
        },
        "safety": {
            "rawdata_readonly": True,
            "allow_overwrite_derivatives": False,
            "require_confirmation": True,
        },
    }

    config_path = project_path / "project_config.yaml"
    try:
        config_path.resolve().relative_to(project_path)
    except ValueError as exc:
        raise ValueError("project_config.yaml must resolve inside project_dir") from exc
    config_path.write_text(
        yaml.safe_dump(
            config,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return config_path
