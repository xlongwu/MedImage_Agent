"""Temporal Filtering Sandbox Execution Service — Phase 5L. Python-only."""
from __future__ import annotations
import os, json, hashlib, shutil
from pathlib import Path

from src.backend.app.schemas.preprocessing_filtering_execution import (
    FilteringSandboxExecutionRequest, FilteringSandboxExecutionResponse,
    validate_filtering_env, filtering_safety_flags,
)
from src.backend.app.services.mock_store import mock_store


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def run_filtering_sandbox_execution(
    project_id: str, run_id: str, request: FilteringSandboxExecutionRequest,
    *, project_dir: str = "", env: dict[str, str] | None = None
) -> FilteringSandboxExecutionResponse:
    eff_env = env or dict(os.environ)
    ok_flags, missing = validate_filtering_env(eff_env)
    if not ok_flags:
        return FilteringSandboxExecutionResponse(ok=False, status="disabled", project_id=project_id,
            blocking_issues=[f"Missing env flags: {missing}"], safety_flags=filtering_safety_flags())

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")

    dry_dir = Path(effective_pd) / "preprocessing_runs" / run_id / "spm_dry_runs" / request.dry_run_id if effective_pd else None
    if not dry_dir or not dry_dir.exists():
        return FilteringSandboxExecutionResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=[f"Dry-run not found: {request.dry_run_id}"], safety_flags=filtering_safety_flags())

    func_input = request.functional_input_dir or str(meta.get("current_functional_input_dir") or "")
    func_path = Path(func_input) if func_input else None
    if not func_path or not func_path.exists():
        return FilteringSandboxExecutionResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["Functional input not found."], safety_flags=filtering_safety_flags())

    bold_files = [p for p in sorted(func_path.rglob("*.nii*")) if p.is_file() and ("bold" in p.name.lower() or "rest" in p.name.lower())]
    if not bold_files:
        return FilteringSandboxExecutionResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["No functional files found."], safety_flags=filtering_safety_flags())

    exec_id = "tf-ex-" + hashlib.sha256(f"{project_id}:{run_id}:{_now_iso()}".encode()).hexdigest()[:10]
    exec_dir = Path(effective_pd) / "preprocessing_runs" / run_id / "spm_exec" / exec_id if effective_pd else Path(f"outputs/spm_exec/{exec_id}")
    exec_dir.mkdir(parents=True, exist_ok=True)
    sandbox_in = exec_dir / "sandbox_input"; sandbox_in.mkdir()
    sandbox_out = exec_dir / "sandbox_output"; sandbox_out.mkdir()
    logs_dir = exec_dir / "logs"; logs_dir.mkdir()

    warnings: list[str] = []; copied = []; designs = []
    for bf in bold_files[:10]:
        subj = "sub-unknown"
        for part in bf.parts:
            if part.startswith("sub-"): subj = part; break
        dest = sandbox_in / subj; dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bf, dest / bf.name)
        copied.append(dest / bf.name)
        designs.append({"subject": subj, "functional": str(dest / bf.name), "filtered": False})

    # Attempt numerical filtering if scipy/numpy available
    metadata_only = True; filtered = 0
    _SCIPY_OK = False
    try:
        import numpy as _np; from scipy import signal as _sig
        _SCIPY_OK = True
    except ImportError:
        warnings.append("scipy/numpy not available; metadata-only execution.")

    if _SCIPY_OK:
        for cp, design in zip(copied, designs):
            try:
                import nibabel as _nib
                img = _nib.load(str(cp))
                data = img.get_fdata()
                T = data.shape[-1] if data.ndim >= 4 else data.shape[0]
                if T < 5:
                    warnings.append(f"{design['subject']}: too few timepoints ({T})")
                    continue
                tr = 2.0  # default; sidecar reading omitted for simplicity
                nyq = 0.5 / tr; low, high = 0.01 / nyq, 0.08 / nyq
                b, a = _sig.butter(2, [low, high], btype="band")
                orig_shape = data.shape; data_2d = data.reshape(-1, T)
                filtered_2d = _sig.filtfilt(b, a, data_2d, axis=-1)
                filtered_data = filtered_2d.reshape(orig_shape)
                filt_img = _nib.Nifti1Image(filtered_data.astype(_np.float32), img.affine, img.header)
                out_path = sandbox_out / design['subject'] / f"filtered_{cp.name}"
                out_path.parent.mkdir(parents=True, exist_ok=True)
                _nib.save(filt_img, str(out_path))
                design['filtered'] = True; design['output_path'] = str(out_path)
                filtered += 1; metadata_only = False
            except Exception as exc:
                warnings.append(f"{design['subject']}: {exc}")

    fd_path = exec_dir / "filter_design.json"
    fd_path.write_text(json.dumps({"designs": designs, "metadata_only": metadata_only}, indent=2))

    stdout_log = logs_dir / "stdout.log"; stderr_log = logs_dir / "stderr.log"
    result_status = "warning" if metadata_only else "succeeded"
    stdout_log.write_text(f"Temporal filtering: status={result_status}, filtered={filtered}\n")
    stderr_log.write_text("")

    (exec_dir / "manifest.json").write_text(json.dumps({"status": result_status, "metadata_only": metadata_only}))
    (exec_dir / "provenance.json").write_text(json.dumps({"sandbox_only": True, "metadata_only": metadata_only}))
    (exec_dir / "subject_status.json").write_text(json.dumps({"total": len(copied), "filtered": filtered, "metadata_only": metadata_only}))
    (exec_dir / "README.md").write_text(
        f"# Temporal Filtering Sandbox\nStatus: {result_status}. Filtered: {filtered}/{len(copied)}.\n")

    return FilteringSandboxExecutionResponse(
        ok=True, status=result_status, project_id=project_id, preprocessing_run_id=run_id,
        dry_run_id=request.dry_run_id, execution_id=exec_id, execution_dir=str(exec_dir),
        sandbox_input_dir=str(sandbox_in), sandbox_output_dir=str(sandbox_out),
        subjects_total=len(copied), subjects_succeeded=filtered,
        subjects_failed=len(copied) - filtered,
        filter_design_path=str(fd_path), stdout_log_path=str(stdout_log),
        stderr_log_path=str(stderr_log), manifest_path=str(exec_dir / "manifest.json"),
        provenance_path=str(exec_dir / "provenance.json"),
        subject_status_path=str(exec_dir / "subject_status.json"),
        warnings=warnings, next_actions=["Review filter results.", "Plan ALFF/ReHo dry-run."],
        safety_flags=filtering_safety_flags())
