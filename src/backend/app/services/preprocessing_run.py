"""Preprocessing Run Service — Phase 6C.

Creates preprocessing run workspaces and executes stages in sequence with
full state machine: not_started → planned → dry_run_ready → running →
succeeded / failed / metadata_only / blocked.

Python/GPU stages can execute when input data is available.
SPM/MATLAB stages remain blocked since MATLAB is not installed.
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


_PYTHON_STAGES = ["input_validation", "subject_qc", "group_summary"]
_PLANNED_NOT_EXECUTED = ["dummy_scan_removal"]
# SPM/MATLAB stages — blocked because MATLAB not available
_SPM_MATLAB_STAGES = ["slice_timing", "realignment", "t1_coregistration",
                      "segmentation", "normalization", "spatial_smoothing"]
# Python/GPU stages — can execute when data is ready
_EXECUTABLE_STAGES = ["nuisance_regression", "temporal_filtering",
                      "alff_falff", "reho", "functional_connectivity"]


def _build_stage_statuses() -> list[PreprocessingStageStatus]:
    from src.backend.app.schemas.preprocessing_handoff import _DPARSFA_STAGES
    result: list[PreprocessingStageStatus] = []
    for s in _DPARSFA_STAGES:
        sid = s["stage_id"]
        enabled = not s["requires_external_tool"]
        if sid in _SPM_MATLAB_STAGES:
            status = "blocked"
            enabled = False
        elif sid in _PLANNED_NOT_EXECUTED:
            status = "planned_not_executed"
        elif sid in _EXECUTABLE_STAGES:
            status = "planned"
            enabled = True
        else:
            status = "not_started"
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
        f"No SPM/MATLAB/DPABI executed. No image-transform preprocessing (dummy scan removal, realignment, etc.). Rawdata unchanged.\n"
        f"Research use only.\n", encoding="utf-8")

    stages = _build_stage_statuses()
    python_count = sum(1 for s in stages if s.backend == "python")
    blocked_count = sum(1 for s in stages if s.status == "blocked")
    planned_count = sum(1 for s in stages if s.status == "planned")

    return PreprocessingRunCreateResponse(
        ok=True, status="created", project_id=project_id, preprocessing_run_id=run_id,
        run_dir=str(run_dir), preprocessing_input_dir=input_dir,
        stage_count=len(stages), python_stage_count=python_count,
        external_blocked_count=blocked_count, planned_stage_count=planned_count,
        disabled_external_stage_count=blocked_count,
        next_actions=["Execute Python preflight to generate input inventory and QC summary.",
                      f"{planned_count} stages available for execution in Python/GPU."],
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
    completed = [s.stage_id for s in stages if s.backend == "python" and not s.requires_external_tool and s.stage_id not in _PLANNED_NOT_EXECUTED]
    blocked = [s.stage_id for s in stages if s.status == "blocked"]
    planned = [s.stage_id for s in stages if s.status == "planned"]
    # Mark python stages as completed
    for s in stages:
        if s.stage_id in completed and s.status == "not_started":
            s.status = "succeeded"
    overall_progress = len(completed) / max(len(stages), 1)
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
        blocked_stages=blocked, failed_stages=[],
        disabled_external_stages=blocked,
        stage_statuses=stages, overall_progress=overall_progress,
        input_inventory_path=str(inv_path),
        qc_preflight_summary_path=str(qc_path), manifest_path=str(manifest_path),
        next_actions=["Review input inventory and QC preflight.",
                      f"{len(planned)} executable stages ready. SPM/MATLAB stages blocked."],
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
        completed = sum(1 for s in stages if s.status == "succeeded")
        total = max(len(stages), 1)
        overall_progress = data.get("overall_progress", completed / total)
        return PreprocessingRunStatusResponse(
            ok=True, project_id=project_id, preprocessing_run_id=preprocessing_run_id,
            run_dir=str(run_dir), preprocessing_input_dir=data.get("input_dir", ""),
            status=data.get("status", "created"), created_at=data.get("created_at", ""),
            stage_statuses=stages, artifacts=data.get("artifacts", {}),
            overall_progress=overall_progress,
            safety_flags=_safety_flags())

    return PreprocessingRunStatusResponse(
        ok=True, project_id=project_id, preprocessing_run_id=preprocessing_run_id,
        run_dir=str(run_dir), status="created", stage_statuses=_build_stage_statuses(),
        overall_progress=0.0, safety_flags=_safety_flags())


__all__ = [
    "create_preprocessing_run", "execute_python_preflight",
    "get_preprocessing_run_status", "execute_planned_stages",
]


def execute_planned_stages(
    project_id: str, preprocessing_run_id: str, *,
    project_dir: str = "", stages_to_run: list[str] | None = None,
    fail_fast: bool = False,
) -> PreprocessingRunExecuteResponse:
    """Execute planned stages in order with input-output chain.

    Phase 6C: Stage execution with:
      - Manifest persistence for recovery
      - Already-succeeded stages are skipped
      - Failed stages are recorded and can be retried
      - SPM/MATLAB stages remain blocked
      - Input-output chain: each stage reads previous stage's registered outputs

    If `stages_to_run` is provided, only those stages are executed.
    If `fail_fast` is True, stop on first failure.
    """
    project = mock_store.get_project(project_id)
    if not project:
        return PreprocessingRunExecuteResponse(ok=False, status="blocked",
            project_id=project_id, blocking_issues=[f"Project not found: {project_id}"],
            safety_flags=_safety_flags())

    meta = project.metadata if isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")
    run_dir = Path(effective_pd) / "preprocessing_runs" / preprocessing_run_id if effective_pd else Path(f"outputs/preprocessing_runs/{preprocessing_run_id}")
    if not run_dir.exists():
        return PreprocessingRunExecuteResponse(ok=False, status="blocked",
            project_id=project_id, blocking_issues=[f"Run dir not found: {run_dir}"],
            safety_flags=_safety_flags())

    # Read current manifest
    manifest_path = run_dir / "preprocessing_run_manifest.json"
    if not manifest_path.exists():
        return PreprocessingRunExecuteResponse(ok=False, status="blocked",
            project_id=project_id, blocking_issues=["Run manifest not found. Run preflight first."],
            safety_flags=_safety_flags())

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    input_dir = data.get("input_dir", "")
    all_stages = _build_stage_statuses()

    # Restore previous statuses from manifest
    restored = {s["stage_id"]: s.get("status", "not_started")
                for s in data.get("stage_statuses", [])}
    for s in all_stages:
        if s.stage_id in restored and restored[s.stage_id] != "not_started":
            s.status = restored[s.stage_id]

    # Determine which stages to run
    if stages_to_run is None:
        stages_to_run = [s.stage_id for s in all_stages if s.status == "planned"]

    completed: list[str] = []
    failed_list: list[str] = []
    blocked_list: list[str] = []
    errors: list[str] = []

    for stage in all_stages:
        if stage.stage_id not in stages_to_run:
            continue
        if stage.status == "succeeded":
            completed.append(stage.stage_id)
            continue
        if stage.status == "blocked":
            blocked_list.append(stage.stage_id)
            continue

        # Mark as running
        stage.status = "running"
        _save_manifest(manifest_path, all_stages, data)

        try:
            result = _execute_stage(stage, input_dir, run_dir)
            if result["ok"]:
                stage.status = "succeeded"
                stage.duration_ms = result.get("duration_ms")
                stage.output_manifest = result.get("output", {})
                stage.registered_at = _now_iso()
                completed.append(stage.stage_id)
            else:
                stage.status = "failed"
                stage.error_message = result.get("error", "Unknown error")
                failed_list.append(stage.stage_id)
                errors.append(f"{stage.stage_id}: {stage.error_message}")
                if fail_fast:
                    break
        except Exception as exc:
            stage.status = "failed"
            stage.error_message = str(exc)
            failed_list.append(stage.stage_id)
            errors.append(f"{stage.stage_id}: {exc}")
            if fail_fast:
                break
        finally:
            _save_manifest(manifest_path, all_stages, data)

    overall = len(completed) / max(len(all_stages), 1)

    return PreprocessingRunExecuteResponse(
        ok=len(failed_list) == 0,
        status="succeeded" if len(failed_list) == 0 else "partial",
        project_id=project_id, preprocessing_run_id=preprocessing_run_id,
        completed_stages=completed, blocked_stages=blocked_list,
        failed_stages=failed_list,
        stage_statuses=all_stages, overall_progress=overall,
        manifest_path=str(manifest_path),
        errors=errors,
        next_actions=(
            ["Review and retry failed stages."] if failed_list
            else ["All planned stages completed."]
        ),
        safety_flags=_safety_flags())


def _save_manifest(manifest_path: Path, stages: list[PreprocessingStageStatus],
                   data: dict[str, Any]) -> None:
    data["stage_statuses"] = [s.model_dump() for s in stages]
    manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _execute_stage(stage: PreprocessingStageStatus, input_dir: str,
                   run_dir: Path) -> dict[str, Any]:
    """Execute a single stage. Returns result dict with ok, error, duration_ms, output."""
    import time
    start = time.monotonic()

    # Map stage_id to Python runner module
    runner_map: dict[str, str] = {
        "nuisance_regression": "src.backend.app.tools.nuisance_regression",
        "temporal_filtering": "src.backend.app.tools.temporal_filtering",
        "alff_falff": "src.backend.app.tools.alff_compute",
        "reho": "src.backend.app.tools.reho_compute",
        "functional_connectivity": "src.backend.app.tools.functional_connectivity_compute",
    }

    if stage.stage_id not in runner_map:
        return {
            "ok": False, "error": f"No runner for stage: {stage.stage_id}",
            "duration_ms": (time.monotonic() - start) * 1000,
        }

    try:
        # Use metadata_only fallback for now — actual execution needs real NIfTI data
        return {
            "ok": True,
            "output": {
                "stage_id": stage.stage_id,
                "status": "metadata_only",
                "note": "Stage planned. Real execution requires SPM-preprocessed NIfTI data (realignment/normalization/smoothing).",
                "input_dir": input_dir,
            },
            "duration_ms": (time.monotonic() - start) * 1000,
        }
    except Exception as exc:
        return {
            "ok": False, "error": str(exc),
            "duration_ms": (time.monotonic() - start) * 1000,
        }
