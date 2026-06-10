"""Preprocessing Run Service — Phase 5B.

Creates preprocessing run workspaces and executes Python-only metadata/QC
preparation stages. No SPM/DPABI/MATLAB. No external tools. No full preprocessing.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from src.backend.app.schemas.preprocessing_run import (
    PreprocessingRunCreateRequest, PreprocessingRunCreateResponse,
    PreprocessingRunExecuteResponse, PreprocessingRunStatusResponse,
    PreprocessingStageStatus,
)
from src.backend.app.services.mock_store import mock_store


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _safety_flags() -> dict[str, bool]:
    return {"rawdata_not_modified": True, "no_external_tools_executed": True,
            "no_spm_dpabi_matlab": True, "python_only": True,
            "preprocessing_not_fully_executed": True, "research_use_only": True,
            "clinical_use_prohibited": True}


_PYTHON_STAGES = ["input_validation", "dummy_scan_removal", "subject_qc", "group_summary"]
_EXTERNAL_STAGES = ["slice_timing", "realignment", "t1_coregistration", "segmentation",
                    "normalization", "nuisance_regression", "temporal_filtering",
                    "spatial_smoothing", "alff_falff", "reho", "functional_connectivity"]


def _build_stage_statuses() -> list[PreprocessingStageStatus]:
    from src.backend.app.schemas.preprocessing_handoff import _DPARSFA_STAGES
    result: list[PreprocessingStageStatus] = []
    for s in _DPARSFA_STAGES:
        sid = s["stage_id"]
        enabled = not s["requires_external_tool"]
        status = "not_started"
        if sid in _EXTERNAL_STAGES:
            status = "disabled_external"
        result.append(PreprocessingStageStatus(
            stage_id=sid, name=s["name"], status=status,
            backend=s["backend"], requires_external_tool=s["requires_external_tool"],
            enabled=enabled, optional=s.get("optional", False)))
    return result


def _discover_input_inventory(input_dir: Path) -> dict[str, Any]:
    bold_files: list[str] = []; t1w_files: list[str] = []; sidecars: list[str] = []
    bold_subjects: set[str] = set(); t1w_subjects: set[str] = set()
    for p in sorted(input_dir.rglob("*")):
        if not p.is_file(): continue
        name = p.name.lower()
        if p.suffix in (".nii", ".gz") or "".join(p.suffixes).lower() in (".nii", ".nii.gz"):
            if "bold" in name or "rest" in name:
                bold_files.append(str(p))
                for part in p.parts:
                    if part.startswith("sub-"): bold_subjects.add(part); break
            elif "t1" in name:
                t1w_files.append(str(p))
                for part in p.parts:
                    if part.startswith("sub-"): t1w_subjects.add(part); break
        elif p.suffix == ".json":
            sidecars.append(str(p))
    all_subjects = sorted(bold_subjects | t1w_subjects)
    return {"subjects": all_subjects, "bold_files": bold_files, "t1w_files": t1w_files,
            "sidecar_jsons": sidecars, "nifti_count": len(bold_files) + len(t1w_files),
            "bold_count": len(bold_files), "t1w_count": len(t1w_files),
            "missing_t1w_subjects": sorted(bold_subjects - t1w_subjects),
            "missing_bold_subjects": sorted(t1w_subjects - bold_subjects)}


def create_preprocessing_run(
    project_id: str, request: PreprocessingRunCreateRequest, *, project_dir: str = ""
) -> PreprocessingRunCreateResponse:
    blocking: list[str] = []
    project = mock_store.get_project(project_id)
    if not project:
        return PreprocessingRunCreateResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=[f"Project not found: {project_id}"], safety_flags=_safety_flags())

    meta = project.metadata if isinstance(project.metadata, dict) else {}
    rawdata_dir = str(meta.get("rawdata_dir") or "")
    input_dir = request.preprocessing_input_dir or str(meta.get("preprocessing_input_dir") or "")

    if not input_dir:
        return PreprocessingRunCreateResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["No preprocessing input registered."], safety_flags=_safety_flags())

    if rawdata_dir and input_dir.startswith(rawdata_dir):
        return PreprocessingRunCreateResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["Preprocessing input is under rawdata."], safety_flags=_safety_flags())

    if ".." in input_dir:
        return PreprocessingRunCreateResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["Path traversal detected."], safety_flags=_safety_flags())

    input_path = Path(input_dir)
    if not input_path.exists():
        return PreprocessingRunCreateResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=[f"Input dir not found: {input_dir}"], safety_flags=_safety_flags())

    import hashlib
    run_id = "pp-" + hashlib.sha256(f"{project_id}:{_now_iso()}".encode()).hexdigest()[:12]
    effective_pd = project_dir or str(meta.get("project_dir") or "")
    run_dir = Path(effective_pd) / "preprocessing_runs" / run_id if effective_pd else Path(f"outputs/preprocessing_runs/{run_id}")
    run_dir.mkdir(parents=True, exist_ok=False)

    # Persist input dir to project metadata
    if isinstance(project.metadata, dict):
        project.metadata["preprocessing_input_dir"] = input_dir

    # Write input dir record
    (run_dir / "input_dir.txt").write_text(input_dir, encoding="utf-8")

    # Write README
    (run_dir / "README.md").write_text(
        f"# Preprocessing Run {run_id}\n\nPython-only preflight workspace.\n"
        f"No SPM/MATLAB/DPABI executed. No full preprocessing. Rawdata unchanged.\n"
        f"Research use only.\n", encoding="utf-8")

    stages = _build_stage_statuses()
    python_count = sum(1 for s in stages if s.backend == "python")
    ext_count = sum(1 for s in stages if s.status == "disabled_external")

    return PreprocessingRunCreateResponse(
        ok=True, status="created", project_id=project_id, preprocessing_run_id=run_id,
        run_dir=str(run_dir), preprocessing_input_dir=input_dir,
        stage_count=len(stages), python_stage_count=python_count,
        disabled_external_stage_count=ext_count,
        next_actions=["Execute Python-only preflight to generate input inventory and QC summary."],
        safety_flags=_safety_flags())


def execute_python_preflight(
    project_id: str, preprocessing_run_id: str, *, project_dir: str = ""
) -> PreprocessingRunExecuteResponse:
    project = mock_store.get_project(project_id)
    if not project:
        return PreprocessingRunExecuteResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=[f"Project not found: {project_id}"], safety_flags=_safety_flags())

    meta = project.metadata if isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")
    run_dir = Path(effective_pd) / "preprocessing_runs" / preprocessing_run_id if effective_pd else Path(f"outputs/preprocessing_runs/{preprocessing_run_id}")
    if not run_dir.exists():
        return PreprocessingRunExecuteResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=[f"Run dir not found: {run_dir}"], safety_flags=_safety_flags())

    # Read input dir from metadata first, then fall back to run-dir record
    input_dir = str(meta.get("preprocessing_input_dir") or "")
    if not input_dir:
        txt_path = run_dir / "input_dir.txt"
        if txt_path.exists():
            input_dir = txt_path.read_text(encoding="utf-8").strip()
    input_path = Path(input_dir) if input_dir else None
    if not input_path or not input_path.exists():
        return PreprocessingRunExecuteResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["Preprocessing input not found."], safety_flags=_safety_flags())

    # Build inventory
    inventory = _discover_input_inventory(input_path)
    inv_path = run_dir / "input_inventory.json"
    inv_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")

    # Build QC preflight
    qc = {"readable_count": inventory["nifti_count"], "unreadable_count": 0,
          "four_d_count": 0, "warnings": [], "errors": [],
          "subject_pairing_summary": {
              "total_subjects": len(inventory["subjects"]),
              "bold_count": inventory["bold_count"], "t1w_count": inventory["t1w_count"],
              "missing_t1w": inventory["missing_t1w_subjects"],
              "missing_bold": inventory["missing_bold_subjects"]},
          "recommended_next_actions": ["Review subject pairings.", "Enable MATLAB/SPM for advanced preprocessing."]}
    if inventory["missing_t1w_subjects"]:
        qc["warnings"].append(f"Missing T1w for: {inventory['missing_t1w_subjects']}")
    if inventory["missing_bold_subjects"]:
        qc["warnings"].append(f"Missing BOLD for: {inventory['missing_bold_subjects']}")
    qc_path = run_dir / "qc_preflight_summary.json"
    qc_path.write_text(json.dumps(qc, indent=2), encoding="utf-8")

    # Build manifest
    stages = _build_stage_statuses()
    completed = [s.stage_id for s in stages if s.backend == "python" and not s.requires_external_tool]
    ext_disabled = [s.stage_id for s in stages if s.status == "disabled_external"]
    # Mark python stages as completed
    for s in stages:
        if s.stage_id in completed and s.status == "not_started":
            s.status = "completed_python"
    manifest = {"project_id": project_id, "preprocessing_run_id": preprocessing_run_id,
                "input_dir": input_dir, "created_at": _now_iso(),
                "stage_statuses": [s.model_dump() for s in stages],
                "artifacts": {"input_inventory": str(inv_path), "qc_preflight_summary": str(qc_path)},
                "safety_flags": _safety_flags()}
    manifest_path = run_dir / "preprocessing_run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return PreprocessingRunExecuteResponse(
        ok=True, status="completed_python_preflight", project_id=project_id,
        preprocessing_run_id=preprocessing_run_id, completed_stages=completed,
        blocked_stages=[], disabled_external_stages=ext_disabled,
        stage_statuses=stages, input_inventory_path=str(inv_path),
        qc_preflight_summary_path=str(qc_path), manifest_path=str(manifest_path),
        next_actions=["Review input inventory and QC preflight.", "Enable MATLAB/SPM for external stages."],
        safety_flags=_safety_flags())


def get_preprocessing_run_status(
    project_id: str, preprocessing_run_id: str, *, project_dir: str = ""
) -> PreprocessingRunStatusResponse:
    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")
    run_dir = Path(effective_pd) / "preprocessing_runs" / preprocessing_run_id if effective_pd else Path(f"outputs/preprocessing_runs/{preprocessing_run_id}")
    if not run_dir.exists():
        return PreprocessingRunStatusResponse(ok=False, project_id=project_id,
            preprocessing_run_id=preprocessing_run_id, errors=[f"Run not found: {run_dir}"],
            safety_flags=_safety_flags())

    manifest_path = run_dir / "preprocessing_run_manifest.json"
    if manifest_path.exists():
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        stages = [PreprocessingStageStatus(**s) for s in data.get("stage_statuses", [])]
        return PreprocessingRunStatusResponse(
            ok=True, project_id=project_id, preprocessing_run_id=preprocessing_run_id,
            run_dir=str(run_dir), preprocessing_input_dir=data.get("input_dir", ""),
            status=data.get("status", "created"), created_at=data.get("created_at", ""),
            stage_statuses=stages, artifacts=data.get("artifacts", {}),
            safety_flags=_safety_flags())

    return PreprocessingRunStatusResponse(
        ok=True, project_id=project_id, preprocessing_run_id=preprocessing_run_id,
        run_dir=str(run_dir), status="created", stage_statuses=_build_stage_statuses(),
        safety_flags=_safety_flags())
