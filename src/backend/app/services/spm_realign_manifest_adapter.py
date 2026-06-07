"""SPM realign manifest adapter — pure helpers for schema alignment.

Converts dry-run predicted outputs into future execution contract
schemas (output manifest items, output manifest, provenance preview)
without executing MATLAB/SPM or writing files.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.backend.app.schemas.desktop import (
    SpmRealignExecutionProvenance,
    SpmRealignOutputManifest,
    SpmRealignOutputManifestItem,
)

_REQUIRED_KINDS: frozenset[str] = frozenset({
    "realigned_bold",
    "mean_bold",
    "motion_params",
    "stdout_log",
    "stderr_log",
    "provenance_json",
    "node_state_json",
})


def predicted_output_to_manifest_item(
    predicted: dict[str, Any],
    relative_to: str | None = None,
) -> SpmRealignOutputManifestItem:
    """Convert a dry-run predicted output dict into an output manifest item."""
    kind = str(predicted.get("kind", "realigned_bold"))
    path = str(predicted.get("path", ""))
    exists = bool(predicted.get("exists", False))
    would_overwrite = bool(predicted.get("would_overwrite", False))
    warning = predicted.get("warning")
    warnings: list[str] = []
    if would_overwrite and warning:
        warnings.append(str(warning))
    if would_overwrite and not warning:
        warnings.append(f"Output file already exists and would be overwritten: {path}")

    # Compute relative_path
    relative_path: str | None = None
    if relative_to and path.startswith(relative_to):
        rel = path[len(relative_to):].lstrip("/").lstrip("\\")
        if rel:
            relative_path = rel

    return SpmRealignOutputManifestItem(
        kind=kind,
        path=path,
        relative_path=relative_path,
        exists=exists,
        size_bytes=predicted.get("size_bytes"),
        checksum_sha256=predicted.get("checksum_sha256"),
        modified_at=predicted.get("modified_at"),
        required=kind in _REQUIRED_KINDS,
        verified=False,
        warnings=warnings[:5],
    )


def build_output_manifest_from_dry_run_input(
    *,
    project_id: str,
    run_id: str,
    input_preview: dict[str, Any],
    output_root: str,
) -> SpmRealignOutputManifest:
    """Build an output manifest from a single dry-run input preview."""
    subject_id = input_preview.get("subject_id")
    session_id = input_preview.get("session_id")

    items: list[SpmRealignOutputManifestItem] = []
    errors: list[str] = []
    manifest_warnings: list[str] = list(
        input_preview.get("warnings", [])[:20]
    )

    for pred in input_preview.get("predicted_outputs", [])[:50]:
        if not isinstance(pred, dict):
            continue
        item = predicted_output_to_manifest_item(pred, relative_to=output_root)
        items.append(item)
        if item.warnings:
            manifest_warnings.extend(item.warnings[:5])

    verified_count = sum(1 for i in items if i.verified)
    missing_required_count = sum(1 for i in items if i.required and not i.exists)

    return SpmRealignOutputManifest(
        project_id=project_id,
        run_id=run_id,
        node_id="spm_realign_subject",
        subject_id=subject_id,
        session_id=session_id,
        output_root=output_root,
        items=items,
        missing_required_count=missing_required_count,
        verified_count=verified_count,
        warnings=manifest_warnings[:30],
        errors=errors[:20],
    )


def build_provenance_preview_from_dry_run(
    *,
    project_id: str,
    reviewed_plan_id: str,
    run_id: str,
    dry_run: dict[str, Any],
    command_template_id: str,
    approval_context: dict[str, Any] | None = None,
) -> SpmRealignExecutionProvenance:
    """Build a provenance preview from a dry-run response dict."""
    params = deepcopy(dry_run.get("params", {}) or {})

    # Collect input paths and predicted outputs from all candidates
    input_paths: list[str] = []
    predicted_paths: list[str] = []
    stdout_log_path: str | None = None
    stderr_log_path: str | None = None

    for inp in dry_run.get("inputs", [])[:50]:
        if not isinstance(inp, dict):
            continue
        bp = str(inp.get("bold_path", ""))
        if bp and bp not in input_paths:
            input_paths.append(bp)
        for pred in inp.get("predicted_outputs", [])[:10]:
            if not isinstance(pred, dict):
                continue
            kind = str(pred.get("kind", ""))
            pp = str(pred.get("path", ""))
            if pp and pp not in predicted_paths:
                predicted_paths.append(pp)
            if kind == "stdout_log" and stdout_log_path is None:
                stdout_log_path = pp
            if kind == "stderr_log" and stderr_log_path is None:
                stderr_log_path = pp

    env_status = dry_run.get("environment_status")
    all_warnings: list[str] = list(dry_run.get("warnings", [])[:20])

    return SpmRealignExecutionProvenance(
        project_id=project_id,
        reviewed_plan_id=reviewed_plan_id,
        run_id=run_id,
        node_id="spm_realign_subject",
        command_template_id=command_template_id,
        params=params,
        input_paths=input_paths[:100],
        input_checksums={},
        predicted_output_paths=predicted_paths[:200],
        actual_output_paths=[],
        matlab_version=None,
        spm_version=None,
        platform=None,
        started_at=None,
        finished_at=None,
        return_code=None,
        stdout_log_path=stdout_log_path,
        stderr_log_path=stderr_log_path,
        batch_file_path=None,
        dry_run_manifest_id=None,
        approval_context=deepcopy(approval_context) if approval_context else {},
        warnings=all_warnings[:30],
        errors=[],
    )
