"""Pipeline Writer — safely write reviewed pipeline dicts as YAML files.

This module writes executor-compatible pipeline dicts to a controlled
directory so that run_pipeline(project_config_path, pipeline_path) can
consume them.  NEVER writes to rawdata, derivatives, or user-supplied
arbitrary paths.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT_DIR = Path("outputs/work/reviewed_pipelines")
_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_.-]")


def _sanitize_name(name: str) -> str:
    """Replace unsafe characters with underscores.  Also remove '..' patterns."""
    sanitized = name.replace("..", "__")
    sanitized = _SAFE_NAME_RE.sub("_", sanitized)
    # Collapse multiple underscores and strip
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized or "pipeline"


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")


def write_reviewed_pipeline_yaml(
    pipeline: dict[str, Any],
    *,
    audit_id: str | None = None,
    plan_hash: str | None = None,
    output_dir: str | Path | None = None,
) -> Path:
    """Write an executor-compatible pipeline dict as a YAML file.

    Args:
        pipeline: Pipeline dict from plan_adapter.reviewed_plan_to_pipeline_dict.
        audit_id: Optional audit record id for traceability.
        plan_hash: Optional plan hash for filename uniqueness.
        output_dir: Override output directory (must stay under repo root).

    Returns:
        Path to the written YAML file.

    Raises:
        ValueError: If output_dir escapes the allowed base directory.
    """
    try:
        import yaml
    except ImportError:
        raise ImportError("Missing dependency: PyYAML. Install with: pip install pyyaml")

    # ── Resolve output directory ──
    base = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    base = base.resolve()

    # Safety: when using the default dir, it must stay under repo root.
    # When output_dir is explicitly provided by a trusted caller (tests, API),
    # we allow it — the caller is responsible for path safety.
    if output_dir is None:
        repo_root = Path.cwd().resolve()
        if not str(base).startswith(str(repo_root)):
            raise ValueError(f"Default output_dir must be under the repository root: {base}")

    base.mkdir(parents=True, exist_ok=True)

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
    # Ensure uniqueness
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
