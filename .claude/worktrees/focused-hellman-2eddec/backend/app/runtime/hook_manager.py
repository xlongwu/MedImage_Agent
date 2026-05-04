from __future__ import annotations

from pathlib import Path
from typing import Any


class HookError(Exception):
    pass


def run_before_plan(
    project_config: dict[str, Any],
    pipeline_path: str,
) -> list[str]:
    warnings: list[str] = []
    if not Path(pipeline_path).exists():
        raise HookError(f"Pipeline file not found: {pipeline_path}")

    safety = project_config.get("safety", {})
    if not safety.get("rawdata_readonly", True):
        warnings.append("rawdata_readonly is not enabled.")

    return warnings


def run_after_plan(plan: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if not plan.get("nodes"):
        warnings.append("Plan contains no nodes.")
    return warnings


def run_before_execute(
    project_config: dict[str, Any],
    plan_path: str,
    approved: bool,
) -> list[str]:
    warnings: list[str] = []

    if not approved:
        raise HookError("Execution requires explicit approval.")

    if not Path(plan_path).exists():
        raise HookError(f"Plan file not found: {plan_path}")

    safety = project_config.get("safety", {})
    if not safety.get("rawdata_readonly", True):
        raise HookError("Refusing to execute because rawdata_readonly is false.")

    if safety.get("allow_overwrite_derivatives", False):
        warnings.append("allow_overwrite_derivatives is enabled.")

    return warnings


def run_after_execute(summary: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if summary.get("status") not in {"SUCCESS", "PARTIAL"}:
        warnings.append(f"Pipeline finished with status={summary.get('status')}")
    return warnings


def run_on_error(exc: Exception) -> dict[str, Any]:
    return {
        "ok": False,
        "error_type": exc.__class__.__name__,
        "error": str(exc),
    }
