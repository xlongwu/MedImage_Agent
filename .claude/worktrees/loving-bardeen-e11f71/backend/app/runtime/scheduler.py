from __future__ import annotations

from typing import Any


DEFAULT_SCHEDULER = {
    "mode": "sequential",
    "max_workers": 1,
    "matlab_max_workers": 1,
}


def get_scheduler_config(
    project_config: dict[str, Any],
    pipeline_execution: dict[str, Any],
) -> dict[str, Any]:
    config = dict(DEFAULT_SCHEDULER)

    project_scheduler = project_config.get("scheduler", {}) or {}
    execution_scheduler = pipeline_execution.get("scheduler", {}) or {}

    config.update(project_scheduler)
    config.update(execution_scheduler)

    return validate_scheduler_config(config)


def validate_scheduler_config(config: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    mode = str(config.get("mode", "sequential"))

    if mode not in {"sequential", "local_parallel"}:
        errors.append(f"Unsupported scheduler mode: {mode}")
        mode = "sequential"

    try:
        max_workers = int(config.get("max_workers", 1))
    except Exception:
        max_workers = 1
        warnings.append("Invalid max_workers; fallback to 1.")

    try:
        matlab_max_workers = int(config.get("matlab_max_workers", 1))
    except Exception:
        matlab_max_workers = 1
        warnings.append("Invalid matlab_max_workers; fallback to 1.")

    if max_workers < 1:
        warnings.append("max_workers < 1; fallback to 1.")
        max_workers = 1

    if max_workers > 8:
        warnings.append("max_workers > 8; capped to 8 for MVP safety.")
        max_workers = 8

    if matlab_max_workers < 1:
        warnings.append("matlab_max_workers < 1; fallback to 1.")
        matlab_max_workers = 1

    if matlab_max_workers > max_workers:
        warnings.append("matlab_max_workers > max_workers; capped to max_workers.")
        matlab_max_workers = max_workers

    if mode == "sequential":
        max_workers = 1
        matlab_max_workers = 1

    return {
        "ok": len(errors) == 0,
        "mode": mode,
        "max_workers": max_workers,
        "matlab_max_workers": matlab_max_workers,
        "warnings": warnings,
        "errors": errors,
    }


def create_scheduler_plan(
    pipeline: Any,
    project_config: dict[str, Any],
) -> dict[str, Any]:
    config = get_scheduler_config(project_config, pipeline.execution)

    subject_nodes = [
        node.id for node in pipeline.nodes if node.parallel_level == "subject"
    ]

    matlab_subject_nodes = [
        node.id
        for node in pipeline.nodes
        if node.parallel_level == "subject" and "matlab" in node.backend
    ]

    warnings = list(config.get("warnings", []))

    if config["mode"] == "local_parallel" and not subject_nodes:
        warnings.append("local_parallel enabled but no subject-level nodes found.")

    if matlab_subject_nodes and config["matlab_max_workers"] > 1:
        warnings.append(
            "Running multiple MATLAB workers may consume multiple MATLAB licenses."
        )

    return {
        "ok": config["ok"],
        "mode": config["mode"],
        "max_workers": config["max_workers"],
        "matlab_max_workers": config["matlab_max_workers"],
        "subject_level_nodes": subject_nodes,
        "matlab_subject_nodes": matlab_subject_nodes,
        "estimated_parallelism": {
            "subject_workers": config["max_workers"],
            "matlab_workers": config["matlab_max_workers"],
        },
        "warnings": warnings,
        "errors": config.get("errors", []),
    }
