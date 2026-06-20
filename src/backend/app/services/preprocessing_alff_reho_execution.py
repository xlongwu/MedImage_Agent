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

    # Numerical ALFF/fALFF via the unified FFT kernel and ReHo via the unified
    # KCC kernel. No inline math: both metrics delegate to tools/*_compute.py.
    metadata_only = True; computed = 0
    alff_status = "metadata_only"; falff_status = "metadata_only"; reho_status = "metadata_only"
    any_alff = False; any_falff = False; any_reho = False
    _NUMPY_OK = False
    try:
        import numpy as _np; import nibabel as _nib
        _NUMPY_OK = True
    except ImportError:
        warnings.append("numpy/nibabel not available; metadata-only execution.")

    if _NUMPY_OK:
        from src.backend.app.tools.alff_compute import compute_alff_backend
        from src.backend.app.tools.reho_compute import compute_reho_backend

        def _read_tr(bold_path: Path) -> float:
            """TR in seconds: prefer BIDS JSON sidecar, else default 2.0s."""
            sidecar = bold_path.with_suffix("")
            for ext in (".json",):
                cand = Path(str(sidecar) + ext)
                if cand.exists():
                    try:
                        sc = json.loads(cand.read_text())
                        if isinstance(sc, dict) and isinstance(sc.get("RepetitionTime"), (int, float)):
                            return float(sc["RepetitionTime"])
                    except Exception:
                        pass
            return 2.0

        for cp, design in zip(copied, designs):
            try:
                img = _nib.load(str(cp))
                data = img.get_fdata()
                if data.ndim < 4:
                    data = data[..., None]
                T = data.shape[-1]
                if T < 8:
                    warnings.append(f"{design['subject']}: too few timepoints ({T})")
                    continue
                tr = _read_tr(cp)
                freq_band = (0.01, 0.08)
                alff_res = compute_alff_backend(data, tr=tr, freq_band=freq_band, prefer_gpu=True)
                out_path = sandbox_out / design['subject']
                out_path.mkdir(parents=True, exist_ok=True)
                if alff_res.get("ok") and alff_res.get("alff") is not None:
                    alff_map = _np.asarray(alff_res["alff"]).astype(_np.float32)
                    falff_map = _np.asarray(alff_res["falff"]).astype(_np.float32)
                    alff_out = out_path / f"sub-{design['subject']}_desc-alff_map.nii.gz"
                    falff_out = out_path / f"sub-{design['subject']}_desc-falff_map.nii.gz"
                    _nib.save(_nib.Nifti1Image(alff_map, img.affine, img.header), str(alff_out))
                    _nib.save(_nib.Nifti1Image(falff_map, img.affine, img.header), str(falff_out))
                    (out_path / f"sub-{design['subject']}_desc-alff_provenance.json").write_text(
                        json.dumps({"tr": tr, "freq_band": list(freq_band),
                                    "algorithm": "fft", "backend": alff_res.get("backend"),
                                    "input_shape": [int(s) for s in data.shape]}, indent=2))
                    design['alff_computed'] = True; design['alff_output'] = str(alff_out)
                    design['falff_computed'] = True; design['falff_output'] = str(falff_out)
                    any_alff = True; any_falff = True
                    computed += 1; metadata_only = False
                else:
                    warnings.append(f"{design['subject']}: ALFF kernel failed: {alff_res.get('errors')}")

                # ReHo via unified KCC kernel (27-neighborhood, no GM mask in sandbox).
                reho_res = compute_reho_backend(data, neighborhood=27, prefer_gpu=True)
                if reho_res.get("ok") and reho_res.get("reho") is not None:
                    reho_map = _np.asarray(reho_res["reho"]).astype(_np.float32)
                    reho_out = out_path / f"sub-{design['subject']}_desc-reho_map.nii.gz"
                    _nib.save(_nib.Nifti1Image(reho_map, img.affine, img.header), str(reho_out))
                    (out_path / f"sub-{design['subject']}_desc-reho_provenance.json").write_text(
                        json.dumps({"neighborhood": 27, "method": "kcc",
                                    "backend": reho_res.get("backend"),
                                    "valid_voxel_count": int(reho_res.get("valid_voxel_count", 0)),
                                    "input_shape": [int(s) for s in data.shape]}, indent=2))
                    design['reho_computed'] = True; design['reho_output'] = str(reho_out)
                    any_reho = True
                else:
                    warnings.append(f"{design['subject']}: ReHo kernel failed: {reho_res.get('errors')}")
            except Exception as exc:
                warnings.append(f"{design['subject']}: {exc}")

    alff_status = "numerically_computed" if any_alff else alff_status
    falff_status = "numerically_computed" if any_falff else falff_status
    reho_status = "numerically_implemented_unvalidated" if any_reho else reho_status

    mp_path = exec_dir / "metric_plan.json"
    mp_path.write_text(json.dumps({"designs": designs, "metadata_only": metadata_only,
                                   "alff_status": alff_status, "reho_status": reho_status}, indent=2))

    stdout_log = logs_dir / "stdout.log"; stderr_log = logs_dir / "stderr.log"
    result_status = "warning" if metadata_only else "succeeded"
    stdout_log.write_text(f"ALFF/ReHo: status={result_status}, computed={computed}\n"); stderr_log.write_text("")

    (exec_dir / "manifest.json").write_text(json.dumps({
        "status": result_status, "metadata_only": metadata_only,
        "alff": {"computed": any_alff, "status": alff_status},
        "falff": {"computed": any_falff, "status": falff_status},
        "reho": {"computed": any_reho, "status": reho_status,
                  "note": "numerically_implemented_unvalidated: pending independent reference validation"}}))
    (exec_dir / "provenance.json").write_text(json.dumps({
        "sandbox_only": True, "metadata_only": metadata_only,
        "alff_status": alff_status, "reho_status": reho_status,
        "kernels": ["tools/alff_compute.py::compute_alff_backend",
                    "tools/reho_compute.py::compute_reho_backend"]}))
    (exec_dir / "subject_status.json").write_text(json.dumps(
        {"total": len(copied), "computed": computed, "metadata_only": metadata_only,
         "alff_status": alff_status, "reho_status": reho_status}))
    (exec_dir / "README.md").write_text(
        f"# ALFF/ReHo Sandbox\nStatus: {result_status}. Computed: {computed}/{len(copied)}.\n"
        f"ALFF/fALFF: {alff_status}. ReHo: {reho_status}.\n")

    return AlffRehoSandboxExecutionResponse(
        ok=True, status=result_status, project_id=project_id, preprocessing_run_id=run_id,
        dry_run_id=request.dry_run_id, execution_id=exec_id, execution_dir=str(exec_dir),
        sandbox_input_dir=str(sandbox_in), sandbox_output_dir=str(sandbox_out),
        subjects_total=len(copied), subjects_succeeded=computed, subjects_failed=len(copied) - computed,
        metric_plan_path=str(mp_path), stdout_log_path=str(stdout_log),
        stderr_log_path=str(stderr_log), manifest_path=str(exec_dir / "manifest.json"),
        provenance_path=str(exec_dir / "provenance.json"),
        subject_status_path=str(exec_dir / "subject_status.json"),
        alff_computed=any_alff, alff_status=alff_status, falff_computed=any_falff,
        reho_computed=any_reho, reho_status=reho_status,
        warnings=warnings, next_actions=["Review ALFF/fALFF/ReHo maps.", "ReHo remains pending independent reference validation."],
        safety_flags=alff_reho_exec_safety_flags())
