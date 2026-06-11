"""ALFF/ReHo Sandbox Execution Service — Phase 5M. Python-only, metadata-first."""
from __future__ import annotations
import os, json, hashlib, shutil
from pathlib import Path

from src.backend.app.schemas.preprocessing_alff_reho_execution import (
    AlffRehoSandboxExecutionRequest, AlffRehoSandboxExecutionResponse,
    validate_alff_reho_env, alff_reho_exec_safety_flags,
)
from src.backend.app.services.mock_store import mock_store


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def run_alff_reho_sandbox_execution(
    project_id: str, run_id: str, request: AlffRehoSandboxExecutionRequest,
    *, project_dir: str = "", env: dict[str, str] | None = None
) -> AlffRehoSandboxExecutionResponse:
    eff_env = env or dict(os.environ)
    ok_flags, missing = validate_alff_reho_env(eff_env)
    if not ok_flags:
        return AlffRehoSandboxExecutionResponse(ok=False, status="disabled", project_id=project_id,
            blocking_issues=[f"Missing env flags: {missing}"], safety_flags=alff_reho_exec_safety_flags())

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")

    dry_dir = Path(effective_pd) / "preprocessing_runs" / run_id / "spm_dry_runs" / request.dry_run_id if effective_pd else None
    if not dry_dir or not dry_dir.exists():
        return AlffRehoSandboxExecutionResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=[f"Dry-run not found: {request.dry_run_id}"], safety_flags=alff_reho_exec_safety_flags())

    func_input = request.functional_input_dir or str(meta.get("current_functional_input_dir") or "")
    func_path = Path(func_input) if func_input else None
    if not func_path or not func_path.exists():
        return AlffRehoSandboxExecutionResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["Functional input not found."], safety_flags=alff_reho_exec_safety_flags())

    bold_files = [p for p in sorted(func_path.rglob("*.nii*")) if p.is_file() and ("bold" in p.name.lower() or "rest" in p.name.lower())]
    if not bold_files:
        return AlffRehoSandboxExecutionResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["No functional files found."], safety_flags=alff_reho_exec_safety_flags())

    exec_id = "ar-ex-" + hashlib.sha256(f"{project_id}:{run_id}:{_now_iso()}".encode()).hexdigest()[:10]
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
        designs.append({"subject": subj, "functional": str(dest / bf.name), "alff_computed": False, "reho_computed": False})

    # Attempt numerical ALFF if numpy/nibabel available
    metadata_only = True; computed = 0
    _NUMPY_OK = False
    try:
        import numpy as _np; import nibabel as _nib
        _NUMPY_OK = True
    except ImportError:
        warnings.append("numpy/nibabel not available; metadata-only execution.")

    if _NUMPY_OK:
        for cp, design in zip(copied, designs):
            try:
                img = _nib.load(str(cp))
                data = img.get_fdata()
                T = data.shape[-1] if data.ndim >= 4 else data.shape[0]
                if T < 5:
                    warnings.append(f"{design['subject']}: too few timepoints")
                    continue
                # ALFF: mean amplitude in time domain (low-freq band assumed by prior filtering)
                voxel_std = _np.std(data, axis=-1)
                alff_map = voxel_std  # simplified ALFF from filtered data
                alff_img = _nib.Nifti1Image(alff_map.astype(_np.float32), img.affine)
                alff_out = sandbox_out / design['subject'] / f"ALFF_{cp.name}"
                alff_out.parent.mkdir(parents=True, exist_ok=True)
                _nib.save(alff_img, str(alff_out))
                design['alff_computed'] = True; design['alff_output'] = str(alff_out)
                computed += 1; metadata_only = False
            except Exception as exc:
                warnings.append(f"{design['subject']}: {exc}")
    warnings.append("ReHo computation not yet implemented; metadata-only for ReHo.")

    mp_path = exec_dir / "metric_plan.json"
    mp_path.write_text(json.dumps({"designs": designs, "metadata_only": metadata_only}, indent=2))

    stdout_log = logs_dir / "stdout.log"; stderr_log = logs_dir / "stderr.log"
    result_status = "warning" if metadata_only else "succeeded"
    stdout_log.write_text(f"ALFF/ReHo: status={result_status}, computed={computed}\n"); stderr_log.write_text("")

    (exec_dir / "manifest.json").write_text(json.dumps({"status": result_status, "metadata_only": metadata_only}))
    (exec_dir / "provenance.json").write_text(json.dumps({"sandbox_only": True, "metadata_only": metadata_only}))
    (exec_dir / "subject_status.json").write_text(json.dumps({"total": len(copied), "computed": computed, "metadata_only": metadata_only}))
    (exec_dir / "README.md").write_text(f"# ALFF/ReHo Sandbox\nStatus: {result_status}. Computed: {computed}/{len(copied)}.\nReHo not implemented.\n")

    return AlffRehoSandboxExecutionResponse(
        ok=True, status=result_status, project_id=project_id, preprocessing_run_id=run_id,
        dry_run_id=request.dry_run_id, execution_id=exec_id, execution_dir=str(exec_dir),
        sandbox_input_dir=str(sandbox_in), sandbox_output_dir=str(sandbox_out),
        subjects_total=len(copied), subjects_succeeded=computed, subjects_failed=len(copied) - computed,
        metric_plan_path=str(mp_path), stdout_log_path=str(stdout_log),
        stderr_log_path=str(stderr_log), manifest_path=str(exec_dir / "manifest.json"),
        provenance_path=str(exec_dir / "provenance.json"),
        subject_status_path=str(exec_dir / "subject_status.json"),
        warnings=warnings, next_actions=["Review ALFF outputs.", "ReHo execution requires explicit implementation."],
        safety_flags=alff_reho_exec_safety_flags())
