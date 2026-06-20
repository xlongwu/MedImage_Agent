"""ALFF/ReHo Sandbox Execution Service — Phase 5M. Python-only, metadata-first."""
from __future__ import annotations
import os, json, hashlib, shutil
from pathlib import Path

from src.backend.app.schemas.preprocessing_alff_reho_execution import (
    AlffRehoSandboxExecutionRequest, AlffRehoSandboxExecutionResponse,
    validate_alff_reho_env, alff_reho_exec_safety_flags,
)
from src.backend.app.services.mock_store import mock_store


def bids_sidecar_for(path: Path) -> Path | None:
    """Return the BIDS JSON sidecar path for a NIfTI file, or None.

    Correctly strips both .nii.gz and .nii extensions per BIDS spec.
    For 'sub-001_task-rest_bold.nii.gz' returns 'sub-001_task-rest_bold.json'.
    """
    name = path.name
    if name.endswith(".nii.gz"):
        stem = name[:-7]
    elif name.endswith(".nii"):
        stem = name[:-4]
    else:
        return None
    return path.parent / f"{stem}.json"


def bids_prefix_from_path(path: Path) -> str:
    """Extract a unique BIDS entity prefix from a NIfTI file path.

    Returns a string like 'sub-001' or 'sub-001_ses-01_task-rest_run-1'
    containing all BIDS key-value pairs found in the filename. This ensures
    multi-session / multi-run inputs produce non-colliding output paths.
    """
    name = path.name
    if name.endswith(".nii.gz"):
        stem = name[:-7]
    elif name.endswith(".nii"):
        stem = name[:-4]
    else:
        stem = name
    # Remove trailing descriptor like _bold, _T1w, etc. — keep only entity pairs
    parts = stem.split("_")
    entities = [p for p in parts if "-" in p]
    if not entities:
        return path.stem
    return "_".join(entities)


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
    files_discovered = len(bold_files)
    files_selected = min(files_discovered, 10)
    dataset_complete = files_discovered <= 10
    if not dataset_complete:
        warnings.append(
            f"Found {files_discovered} BOLD files but only processing first 10 "
            f"(preview mode). Set a higher limit or split the dataset.")
    for bf in bold_files[:10]:
        subj = "sub-unknown"
        for part in bf.parts:
            if part.startswith("sub-"): subj = part; break
        bids_prefix = bids_prefix_from_path(bf)
        dest = sandbox_in / bids_prefix; dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bf, dest / bf.name)
        # Copy BIDS JSON sidecar alongside NIfTI so TR can be read correctly.
        sidecar = bids_sidecar_for(bf)
        if sidecar and sidecar.exists():
            shutil.copy2(sidecar, dest / sidecar.name)
        copied.append(dest / bf.name)
        designs.append({"subject": subj, "bids_prefix": bids_prefix,
                        "functional": str(dest / bf.name),
                        "alff_computed": False, "falff_computed": False,
                        "reho_computed": False, "tr_source": "unknown"})

    # Numerical ALFF/fALFF via the unified FFT kernel and ReHo via the unified
    # KCC kernel. No inline math: both metrics delegate to tools/*_compute.py.
    metadata_only = True
    alff_status = "metadata_only"; falff_status = "metadata_only"; reho_status = "metadata_only"
    reho_validation_status = "unvalidated"; reho_backend = "none"
    any_alff = False; any_falff = False; any_reho = False
    alff_succeeded = 0; reho_succeeded = 0
    subjects_complete = 0; subjects_partial = 0
    _NUMPY_OK = False
    try:
        import numpy as _np; import nibabel as _nib
        _NUMPY_OK = True
    except ImportError:
        warnings.append("numpy/nibabel not available; metadata-only execution.")

    if _NUMPY_OK:
        from src.backend.app.tools.alff_compute import compute_alff_backend
        from src.backend.app.tools.reho_compute import compute_reho_backend

        def _read_tr(bold_path: Path) -> tuple[float, str]:
            """TR in seconds: prefer BIDS JSON sidecar, else default 2.0s.

            Returns (tr_value, tr_source) where tr_source is "bids_json"
            or "default". A "default" source means the sidecar was missing
            or invalid; callers record this in provenance and warn.
            """
            sidecar = bids_sidecar_for(bold_path)
            if sidecar and sidecar.exists():
                try:
                    sc = json.loads(sidecar.read_text())
                    if isinstance(sc, dict) and isinstance(sc.get("RepetitionTime"), (int, float)):
                        return float(sc["RepetitionTime"]), "bids_json"
                except Exception:
                    pass
            return 2.0, "default"

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
                tr, tr_source = _read_tr(cp)
                design['tr_source'] = tr_source
                if tr_source == "default":
                    warnings.append(
                        f"{design['subject']}: TR sidecar not found or invalid; "
                        f"falling back to default TR=2.0s")
                freq_band = (0.01, 0.08)
                alff_res = compute_alff_backend(data, tr=tr, freq_band=freq_band, prefer_gpu=True)
                out_path = sandbox_out / design['bids_prefix']
                out_path.mkdir(parents=True, exist_ok=True)
                if alff_res.get("ok") and alff_res.get("alff") is not None:
                    alff_map = _np.asarray(alff_res["alff"]).astype(_np.float32)
                    falff_map = _np.asarray(alff_res["falff"]).astype(_np.float32)
                    alff_out = out_path / f"{design['subject']}_desc-alff_map.nii.gz"
                    falff_out = out_path / f"{design['subject']}_desc-falff_map.nii.gz"
                    _nib.save(_nib.Nifti1Image(alff_map, img.affine, img.header), str(alff_out))
                    _nib.save(_nib.Nifti1Image(falff_map, img.affine, img.header), str(falff_out))
                    (out_path / f"{design['subject']}_desc-alff_provenance.json").write_text(
                        json.dumps({"tr": tr, "tr_source": tr_source,
                                    "freq_band": list(freq_band),
                                    "algorithm": "fft", "backend": alff_res.get("backend"),
                                    "input_shape": [int(s) for s in data.shape]}, indent=2))
                    design['alff_computed'] = True; design['alff_output'] = str(alff_out)
                    design['falff_computed'] = True; design['falff_output'] = str(falff_out)
                    any_alff = True; any_falff = True
                    alff_succeeded += 1; metadata_only = False
                else:
                    warnings.append(f"{design['subject']}: ALFF kernel failed: {alff_res.get('errors')}")

                # ReHo via unified KCC kernel (27-neighborhood, no GM mask in sandbox).
                # ReHo: use CPU path (prefer_gpu=False) because the GPU
                # implementation does not yet handle ties correction. Ties
                # are common in real fMRI data (background zeros, quantized
                # signals, scrubbed timepoints) and would produce silently
                # incorrect KCC values on GPU.
                reho_res = compute_reho_backend(data, neighborhood=27, prefer_gpu=False)
                if reho_res.get("ok") and reho_res.get("reho") is not None:
                    reho_map = _np.asarray(reho_res["reho"]).astype(_np.float32)
                    reho_out = out_path / f"{design['subject']}_desc-reho_map.nii.gz"
                    _nib.save(_nib.Nifti1Image(reho_map, img.affine, img.header), str(reho_out))
                    (out_path / f"{design['subject']}_desc-reho_provenance.json").write_text(
                        json.dumps({"neighborhood": 27, "method": "kcc",
                                    "backend": reho_res.get("backend"),
                                    "valid_voxel_count": int(reho_res.get("valid_voxel_count", 0)),
                                    "input_shape": [int(s) for s in data.shape]}, indent=2))
                    design['reho_computed'] = True; design['reho_output'] = str(reho_out)
                    any_reho = True; reho_succeeded += 1; metadata_only = False
                else:
                    warnings.append(f"{design['subject']}: ReHo kernel failed: {reho_res.get('errors')}")
            except Exception as exc:
                warnings.append(f"{design['subject']}: {exc}")

    alff_status = "numerically_computed" if any_alff else alff_status
    falff_status = "numerically_computed" if any_falff else falff_status
    reho_status = "validated" if any_reho else reho_status
    if any_reho:
        reho_validation_status = "golden_validated"
        reho_backend = "cpu-numpy"

    # Per-subject aggregation: classify each subject as complete/partial/failed.
    for d in designs:
        metrics_ok = sum([d.get("alff_computed", False),
                          d.get("falff_computed", False),
                          d.get("reho_computed", False)])
        if metrics_ok == 3:
            subjects_complete += 1
        elif metrics_ok > 0:
            subjects_partial += 1

    # Aggregate TR source across all subjects: "bids_json" if all used sidecar,
    # "default" if all fell back, "mixed" if some of each.
    tr_sources = {d.get("tr_source", "unknown") for d in designs}
    if tr_sources == {"bids_json"}:
        agg_tr_source = "bids_json"
    elif tr_sources == {"default"}:
        agg_tr_source = "default"
    else:
        agg_tr_source = "mixed"

    total_subjects = len(copied)
    if total_subjects > 0 and subjects_complete == total_subjects:
        # All metrics succeeded for all subjects. If TR came from default
        # fallback (not BIDS sidecar), frequency axis is uncertain → downgrade
        # to "partial" since ALFF/fALFF values may be inaccurate.
        if agg_tr_source == "default":
            result_status = "partial"
            warnings.append(
                "Overall status downgraded to 'partial' because TR source is "
                "'default' (BIDS sidecar not found). ALFF/fALFF frequency axis "
                "may be inaccurate.")
        else:
            result_status = "succeeded"
    elif subjects_complete > 0 or subjects_partial > 0:
        result_status = "partial"
    else:
        result_status = "warning"

    # If only a subset of discovered files was processed (preview mode),
    # downgrade 'succeeded' to 'partial' — per AGENTS Scientific Computing
    # Contract, subset processing must not claim full-dataset completion.
    if not dataset_complete and result_status == "succeeded":
        result_status = "partial"
        warnings.append(
            f"Overall status downgraded to 'partial' because only {files_selected} "
            f"of {files_discovered} discovered BOLD files were processed (preview mode).")

    mp_path = exec_dir / "metric_plan.json"
    mp_path.write_text(json.dumps({"designs": designs, "metadata_only": metadata_only,
                                   "alff_status": alff_status, "reho_status": reho_status,
                                   "reho_validation_status": reho_validation_status,
                                   "reho_backend": reho_backend,
                                   "subjects_complete": subjects_complete,
                                   "subjects_partial": subjects_partial}, indent=2))

    stdout_log = logs_dir / "stdout.log"; stderr_log = logs_dir / "stderr.log"
    stdout_log.write_text(
        f"ALFF/ReHo: status={result_status}, complete={subjects_complete}, "
        f"partial={subjects_partial}, failed={total_subjects - subjects_complete - subjects_partial}, "
        f"alff_succeeded={alff_succeeded}, reho_succeeded={reho_succeeded}\n")
    stderr_log.write_text("")

    (exec_dir / "manifest.json").write_text(json.dumps({
        "status": result_status, "metadata_only": metadata_only,
        "subjects": {"total": total_subjects, "complete": subjects_complete,
                     "partial": subjects_partial,
                     "failed": total_subjects - subjects_complete - subjects_partial},
        "alff": {"computed": any_alff, "status": alff_status, "subject_count": alff_succeeded},
        "falff": {"computed": any_falff, "status": falff_status, "subject_count": alff_succeeded},
        "reho": {"computed": any_reho, "subject_count": reho_succeeded,
                  "execution_status": reho_status,
                  "validation_status": reho_validation_status,
                  "backend": reho_backend,
                  "external_reference_validated": False,
                  "gpu_validated": False,
                  "note": "CPU Kendall's W implementation is golden validated and agrees with an independent in-repository NumPy reference. External reference validation remains pending. GPU backend remains unvalidated."}}))
    (exec_dir / "provenance.json").write_text(json.dumps({
        "sandbox_only": True, "metadata_only": metadata_only,
        "alff_status": alff_status, "reho_status": reho_status,
        "reho_validation_status": reho_validation_status, "reho_backend": reho_backend,
        "tr_source": agg_tr_source,
        "dataset_selection": {"files_discovered": files_discovered,
                              "files_selected": files_selected,
                              "selection_policy": "first_10_preview" if not dataset_complete else "all",
                              "dataset_complete": dataset_complete},
        "kernels": ["tools/alff_compute.py::compute_alff_backend",
                    "tools/reho_compute.py::compute_reho_backend"]}))
    (exec_dir / "subject_status.json").write_text(json.dumps(
        {"total": total_subjects, "complete": subjects_complete,
         "partial": subjects_partial,
         "failed": total_subjects - subjects_complete - subjects_partial,
         "metadata_only": metadata_only,
         "alff_succeeded": alff_succeeded, "reho_succeeded": reho_succeeded,
         "alff_status": alff_status, "reho_status": reho_status,
         "reho_validation_status": reho_validation_status, "reho_backend": reho_backend,
         "per_subject": [{"subject": d["subject"],
                          "alff_computed": d.get("alff_computed", False),
                          "falff_computed": d.get("falff_computed", False),
                          "reho_computed": d.get("reho_computed", False),
                          "tr_source": d.get("tr_source", "unknown")}
                         for d in designs]}))
    (exec_dir / "README.md").write_text(
        f"# ALFF/ReHo Sandbox\nStatus: {result_status}. "
        f"Complete: {subjects_complete}/{total_subjects}, Partial: {subjects_partial}.\n"
        f"ALFF/fALFF: {alff_status} ({alff_succeeded} subjects). "
        f"ReHo: {reho_status} ({reho_succeeded} subjects).\n")

    return AlffRehoSandboxExecutionResponse(
        ok=True, status=result_status, project_id=project_id, preprocessing_run_id=run_id,
        dry_run_id=request.dry_run_id, execution_id=exec_id, execution_dir=str(exec_dir),
        sandbox_input_dir=str(sandbox_in), sandbox_output_dir=str(sandbox_out),
        subjects_total=total_subjects, subjects_succeeded=subjects_complete,
        subjects_failed=total_subjects - subjects_complete - subjects_partial,
        subjects_partial=subjects_partial,
        files_discovered=files_discovered, files_selected=files_selected,
        dataset_complete=dataset_complete,
        metric_plan_path=str(mp_path), stdout_log_path=str(stdout_log),
        stderr_log_path=str(stderr_log), manifest_path=str(exec_dir / "manifest.json"),
        provenance_path=str(exec_dir / "provenance.json"),
        subject_status_path=str(exec_dir / "subject_status.json"),
        alff_computed=any_alff, alff_status=alff_status, falff_computed=any_falff,
        reho_computed=any_reho, reho_status=reho_status,
        reho_validation_status=reho_validation_status, reho_backend=reho_backend,
        tr_source=agg_tr_source,
        warnings=warnings, next_actions=["Review ALFF/fALFF/ReHo maps.", "External ReHo validation and GPU ties-correct implementation remain pending."],
        safety_flags=alff_reho_exec_safety_flags())
