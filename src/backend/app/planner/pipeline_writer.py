"""Pipeline Writer — safely write reviewed pipeline dicts as YAML files.

Writes executor-compatible pipeline dicts to a fixed safe directory.
NEVER writes to rawdata, derivatives, reports, or user-supplied paths.
Tests monkeypatch REVIEWED_PIPELINE_DIR to use tmp_path.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REVIEWED_PIPELINE_DIR = Path("outputs/work/reviewed_pipelines")

_FORBIDDEN_DIRS = [
    Path("data"),
    Path("rawdata"),
    Path("outputs/derivatives"),
    Path("derivatives"),
    Path("outputs/reports"),
    Path("reports"),
]

_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_.-]")


def _sanitize_name(name: str) -> str:
    sanitized = name.replace("..", "__")
    sanitized = _SAFE_NAME_RE.sub("_", sanitized)
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized or "pipeline"


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")


def write_reviewed_pipeline_yaml(
    pipeline: dict[str, Any],
    *,
    audit_id: str | None = None,
    plan_hash: str | None = None,
) -> Path:
    """Write an executor-compatible pipeline dict as a YAML file.

    Writes to REVIEWED_PIPELINE_DIR (monkeypatchable for tests).
    Never writes to rawdata, derivatives, or reports.

    Args:
        pipeline: Pipeline dict from plan_adapter.
        audit_id: Optional audit record id.
        plan_hash: Optional plan hash for filename uniqueness.

    Returns:
        Path to the written YAML file.

    Raises:
        ValueError: If output dir would be outside the allowed base.
    """
    try:
        import yaml
    except ImportError:
        raise ImportError("Missing dependency: PyYAML. Install with: pip install pyyaml")

    base = REVIEWED_PIPELINE_DIR.resolve()
    base.mkdir(parents=True, exist_ok=True)

    # ── Safety: forbid forbidden directories ──
    repo = Path.cwd().resolve()
    for forbidden in _FORBIDDEN_DIRS:
        fb = (repo / forbidden).resolve()
        if str(base).startswith(str(fb)):
            raise ValueError(f"Cannot write to forbidden directory: {forbidden}")

    # ── Safety: path traversal / escape ──
    if ".." in str(base):
        raise ValueError("output_dir contains path traversal: '..'")

    # ── Build safe filename ──
    name = _sanitize_name(str(pipeline.get("pipeline_id", pipeline.get("name", "pipeline"))))
    ts = _now_stamp()
    suffix = ""
    if plan_hash:
        suffix = f"_{plan_hash[:12]}"
    elif audit_id:
        suffix = f"_{audit_id[:12]}"

    filename = f"reviewed_{name}_{ts}{suffix}.yaml"

    target = base / filename
    if target.exists():
        counter = 1
        while target.exists():
            filename = f"reviewed_{name}_{ts}{suffix}_{counter}.yaml"
            target = base / filename
            counter += 1

    # ── Atomic write ──
    tmp = target.with_suffix(".tmp")
    tmp.write_text(
        yaml.safe_dump(pipeline, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    tmp.replace(target)

    return target
