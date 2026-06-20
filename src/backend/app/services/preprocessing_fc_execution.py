"""FC Sandbox Execution Service — Phase 5N. Python-only, atlas-optional."""
from __future__ import annotations
import os, json, hashlib, shutil
from pathlib import Path

from src.backend.app.schemas.preprocessing_fc_execution import (
    FcSandboxExecutionRequest, FcSandboxExecutionResponse,
    validate_fc_env, fc_exec_safety_flags,
)
from src.backend.app.services.mock_store import mock_store


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def run_fc_sandbox_execution(
    project_id: str, run_id: str, request: FcSandboxExecutionRequest,
    *, project_dir: str = "", env: dict[str, str] | None = None
) -> FcSandboxExecutionResponse:
    eff_env = env or dict(os.environ)
    ok_flags, missing = validate_fc_env(eff_env)
    if not ok_flags:
        return FcSandboxExecutionResponse(ok=False, status="disabled", project_id=project_id,
            blocking_issues=[f"Missing env flags: {missing}"], safety_flags=fc_exec_safety_flags())

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")

    dry_dir = Path(effective_pd) / "preprocessing_runs" / run_id / "spm_dry_runs" / request.dry_run_id if effective_pd else None
    if not dry_dir or not dry_dir.exists():
        return FcSandboxExecutionResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=[f"Dry-run not found: {request.dry_run_id}"], safety_flags=fc_exec_safety_flags())

    func_input = request.functional_input_dir or str(meta.get("current_functional_input_dir") or "")
    func_path = Path(func_input) if func_input else None
    if not func_path or not func_path.exists():
        return FcSandboxExecutionResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["Functional input not found."], safety_flags=fc_exec_safety_flags())

    bold_files = [p for p in sorted(func_path.rglob("*.nii*")) if p.is_file() and ("bold" in p.name.lower() or "rest" in p.name.lower())]
    if not bold_files:
        return FcSandboxExecutionResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["No functional files found."], safety_flags=fc_exec_safety_flags())

    exec_id = "fc-ex-" + hashlib.sha256(f"{project_id}:{run_id}:{_now_iso()}".encode()).hexdigest()[:10]
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
        designs.append({"subject": subj, "functional": str(dest / bf.name), "fc_computed": False})

    # FC execution: ROI-based Pearson via the unified compute kernel.
    # The kernel requires a 4D BOLD volume and a matching 3D atlas. When no
    # external atlas is available we synthesize one via ``_generate_atlas``
    # and record that fact in provenance so the matrix is never mistaken for
    # an atlas-grounded result.
    metadata_only = True; computed = 0; matrix_count = 0
    fc_status = "metadata_only"
    _NUMPY_OK = False
    try:
        import numpy as _np; import nibabel as _nib
        _NUMPY_OK = True
    except ImportError:
        warnings.append("numpy/nibabel not available; metadata-only FC execution.")

    if _NUMPY_OK:
        from src.backend.app.tools.functional_connectivity_compute import (
            compute_fc_backend, _generate_atlas,
        )
        for cp, design in zip(copied, designs):
            try:
                img = _nib.load(str(cp))
                data = img.get_fdata()
                if data.ndim < 4:
                    data = data[..., None]
                T = data.shape[-1]
                if T < 10:
                    warnings.append(f"{design['subject']}: too few timepoints ({T})")
                    continue
                spatial_shape = tuple(int(s) for s in data.shape[:3])
                atlas, atlas_defs = _generate_atlas(spatial_shape, roi_count=8)
                atlas_source = "synthetic_x_chunk"
                result = compute_fc_backend(data, atlas, generate_seed_map=False, prefer_gpu=True)
                if not result.get("ok") or result.get("correlation_matrix") is None:
                    warnings.append(f"{design['subject']}: FC kernel returned no matrix: {result.get('errors')}")
                    continue
                corr = _np.asarray(result["correlation_matrix"]).astype(_np.float32)
                fz = _np.asarray(result["fisher_z_matrix"]).astype(_np.float32)
                out_path = sandbox_out / design['subject']
                out_path.mkdir(parents=True, exist_ok=True)
                corr_npy = out_path / f"sub-{design['subject']}_desc-fc_matrix.npy"
                corr_tsv = out_path / f"sub-{design['subject']}_desc-fc_matrix.tsv"
                fz_npy = out_path / f"sub-{design['subject']}_desc-fisherz_matrix.npy"
                _np.save(corr_npy, corr)
                _np.savetxt(corr_tsv, corr, delimiter="\t", fmt="%.6f")
                _np.save(fz_npy, fz)
                roi_labels = [{"label": d["label"], "name": d["name"]} for d in atlas_defs]
                (out_path / f"sub-{design['subject']}_desc-fc_labels.json").write_text(
                    json.dumps({"roi_count": len(roi_labels), "labels": roi_labels}, indent=2))
                (out_path / f"sub-{design['subject']}_desc-fc_provenance.json").write_text(
                    json.dumps({"method": "pearson", "fisher_z": True, "atlas_source": atlas_source,
                                "backend": result.get("backend"), "roi_count": int(result.get("roi_count", 0)),
                                "timepoints": int(result.get("timepoints", T)),
                                "input_shape": [int(s) for s in data.shape]}, indent=2))
                design['fc_computed'] = True; design['fc_output'] = str(corr_npy)
                design['fisher_z_output'] = str(fz_npy)
                computed += 1; matrix_count += 1; metadata_only = False; fc_status = "numerically_computed"
            except Exception as exc:
                warnings.append(f"{design['subject']}: {exc}")

    fp_path = exec_dir / "fc_plan.json"
    fp_path.write_text(json.dumps({"designs": designs, "metadata_only": metadata_only,
                                   "fc_status": fc_status}, indent=2))

    stdout_log = logs_dir / "stdout.log"; stderr_log = logs_dir / "stderr.log"
    result_status = "warning" if metadata_only else "succeeded"
    stdout_log.write_text(f"FC execution: status={result_status}, computed={computed}\n"); stderr_log.write_text("")

    (exec_dir / "manifest.json").write_text(json.dumps({
        "status": result_status, "metadata_only": metadata_only,
        "fc": {"computed": not metadata_only, "status": fc_status, "matrix_count": matrix_count}}))
    (exec_dir / "provenance.json").write_text(json.dumps({"sandbox_only": True, "metadata_only": metadata_only,
                                                          "fc_status": fc_status}))
    (exec_dir / "subject_status.json").write_text(json.dumps({"total": len(copied), "computed": computed,
                                                              "metadata_only": metadata_only, "fc_status": fc_status}))
    (exec_dir / "README.md").write_text(f"# FC Sandbox\nStatus: {result_status}. Computed: {computed}/{len(copied)}.\n")

    return FcSandboxExecutionResponse(
        ok=True, status=result_status, project_id=project_id, preprocessing_run_id=run_id,
        dry_run_id=request.dry_run_id, execution_id=exec_id, execution_dir=str(exec_dir),
        sandbox_input_dir=str(sandbox_in), sandbox_output_dir=str(sandbox_out),
        subjects_total=len(copied), subjects_succeeded=computed, subjects_failed=len(copied) - computed,
        fc_plan_path=str(fp_path), stdout_log_path=str(stdout_log),
        stderr_log_path=str(stderr_log), manifest_path=str(exec_dir / "manifest.json"),
        provenance_path=str(exec_dir / "provenance.json"),
        subject_status_path=str(exec_dir / "subject_status.json"),
        fc_computed=(not metadata_only), fc_status=fc_status, fc_matrix_count=matrix_count,
        warnings=warnings, next_actions=["Review FC matrices.", "Group analysis requires explicit opt-in."],
        safety_flags=fc_exec_safety_flags())
