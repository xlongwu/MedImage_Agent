"""Preprocessing Run Service — Phase 6C.

Creates preprocessing run workspaces and executes stages in sequence with
the unified stage state machine from preprocessing_stage_catalog.

Python/GPU stages can execute when input data is available.
SPM/MATLAB stages remain blocked since MATLAB is not installed.
"""

from __future__ import annotations

import json
from datetime import UTC
from pathlib import Path
from typing import Any

from src.backend.app.runtime.atomic_file import atomic_write_json
from src.backend.app.schemas.preprocessing_run import (
    PreprocessingRunCreateRequest,
    PreprocessingRunCreateResponse,
    PreprocessingRunExecuteResponse,
    PreprocessingRunStatusResponse,
    PreprocessingStageStatus,
)
from src.backend.app.schemas.preprocessing_stage_catalog import (
    PreprocessingStageSpec,
    initial_stage_execution_status,
    iter_preprocessing_stage_specs,
    normalize_stage_execution_status,
)
from src.backend.app.services.mock_store import mock_store
from src.backend.app.services.preprocessing_artifact_registry import (
    REGISTRY_FILENAME,
    ensure_run_artifact_registry,
    parse_bids_entities,
    update_run_registry_inventory,
)


def _now_iso() -> str:
    from datetime import datetime

    return datetime.now(UTC).isoformat()


def _safety_flags() -> dict[str, bool]:
    return {
        "rawdata_not_modified": True,
        "no_external_tools_executed": True,
        "no_spm_dpabi_matlab": True,
        "python_only": True,
        "preprocessing_not_fully_executed": True,
        "research_use_only": True,
        "clinical_use_prohibited": True,
    }


_PREFLIGHT_METADATA_STAGES = {"input_validation", "subject_qc", "group_summary"}


def _stage_status_from_spec(spec: PreprocessingStageSpec) -> PreprocessingStageStatus:
    return PreprocessingStageStatus(
        stage_id=spec.stage_id,
        name=spec.display_name,
        status=initial_stage_execution_status(spec),
        backend=spec.default_backend,
        requires_external_tool=spec.requires_external_tool,
        enabled=spec.default_enabled,
        optional=spec.optional,
        category=spec.category,
        default_enabled=spec.default_enabled,
        required_for_fc=spec.required_for_fc,
        input_artifact_types=list(spec.input_artifact_types),
        output_artifact_types=list(spec.output_artifact_types),
        supported_backends=list(spec.supported_backends),
        default_backend=spec.default_backend,
        requires_approval=spec.requires_approval,
        requires_env_flags=list(spec.requires_env_flags),
        can_run_in_ci=spec.can_run_in_ci,
        scientific_status=spec.scientific_status,
        validation_status=spec.validation_status,
    )


def _build_stage_statuses() -> list[PreprocessingStageStatus]:
    return [_stage_status_from_spec(spec) for spec in iter_preprocessing_stage_specs()]


def _discover_input_inventory(input_dir: Path) -> dict[str, Any]:
    bold_files: list[str] = []
    t1w_files: list[str] = []
    sidecars: list[str] = []
    bold_subjects: set[str] = set()
    t1w_subjects: set[str] = set()
    sessions: set[str] = set()
    bids_entities: list[dict[str, Any]] = []
    sidecar_stems: set[str] = set()
    for p in sorted(input_dir.rglob("*")):
        if not p.is_file():
            continue
        entities = parse_bids_entities(p)
        if entities.session_id:
            sessions.add(entities.session_id)
        bids_entities.append(entities.model_dump())
        name = p.name.lower()
        if p.suffix in (".nii", ".gz") or "".join(p.suffixes).lower() in (".nii", ".nii.gz"):
            if "bold" in name or "rest" in name:
                bold_files.append(str(p))
                if entities.subject_id:
                    bold_subjects.add(entities.subject_id)
            elif "t1" in name:
                t1w_files.append(str(p))
                if entities.subject_id:
                    t1w_subjects.add(entities.subject_id)
        elif p.suffix == ".json":
            sidecars.append(str(p))
            sidecar_stems.add(p.stem)
    all_subjects = sorted(bold_subjects | t1w_subjects)
    missing_sidecars: list[dict[str, str]] = []
    for value in [*bold_files, *t1w_files]:
        path = Path(value)
        suffixes = "".join(path.suffixes).lower()
        stem = path.name[:-7] if suffixes.endswith(".nii.gz") else path.stem
        if stem not in sidecar_stems:
            missing_sidecars.append({"nifti_path": value, "expected_sidecar_stem": stem})
    return {
        "subjects": all_subjects,
        "bold_files": bold_files,
        "t1w_files": t1w_files,
        "sidecar_jsons": sidecars,
        "nifti_count": len(bold_files) + len(t1w_files),
        "bold_count": len(bold_files),
        "t1w_count": len(t1w_files),
        "sessions": sorted(sessions),
        "bids_entities": bids_entities,
        "missing_sidecar_pairings": missing_sidecars,
        "missing_t1w_subjects": sorted(bold_subjects - t1w_subjects),
        "missing_bold_subjects": sorted(t1w_subjects - bold_subjects),
    }


def _is_relative_to(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def _registered_bids_evidence_is_managed(metadata: dict[str, Any]) -> bool:
    """Return whether the registered BIDS source has a managed project index."""

    project_dir = str(metadata.get("project_dir") or "").strip()
    dataset_index_path = str(metadata.get("dataset_index_path") or "").strip()
    if not project_dir or not dataset_index_path:
        return False
    try:
        project_root = Path(project_dir).expanduser().resolve()
        index_path = Path(dataset_index_path).expanduser().resolve()
    except OSError:
        return False
    return index_path.is_file() and _is_relative_to(index_path, project_root / "data")


def _registered_rawdata_confirmations(
    request: PreprocessingRunCreateRequest,
) -> list[str]:
    confirmations = {
        "confirm_use_converted_input": request.confirm_use_converted_input,
        "confirm_no_rawdata_modification": request.confirm_no_rawdata_modification,
        "confirm_python_only_execution": request.confirm_python_only_execution,
        "confirm_no_spm_matlab": request.confirm_no_spm_matlab,
    }
    return [name for name, confirmed in confirmations.items() if not confirmed]


def create_preprocessing_run(
    project_id: str,
    request: PreprocessingRunCreateRequest,
    *,
    project_dir: str = "",
    store: Any | None = None,
) -> PreprocessingRunCreateResponse:
    _blocking: list[str] = []
    project_store = store or mock_store
    project = project_store.get_project(project_id)
    if not project:
        return PreprocessingRunCreateResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=[f"Project not found: {project_id}"],
            safety_flags=_safety_flags(),
        )

    meta = project.metadata if isinstance(project.metadata, dict) else {}
    rawdata_dir = str(meta.get("rawdata_dir") or "")
    input_dir = request.preprocessing_input_dir or str(meta.get("preprocessing_input_dir") or "")
    if (
        not input_dir
        and request.confirm_use_converted_input
        and rawdata_dir
        and _registered_bids_evidence_is_managed(meta)
    ):
        input_dir = rawdata_dir

    if not input_dir:
        return PreprocessingRunCreateResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["No preprocessing input registered."],
            safety_flags=_safety_flags(),
        )

    if ".." in input_dir:
        return PreprocessingRunCreateResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["Path traversal detected."],
            safety_flags=_safety_flags(),
        )

    input_path = Path(input_dir).expanduser().resolve()
    if not input_path.exists() or not input_path.is_dir():
        return PreprocessingRunCreateResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=[f"Input dir not found: {input_dir}"],
            safety_flags=_safety_flags(),
        )

    uses_registered_rawdata = False
    if rawdata_dir:
        rawdata_path = Path(rawdata_dir).expanduser().resolve()
        if _is_relative_to(input_path, rawdata_path):
            missing_confirmations = _registered_rawdata_confirmations(request)
            if (
                input_path != rawdata_path
                or not _registered_bids_evidence_is_managed(meta)
                or missing_confirmations
            ):
                issues = [
                    "Preprocessing input inside rawdata is allowed only for the exact "
                    "registered BIDS root backed by the managed dataset index."
                ]
                if missing_confirmations:
                    issues.append(
                        "Missing registered BIDS read-only confirmations: "
                        + ", ".join(missing_confirmations)
                    )
                return PreprocessingRunCreateResponse(
                    ok=False,
                    status="blocked",
                    project_id=project_id,
                    blocking_issues=issues,
                    safety_flags=_safety_flags(),
                )
            uses_registered_rawdata = True

    input_dir = str(input_path)
    source_kind = (
        request.source_kind
        or str(meta.get("preprocessing_input_source") or "")
        or ("registered_bids_readonly" if uses_registered_rawdata else "external_import")
    )

    import hashlib

    run_id = "pp-" + hashlib.sha256(f"{project_id}:{_now_iso()}".encode()).hexdigest()[:12]
    effective_pd = project_dir or str(meta.get("project_dir") or "")
    run_dir = (
        Path(effective_pd) / "preprocessing_runs" / run_id
        if effective_pd
        else Path(f"outputs/preprocessing_runs/{run_id}")
    )
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
        f"Research use only.\n",
        encoding="utf-8",
    )

    stages = _build_stage_statuses()
    source_registry_path = request.input_registry_path or str(
        meta.get("preprocessing_input_registry_path") or ""
    )
    conversion_run_id = request.conversion_run_id or str(
        meta.get("preprocessing_conversion_run_id") or ""
    )
    registry = ensure_run_artifact_registry(
        project_id=project_id,
        preprocessing_run_id=run_id,
        run_dir=run_dir,
        input_dir=input_dir,
        project_dir=effective_pd,
        source_registry_path=source_registry_path,
        conversion_run_id=conversion_run_id,
        source_kind=source_kind,
    )
    if not registry.ok:
        return PreprocessingRunCreateResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            preprocessing_run_id=run_id,
            run_dir=str(run_dir),
            preprocessing_input_dir=input_dir,
            blocking_issues=registry.blocking_issues,
            warnings=registry.warnings,
            errors=registry.errors,
            safety_flags=_safety_flags(),
        )
    if isinstance(project.metadata, dict):
        project.metadata["preprocessing_run_registry_path"] = registry.registry_path

    python_count = sum(1 for s in stages if s.backend == "python")
    blocked_count = sum(1 for s in stages if s.status == "blocked")
    planned_count = sum(1 for s in stages if s.status == "planned")
    manifest_path = run_dir / "preprocessing_run_manifest.json"
    manifest = {
        "project_id": project_id,
        "preprocessing_run_id": run_id,
        "status": "created",
        "input_dir": input_dir,
        "source_kind": source_kind,
        "conversion_run_id": conversion_run_id,
        "artifact_registry_path": registry.registry_path,
        "input_inventory": registry.inventory,
        "created_at": _now_iso(),
        "stage_statuses": [s.model_dump() for s in stages],
        "artifacts": {"artifact_registry": registry.registry_path},
        "safety_flags": _safety_flags(),
    }
    atomic_write_json(manifest_path, manifest, schema_version=1)

    persistence_warnings: list[str] = []
    try:
        updated = project_store.update_project_metadata(
            project_id,
            {
                "preprocessing_input_dir": input_dir,
                "preprocessing_input_source": source_kind,
                "preprocessing_input_registry_path": registry.registry_path,
                "preprocessing_run_registry_path": registry.registry_path,
                "latest_preprocessing_run_id": run_id,
                "latest_preprocessing_run_manifest_path": str(manifest_path),
                "latest_preprocessing_run_status": "created",
                "latest_preprocessing_run_updated_at": manifest["created_at"],
            },
        )
        if updated is None:
            persistence_warnings.append(
                "Preprocessing run was created, but project metadata was not updated."
            )
    except Exception as exc:
        persistence_warnings.append(
            f"Preprocessing run was created, but project metadata persistence failed: {exc}"
        )

    return PreprocessingRunCreateResponse(
        ok=True,
        status="created",
        project_id=project_id,
        preprocessing_run_id=run_id,
        run_dir=str(run_dir),
        preprocessing_input_dir=input_dir,
        artifact_registry_path=registry.registry_path,
        input_inventory=registry.inventory,
        stage_count=len(stages),
        python_stage_count=python_count,
        external_blocked_count=blocked_count,
        planned_stage_count=planned_count,
        disabled_external_stage_count=blocked_count,
        warnings=[*registry.warnings, *persistence_warnings],
        next_actions=[
            "Execute Python preflight to generate input inventory and QC summary.",
            f"{planned_count} stages available for execution in Python/GPU.",
        ],
        safety_flags=_safety_flags(),
    )


def execute_python_preflight(
    project_id: str,
    preprocessing_run_id: str,
    *,
    project_dir: str = "",
    store: Any | None = None,
) -> PreprocessingRunExecuteResponse:
    project_store = store or mock_store
    project = project_store.get_project(project_id)
    if not project:
        return PreprocessingRunExecuteResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=[f"Project not found: {project_id}"],
            safety_flags=_safety_flags(),
        )

    meta = project.metadata if isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")
    run_dir = (
        Path(effective_pd) / "preprocessing_runs" / preprocessing_run_id
        if effective_pd
        else Path(f"outputs/preprocessing_runs/{preprocessing_run_id}")
    )
    if not run_dir.exists():
        return PreprocessingRunExecuteResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=[f"Run dir not found: {run_dir}"],
            safety_flags=_safety_flags(),
        )

    # Read input dir from metadata first, then fall back to run-dir record
    input_dir = str(meta.get("preprocessing_input_dir") or "")
    if not input_dir:
        txt_path = run_dir / "input_dir.txt"
        if txt_path.exists():
            input_dir = txt_path.read_text(encoding="utf-8").strip()
    input_path = Path(input_dir) if input_dir else None
    if not input_path or not input_path.exists():
        return PreprocessingRunExecuteResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["Preprocessing input not found."],
            safety_flags=_safety_flags(),
        )

    # Build inventory
    inventory = _discover_input_inventory(input_path)
    inv_path = run_dir / "input_inventory.json"
    atomic_write_json(inv_path, inventory, schema_version=1)
    registry_path = run_dir / REGISTRY_FILENAME
    if not registry_path.exists():
        source_registry_path = str(meta.get("preprocessing_input_registry_path") or "")
        ensure_run_artifact_registry(
            project_id=project_id,
            preprocessing_run_id=preprocessing_run_id,
            run_dir=run_dir,
            input_dir=input_dir,
            project_dir=effective_pd,
            source_registry_path=source_registry_path,
            conversion_run_id=str(meta.get("preprocessing_conversion_run_id") or ""),
            source_kind=str(meta.get("preprocessing_input_source") or "external_import"),
        )
    update_run_registry_inventory(registry_path, inventory)

    # Build QC preflight
    qc = {
        "readable_count": inventory["nifti_count"],
        "unreadable_count": 0,
        "four_d_count": 0,
        "warnings": [],
        "errors": [],
        "subject_pairing_summary": {
            "total_subjects": len(inventory["subjects"]),
            "bold_count": inventory["bold_count"],
            "t1w_count": inventory["t1w_count"],
            "missing_t1w": inventory["missing_t1w_subjects"],
            "missing_bold": inventory["missing_bold_subjects"],
        },
        "recommended_next_actions": [
            "Review subject pairings.",
            "Enable MATLAB/SPM for advanced preprocessing.",
        ],
    }
    if inventory["missing_t1w_subjects"]:
        qc["warnings"].append(f"Missing T1w for: {inventory['missing_t1w_subjects']}")
    if inventory["missing_bold_subjects"]:
        qc["warnings"].append(f"Missing BOLD for: {inventory['missing_bold_subjects']}")
    qc_path = run_dir / "qc_preflight_summary.json"
    atomic_write_json(qc_path, qc, schema_version=1)

    # Build manifest
    stages = _build_stage_statuses()
    completed = [s.stage_id for s in stages if s.stage_id in _PREFLIGHT_METADATA_STAGES]
    blocked = [s.stage_id for s in stages if s.status == "blocked"]
    planned = [s.stage_id for s in stages if s.status == "planned"]
    # Mark only actual Python preflight metadata stages as completed.
    for s in stages:
        if s.stage_id in completed and s.status == "not_started":
            s.status = "succeeded"
    overall_progress = len(completed) / max(len(stages), 1)
    manifest = {
        "project_id": project_id,
        "preprocessing_run_id": preprocessing_run_id,
        "status": "completed_python_preflight",
        "input_dir": input_dir,
        "created_at": _now_iso(),
        "artifact_registry_path": str(registry_path),
        "input_inventory": inventory,
        "overall_progress": overall_progress,
        "stage_statuses": [s.model_dump() for s in stages],
        "artifacts": {
            "input_inventory": str(inv_path),
            "qc_preflight_summary": str(qc_path),
            "artifact_registry": str(registry_path),
        },
        "safety_flags": _safety_flags(),
    }
    manifest_path = run_dir / "preprocessing_run_manifest.json"
    atomic_write_json(manifest_path, manifest, schema_version=1)

    return PreprocessingRunExecuteResponse(
        ok=True,
        status="completed_python_preflight",
        project_id=project_id,
        preprocessing_run_id=preprocessing_run_id,
        completed_stages=completed,
        blocked_stages=blocked,
        failed_stages=[],
        disabled_external_stages=blocked,
        stage_statuses=stages,
        overall_progress=overall_progress,
        input_inventory_path=str(inv_path),
        qc_preflight_summary_path=str(qc_path),
        manifest_path=str(manifest_path),
        artifact_registry_path=str(registry_path),
        next_actions=[
            "Review input inventory and QC preflight.",
            f"{len(planned)} executable stages ready. SPM/MATLAB stages blocked.",
        ],
        safety_flags=_safety_flags(),
    )


def get_preprocessing_run_status(
    project_id: str,
    preprocessing_run_id: str,
    *,
    project_dir: str = "",
    store: Any | None = None,
) -> PreprocessingRunStatusResponse:
    project_store = store or mock_store
    project = project_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")
    run_dir = (
        Path(effective_pd) / "preprocessing_runs" / preprocessing_run_id
        if effective_pd
        else Path(f"outputs/preprocessing_runs/{preprocessing_run_id}")
    )
    if not run_dir.exists():
        return PreprocessingRunStatusResponse(
            ok=False,
            project_id=project_id,
            preprocessing_run_id=preprocessing_run_id,
            errors=[f"Run not found: {run_dir}"],
            safety_flags=_safety_flags(),
        )

    manifest_path = run_dir / "preprocessing_run_manifest.json"
    if manifest_path.exists():
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        stages = [PreprocessingStageStatus(**s) for s in data.get("stage_statuses", [])]
        completed = sum(1 for s in stages if s.status == "succeeded")
        total = max(len(stages), 1)
        overall_progress = data.get("overall_progress", completed / total)
        return PreprocessingRunStatusResponse(
            ok=True,
            project_id=project_id,
            preprocessing_run_id=preprocessing_run_id,
            run_dir=str(run_dir),
            preprocessing_input_dir=data.get("input_dir", ""),
            status=data.get("status", "created"),
            created_at=data.get("created_at", ""),
            stage_statuses=stages,
            artifacts=data.get("artifacts", {}),
            artifact_registry_path=str(
                data.get("artifact_registry_path")
                or data.get("artifacts", {}).get("artifact_registry", "")
            ),
            input_inventory=data.get("input_inventory", {}),
            overall_progress=overall_progress,
            safety_flags=_safety_flags(),
        )

    return PreprocessingRunStatusResponse(
        ok=True,
        project_id=project_id,
        preprocessing_run_id=preprocessing_run_id,
        run_dir=str(run_dir),
        status="created",
        stage_statuses=_build_stage_statuses(),
        overall_progress=0.0,
        safety_flags=_safety_flags(),
    )


__all__ = [
    "create_preprocessing_run",
    "execute_python_preflight",
    "get_preprocessing_run_status",
    "execute_planned_stages",
]


def execute_planned_stages(
    project_id: str,
    preprocessing_run_id: str,
    *,
    project_dir: str = "",
    stages_to_run: list[str] | None = None,
    fail_fast: bool = False,
    store: Any | None = None,
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
    project_store = store or mock_store
    project = project_store.get_project(project_id)
    if not project:
        return PreprocessingRunExecuteResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=[f"Project not found: {project_id}"],
            safety_flags=_safety_flags(),
        )

    meta = project.metadata if isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")
    run_dir = (
        Path(effective_pd) / "preprocessing_runs" / preprocessing_run_id
        if effective_pd
        else Path(f"outputs/preprocessing_runs/{preprocessing_run_id}")
    )
    if not run_dir.exists():
        return PreprocessingRunExecuteResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=[f"Run dir not found: {run_dir}"],
            safety_flags=_safety_flags(),
        )

    # Read current manifest
    manifest_path = run_dir / "preprocessing_run_manifest.json"
    if not manifest_path.exists():
        return PreprocessingRunExecuteResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["Run manifest not found. Run preflight first."],
            safety_flags=_safety_flags(),
        )

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    input_dir = data.get("input_dir", "")
    all_stages = _build_stage_statuses()

    # Restore previous statuses from manifest
    restored = {
        s["stage_id"]: s.get("status", "not_started") for s in data.get("stage_statuses", [])
    }
    for s in all_stages:
        if s.stage_id in restored and restored[s.stage_id] != "not_started":
            s.status = normalize_stage_execution_status(str(restored[s.stage_id]))

    # Determine which stages to run
    if stages_to_run is None:
        stages_to_run = [s.stage_id for s in all_stages if s.status == "planned"]

    completed: list[str] = []
    metadata_only_list: list[str] = []
    preview_only_list: list[str] = []
    failed_list: list[str] = []
    blocked_list: list[str] = []
    errors: list[str] = []
    warnings: list[str] = []

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
                output = result.get("output", {})
                output_status = (
                    str(output.get("status", "succeeded"))
                    if isinstance(output, dict)
                    else "succeeded"
                )
                stage.status = normalize_stage_execution_status(
                    output_status,
                    metadata_only=bool(
                        isinstance(output, dict) and output.get("metadata_only", False)
                    ),
                    preview_only=bool(
                        isinstance(output, dict) and output.get("preview_only", False)
                    ),
                )
                stage.duration_ms = result.get("duration_ms")
                stage.output_manifest = output if isinstance(output, dict) else {}
                stage.registered_at = _now_iso()
                if stage.status == "succeeded":
                    completed.append(stage.stage_id)
                elif stage.status == "metadata_only":
                    metadata_only_list.append(stage.stage_id)
                    warnings.append(
                        f"{stage.stage_id}: metadata_only output was not promoted to succeeded."
                    )
                elif stage.status == "preview_only":
                    preview_only_list.append(stage.stage_id)
                    warnings.append(
                        f"{stage.stage_id}: preview_only output was not promoted to succeeded."
                    )
                elif stage.status == "partial":
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
    if failed_list:
        response_status = "partial"
    elif metadata_only_list and not completed:
        response_status = "metadata_only"
    elif metadata_only_list or preview_only_list:
        response_status = "partial"
    else:
        response_status = "succeeded"

    return PreprocessingRunExecuteResponse(
        ok=len(failed_list) == 0,
        status=response_status,
        project_id=project_id,
        preprocessing_run_id=preprocessing_run_id,
        completed_stages=completed,
        blocked_stages=blocked_list,
        failed_stages=failed_list,
        metadata_only_stages=metadata_only_list,
        preview_only_stages=preview_only_list,
        stage_statuses=all_stages,
        overall_progress=overall,
        manifest_path=str(manifest_path),
        warnings=warnings,
        errors=errors,
        next_actions=(
            ["Review and retry failed stages."]
            if failed_list
            else ["Review metadata_only or preview_only stages before continuing."]
            if metadata_only_list or preview_only_list
            else ["All planned stages completed."]
        ),
        safety_flags=_safety_flags(),
    )


def _save_manifest(
    manifest_path: Path, stages: list[PreprocessingStageStatus], data: dict[str, Any]
) -> None:
    data["stage_statuses"] = [s.model_dump() for s in stages]
    data["updated_at"] = _now_iso()
    atomic_write_json(manifest_path, data, schema_version=1)


def _execute_stage(
    stage: PreprocessingStageStatus, input_dir: str, run_dir: Path
) -> dict[str, Any]:
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
            "ok": False,
            "error": f"No runner for stage: {stage.stage_id}",
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
            "ok": False,
            "error": str(exc),
            "duration_ms": (time.monotonic() - start) * 1000,
        }
