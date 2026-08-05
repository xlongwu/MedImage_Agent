"""SPM realign dry-run output manifest planner.

Validates inputs and params, predicts output paths, reports
approval/environment requirements.  Never runs MATLAB/SPM, never
creates files or directories.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.backend.app.schemas.desktop import (
    SpmRealignDryRunResponse,
    SpmRealignInputPreview,
)
from src.backend.app.services.bold_reference_readiness import (
    build_bold_reference_readiness,
)
from src.backend.app.services.environment_health import build_matlab_spm_health
from src.backend.app.services.mock_store import mock_store
from src.backend.app.services.spm_realign_params import (
    validate_spm_realign_params,
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _safe_slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in value)[:80]


def _predict_output(
    subject_id: str | None,
    bold_path: Path,
    output_root: Path,
    kind: str,
) -> tuple[str, str | None]:
    """Return (path, warning) for a predicted output."""
    stem = bold_path.name
    for ext in (".nii.gz", ".nii"):
        if stem.endswith(ext):
            stem = stem[: -len(ext)]
            break

    subj = subject_id or "unknown"

    if kind == "realigned_bold":
        rel = f"{subj}/func/r{stem}.nii.gz"
    elif kind == "mean_bold":
        rel = f"{subj}/func/mean{stem}.nii.gz"
    elif kind == "motion_params":
        rel = f"{subj}/func/rp_{stem}.txt"
    elif kind == "stdout_log":
        rel = f"logs/{subj}_spm_realign_stdout.log"
    elif kind == "stderr_log":
        rel = f"logs/{subj}_spm_realign_stderr.log"
    elif kind == "provenance_json":
        rel = f"provenance/{subj}_spm_realign_provenance.json"
    elif kind == "node_state_json":
        rel = f"state/{subj}_spm_realign_node_state.json"
    else:
        return "", f"Unknown output kind: {kind}"

    resolved = (output_root / rel).resolve()
    exists = resolved.exists()
    would_overwrite = exists and resolved.is_file()

    return str(resolved), (
        f"Output file already exists and would be overwritten: {resolved}"
        if would_overwrite
        else None
    )


def build_spm_realign_dry_run(
    project_id: str,
    params: dict[str, Any] | None = None,
) -> SpmRealignDryRunResponse:
    """Plan SPM realign output manifest without executing."""

    now = _now_iso()
    warnings: list[str] = []
    blocking: list[str] = []

    project = mock_store.get_project(project_id)
    if project is None:
        return SpmRealignDryRunResponse(
            ok=False, project_id=project_id, status="blocked", checked_at=now,
            blocking_issues=[f"Project not found: {project_id}"],
            safety_flags=_safety_flags(),
        )

    # Validate params
    cleaned, param_warnings, param_errors = validate_spm_realign_params(params or {})
    if param_errors:
        return SpmRealignDryRunResponse(
            ok=False, project_id=project_id, status="blocked", checked_at=now,
            params=params or {}, param_warnings=param_warnings, param_errors=param_errors,
            blocking_issues=param_errors,
            safety_flags=_safety_flags(),
        )

    # Get BOLD candidates
    bold = build_bold_reference_readiness(project_id)
    bold_dict = bold.model_dump()
    candidates = bold_dict.get("candidates", [])

    # Get environment health
    env = build_matlab_spm_health()
    env_status = env.get("status", "unknown")

    # Output root preview
    metadata = project.metadata if isinstance(project.metadata, dict) else {}
    project_dir = str(metadata.get("project_dir") or "")
    output_root = (
        Path(project_dir).expanduser().resolve() / "outputs" / "derivatives" / "spm_realign" / _safe_slug(project_id)
    ) if project_dir else None

    output_root_str = str(output_root) if output_root else None

    # Check rawdata safety
    rawdata = str(metadata.get("rawdata_dir") or "")
    if output_root and rawdata:
        try:
            output_root.resolve().relative_to(Path(rawdata).expanduser().resolve())
            blocking.append("Output root preview is inside rawdata — blocked.")
        except ValueError:
            pass

    inputs: list[dict[str, Any]] = []
    ready_count = 0

    for cand in candidates[:50]:
        bold_path = cand.get("bold_path", "")
        if not bold_path:
            continue
        bp = Path(bold_path)
        subject_id = cand.get("subject_id")
        vol_count = cand.get("volume_count")
        strategy = cand.get("reference_strategy")
        is_4d = cand.get("is_4d", False)
        cand_warnings: list[str] = list(cand.get("warnings", []))

        valid = bool(is_4d and vol_count and vol_count >= 3)

        pred_outputs: list[dict[str, Any]] = []
        if output_root:
            for kind in (
                "realigned_bold", "mean_bold", "motion_params",
                "stdout_log", "stderr_log", "provenance_json", "node_state_json",
            ):
                path_str, warning = _predict_output(subject_id, bp, output_root, kind)
                pred_outputs.append({
                    "kind": kind,
                    "path": path_str,
                    "exists": Path(path_str).exists() if path_str else False,
                    "would_overwrite": warning is not None,
                    "warning": warning,
                })
                if warning:
                    cand_warnings.append(warning)

        inputs.append({
            "subject_id": subject_id,
            "session_id": cand.get("session_id"),
            "bold_path": bold_path,
            "relative_path": cand.get("relative_path"),
            "volume_count": vol_count,
            "reference_strategy": strategy,
            "valid_for_realign": valid,
            "warnings": cand_warnings,
            "predicted_outputs": pred_outputs,
        })
        if valid:
            ready_count += 1

    # Status determination
    if not candidates:
        status = "blocked"
        blocking.append("No BOLD candidates found.")
    elif ready_count == 0:
        status = "blocked"
        blocking.append("No BOLD candidates meet the minimum requirements (4D, ≥3 volumes).")
    elif blocking:
        status = "blocked"
    elif env_status in ("not_configured", "warning"):
        status = "warning"
    elif ready_count > 0:
        status = "ready"
    else:
        status = "unknown"

    next_actions: list[str] = []
    if not candidates:
        next_actions.append("Import a BIDS dataset with 4D BOLD functional data.")
    if ready_count == 0 and candidates:
        next_actions.append("Ensure BOLD files are 4D with at least 3 volumes.")
    if env_status == "not_configured":
        next_actions.append("Configure MATLAB and SPM paths in desktop settings.")
    if status == "ready":
        next_actions.append("Review predicted output paths and proceed to reviewed-plan execution when SPM execution is enabled.")
    if param_warnings:
        next_actions.append("Review parameter warnings.")
    if not next_actions:
        next_actions.append("Complete data readiness and environment checks before attempting SPM realign.")

    return SpmRealignDryRunResponse(
        ok=len(blocking) == 0,
        project_id=project_id,
        status=status,
        dry_run=True,
        checked_at=now,
        params=cleaned,
        param_warnings=param_warnings,
        param_errors=param_errors,
        input_count=len(inputs),
        ready_input_count=ready_count,
        inputs=[SpmRealignInputPreview(**i) for i in inputs],
        output_root_preview=output_root_str,
        environment_status=env_status,
        approval_required=True,
        audit_required=True,
        execution_enabled=False,
        safe_allowlist_enabled=False,
        blocking_issues=blocking[:10],
        warnings=warnings[:30],
        next_actions=next_actions[:10],
        safety_flags=_safety_flags(),
    )


def _safety_flags() -> dict[str, bool]:
    return {
        "dry_run_only": True,
        "rawdata_not_modified": True,
        "no_files_created": True,
        "no_matlab_called": True,
        "no_spm_called": True,
        "execution_disabled": True,
        "approval_required": True,
        "audit_required": True,
    }
