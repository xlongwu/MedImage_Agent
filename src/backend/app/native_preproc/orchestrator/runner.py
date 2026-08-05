"""Native full preprocessing dry-run and execution orchestration."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.backend.app.native_preproc.dpabi_compat.dparsf_config import convert_dparsf_config
from src.backend.app.native_preproc.io.nifti_io import load_nifti
from src.backend.app.native_preproc.orchestrator.artifact_registry import build_artifact_ref
from src.backend.app.native_preproc.orchestrator.gpu_resource_planner import plan_gpu_stage
from src.backend.app.native_preproc.orchestrator.report import run_group_summary
from src.backend.app.native_preproc.orchestrator.stage_graph import (
    NativeFullStageSpec,
    iter_native_full_stage_specs,
    native_full_stage_graph_payload,
)
from src.backend.app.native_preproc.orchestrator.state import NativePreprocRunContext
from src.backend.app.native_preproc.orchestrator.validation import (
    build_full_run_validation_payload,
    validate_stage_result_artifacts,
)
from src.backend.app.native_preproc.stages._common import stage_result
from src.backend.app.native_preproc.stages.alff_falff import run_alff, run_falff
from src.backend.app.native_preproc.stages.atlas_resampling import run_atlas_resampling
from src.backend.app.native_preproc.stages.coregistration import run_coregistration
from src.backend.app.native_preproc.stages.detrending import run_detrending
from src.backend.app.native_preproc.stages.dummy_scan import run_dummy_scan_removal
from src.backend.app.native_preproc.stages.functional_connectivity import (
    run_functional_connectivity,
)
from src.backend.app.native_preproc.stages.motion_qc import run_motion_qc
from src.backend.app.native_preproc.stages.normalization import run_affine_normalization
from src.backend.app.native_preproc.stages.nuisance_regression import run_nuisance_regression
from src.backend.app.native_preproc.stages.realignment import run_realignment
from src.backend.app.native_preproc.stages.reho import run_reho
from src.backend.app.native_preproc.stages.roi_timeseries import run_roi_timeseries
from src.backend.app.native_preproc.stages.segmentation import run_segmentation
from src.backend.app.native_preproc.stages.slice_timing import run_slice_timing_correction
from src.backend.app.native_preproc.stages.smoothing import run_smoothing
from src.backend.app.native_preproc.stages.temporal_filtering import run_temporal_filtering
from src.backend.app.runtime.atomic_file import atomic_write_json
from src.backend.app.schemas.native_preproc import NativePreprocQC, NativePreprocStageResult
from src.backend.app.schemas.native_preproc_api import (
    NativeFullPreprocRequest,
    NativeFullPreprocResponse,
    NativeFullStageApiResult,
)

# Process-local hook used by the spawn-safe subject worker.  The runner remains
# sequential; this only makes stage boundaries observable to its parent.
_NATIVE_PREPROC_PROGRESS_CALLBACK: Callable[[str, str], None] | None = None


def set_native_preproc_progress_callback(callback: Callable[[str, str], None] | None) -> None:
    global _NATIVE_PREPROC_PROGRESS_CALLBACK
    _NATIVE_PREPROC_PROGRESS_CALLBACK = callback


def _emit_stage_progress(stage_id: str, status: str) -> None:
    callback = _NATIVE_PREPROC_PROGRESS_CALLBACK
    if callback is not None:
        try:
            callback(stage_id, status)
        except Exception:
            # Telemetry must never alter a reviewed scientific computation.
            pass


_BIDS_SUBJECT_RE = re.compile(r"sub-[A-Za-z0-9]+")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_run_id(project_id: str) -> str:
    digest = hashlib.sha256(f"{project_id}:{_now_iso()}".encode()).hexdigest()[:12]
    return f"npre-{digest}"


def _safety_flags(*, dry_run: bool, confirmations_ok: bool = True) -> dict[str, bool]:
    return {
        "dry_run_only": dry_run,
        "rawdata_readonly_confirmed": confirmations_ok,
        "no_external_tools_executed": True,
        "no_matlab_spm_dpabi": True,
        "third_party_runtime_not_used": True,
        "research_use_only": confirmations_ok,
        "clinical_use_prohibited": True,
    }


def _project_root(project_dir: str, project_id: str) -> Path:
    return Path(project_dir).expanduser().resolve() if project_dir else Path("outputs") / "native_preproc" / project_id


def _is_within(path: Path, root: Path) -> bool:
    resolved = path.resolve()
    root = root.resolve()
    return resolved == root or root in resolved.parents


def _has_rawdata_part(path: Path) -> bool:
    return any(part.lower() == "rawdata" for part in path.parts)


def _default_sidecar_path(input_bold: str) -> str:
    if not input_bold:
        return ""
    path = Path(input_bold)
    name = path.name
    if name.endswith(".nii.gz"):
        return str(path.with_name(name.removesuffix(".nii.gz") + ".json"))
    return str(path.with_suffix(".json"))


def _infer_subject_id_from_paths(*paths: str) -> str:
    for raw_path in paths:
        if not raw_path:
            continue
        text = str(raw_path)
        for part in Path(text).parts:
            match = _BIDS_SUBJECT_RE.search(part)
            if match:
                return match.group(0)
        match = _BIDS_SUBJECT_RE.search(text)
        if match:
            return match.group(0)
    return ""


def _with_inferred_subject_id(request: NativeFullPreprocRequest) -> NativeFullPreprocRequest:
    if request.subject_id:
        return request
    inferred = _infer_subject_id_from_paths(request.input_bold, request.sidecar_json, request.t1w)
    if not inferred:
        return request
    return request.model_copy(update={"subject_id": inferred})


def _read_sidecar(sidecar_path: str) -> dict[str, Any]:
    if not sidecar_path:
        return {}
    path = Path(sidecar_path)
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def _tr_from_request_or_sidecar(request: NativeFullPreprocRequest, sidecar: dict[str, Any]) -> float | None:
    if request.tr is not None:
        return float(request.tr)
    value = sidecar.get("RepetitionTime")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _stage_enabled(request: NativeFullPreprocRequest, stage_id: str, *, default: bool = True) -> bool:
    if stage_id in request.stage_overrides:
        return bool(request.stage_overrides[stage_id])
    return default


def _apply_dparsf_config(
    request: NativeFullPreprocRequest,
) -> tuple[NativeFullPreprocRequest, list[str]]:
    if not request.dparsf_config:
        return request, []

    conversion = convert_dparsf_config(request.dparsf_config)
    updates: dict[str, Any] = {"stage_overrides": dict(request.stage_overrides)}
    for stage in conversion.stage_configs:
        updates["stage_overrides"][stage.stage_id] = bool(stage.enabled)
        params = dict(stage.parameters or {})
        if stage.stage_id == "dummy_scan_removal" and "remove_first" in params:
            updates["remove_first"] = int(params["remove_first"] or 0)
        elif stage.stage_id == "slice_timing":
            updates["enable_slice_timing"] = bool(stage.enabled)
            if "reference_slice" in params:
                updates["reference_slice_index"] = int(params["reference_slice"])
        elif stage.stage_id == "nuisance_regression":
            if "include_wm" in params:
                updates["include_wm"] = bool(params["include_wm"])
            if "include_csf" in params:
                updates["include_csf"] = bool(params["include_csf"])
            if "include_global_signal" in params:
                updates["include_global_signal"] = bool(params["include_global_signal"])
            if "polynomial_order" in params:
                updates["polynomial_order"] = int(params["polynomial_order"] or 0)
            if params.get("scrub_threshold_mm") is not None:
                updates["fd_threshold_mm"] = float(params["scrub_threshold_mm"])
        elif stage.stage_id == "detrending" and "polynomial_order" in params:
            updates["polynomial_order"] = int(params["polynomial_order"] or 0)
        elif stage.stage_id == "temporal_filtering":
            if "filter_type" in params:
                updates["temporal_filter_type"] = str(params["filter_type"])
            if params.get("low_hz") is not None:
                updates["low_hz"] = float(params["low_hz"])
            if params.get("high_hz") is not None:
                updates["high_hz"] = float(params["high_hz"])
            if "method" in params:
                updates["filtering_method"] = str(params["method"])
        elif stage.stage_id == "smoothing" and "fwhm_mm" in params:
            updates["fwhm_mm"] = params["fwhm_mm"]

    warnings = list(conversion.warnings)
    if conversion.unsupported_keys:
        warnings.append(
            "Unsupported DPARSF keys were preserved in warnings/provenance: "
            + ", ".join(conversion.unsupported_keys)
        )
    return request.model_copy(update=updates), warnings


def _path_exists(value: str) -> bool:
    return bool(value) and Path(value).is_file()


def _artifact_path(result: NativePreprocStageResult | None, artifact_type: str) -> str:
    if not result:
        return ""
    for artifact in result.output_artifacts:
        if artifact.artifact_type == artifact_type:
            return artifact.path
    return ""


def _artifact_paths(result: NativePreprocStageResult | None, artifact_type: str) -> list[str]:
    if not result:
        return []
    return [
        artifact.path
        for artifact in result.output_artifacts
        if artifact.artifact_type == artifact_type and artifact.path
    ]


def _alias_nifti_input(run_dir: Path, path_value: str, name: str) -> str:
    if not path_value:
        return ""
    source = Path(path_value)
    if not source.exists():
        return path_value
    suffix = ".nii.gz" if source.name.endswith(".nii.gz") else source.suffix
    if suffix not in {".nii", ".nii.gz"}:
        return path_value
    target = run_dir / "work_inputs" / f"{name}{suffix}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != target.resolve():
        shutil.copyfile(source, target)
    return str(target)


def _result_to_api(
    spec: NativeFullStageSpec,
    result: NativePreprocStageResult,
    *,
    validation_errors: list[str] | None = None,
) -> NativeFullStageApiResult:
    return NativeFullStageApiResult(
        stage_id=spec.stage_id,
        display_name=spec.display_name,
        node_id=spec.node_id,
        status=result.status,
        capability_level=result.capability_level,
        validation_status=result.validation_status,
        backend=result.backend,
        input_artifacts=[artifact.model_dump(mode="json") for artifact in result.input_artifacts],
        output_artifacts=[artifact.model_dump(mode="json") for artifact in result.output_artifacts],
        warnings=list(result.warnings),
        errors=list(result.errors),
        validation_errors=validation_errors or [],
        result={
            "artifact_count": len(result.output_artifacts),
            "qc_status": result.qc.status,
            "qc_metrics": result.qc.metrics,
        },
    )


def _plain_stage(
    spec: NativeFullStageSpec,
    status: str,
    *,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    blocking_issues: list[str] | None = None,
    result: dict[str, Any] | None = None,
) -> NativeFullStageApiResult:
    return NativeFullStageApiResult(
        stage_id=spec.stage_id,
        display_name=spec.display_name,
        node_id=spec.node_id,
        status=status,
        capability_level=spec.capability_level,
        backend="native_python",
        warnings=warnings or [],
        errors=errors or [],
        blocking_issues=blocking_issues or [],
        result=result or {},
    )


def _metadata_result(
    context: NativePreprocRunContext,
    spec: NativeFullStageSpec,
    *,
    metrics: dict[str, Any],
    warnings: list[str] | None = None,
    status: str = "metadata_only",
) -> NativePreprocStageResult:
    return stage_result(
        context,
        stage_id=spec.stage_id,  # type: ignore[arg-type]
        parameters={"orchestrator": "native_full"},
        status=status,  # type: ignore[arg-type]
        capability_level="metadata_only",
        qc=NativePreprocQC(status="warning" if warnings else "pass", metrics=metrics, warnings=warnings or []),
        warnings=warnings or [],
    )


def _blocked_result(
    context: NativePreprocRunContext,
    spec: NativeFullStageSpec,
    *,
    issues: list[str],
) -> NativePreprocStageResult:
    return stage_result(
        context,
        stage_id=spec.stage_id,  # type: ignore[arg-type]
        parameters={"orchestrator": "native_full"},
        status="blocked",
        capability_level="metadata_only",
        qc=NativePreprocQC(status="fail", errors=issues),
        errors=issues,
    )


def _write_report_stage(
    context: NativePreprocRunContext,
    spec: NativeFullStageSpec,
    *,
    payload: dict[str, Any],
    artifact_type: str,
    filename: str,
) -> NativePreprocStageResult:
    report_dir = context.stage_artifact_dir(spec.stage_id)
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / filename
    atomic_write_json(path, payload, schema_version=1)
    output_ref = build_artifact_ref(path, artifact_type=artifact_type)  # type: ignore[arg-type]
    return stage_result(
        context,
        stage_id=spec.stage_id,  # type: ignore[arg-type]
        parameters={"orchestrator": "native_full", "report": filename},
        status="metadata_only",
        capability_level="metadata_only",
        qc=NativePreprocQC(status="pass", metrics={"report_path": str(path)}),
        output_artifacts=[output_ref],
    )


def _classify_response(
    stage_results: list[NativeFullStageApiResult],
) -> tuple[str, list[str], list[str], list[str], list[str], list[str], list[str]]:
    completed: list[str] = []
    blocked: list[str] = []
    failed: list[str] = []
    skipped: list[str] = []
    metadata_only: list[str] = []
    warning: list[str] = []
    for item in stage_results:
        if item.status == "succeeded":
            completed.append(item.stage_id)
        elif item.status == "warning":
            completed.append(item.stage_id)
            warning.append(item.stage_id)
        elif item.status == "blocked":
            blocked.append(item.stage_id)
        elif item.status == "failed":
            failed.append(item.stage_id)
        elif item.status == "skipped":
            skipped.append(item.stage_id)
        elif item.status == "metadata_only":
            metadata_only.append(item.stage_id)
    if failed:
        status = "failed"
    elif blocked:
        status = "blocked" if not completed else "partial"
    else:
        status = "succeeded"
    return status, completed, blocked, failed, skipped, metadata_only, warning


def _build_response(
    *,
    project_id: str,
    request: NativeFullPreprocRequest,
    run_id: str,
    run_dir: Path,
    dry_run: bool,
    stage_results: list[NativeFullStageApiResult],
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    blocking_issues: list[str] | None = None,
    manifest_path: Path | None = None,
) -> NativeFullPreprocResponse:
    status, completed, blocked, failed, skipped, metadata_only, warning_stages = _classify_response(stage_results)
    if dry_run and not blocked and not failed:
        status = "planned"
    artifact_count = sum(len(item.output_artifacts) for item in stage_results)
    validation_report_path = ""
    final_report_path = ""
    for item in stage_results:
        for artifact in item.output_artifacts:
            if artifact.get("artifact_type") == "validation_report":
                validation_report_path = str(artifact.get("path") or "")
            if artifact.get("artifact_type") == "final_report":
                final_report_path = str(artifact.get("path") or "")
    next_actions = (
        ["Resolve blocked native preprocessing stages before treating the run as complete."]
        if blocked
        else ["Review native validation and final reports before moving to reference validation."]
        if status == "succeeded"
        else ["Review failed native preprocessing stages before retry."]
    )
    return NativeFullPreprocResponse(
        ok=status in {"planned", "succeeded"},
        status=status,  # type: ignore[arg-type]
        dry_run=dry_run,
        project_id=project_id,
        run_id=run_id,
        run_dir=str(run_dir),
        stage_graph=native_full_stage_graph_payload(),
        stage_results=stage_results,
        completed_stages=completed,
        blocked_stages=blocked,
        failed_stages=failed,
        skipped_stages=skipped,
        metadata_only_stages=metadata_only,
        warning_stages=warning_stages,
        artifact_count=artifact_count,
        manifest_path=str(manifest_path or ""),
        validation_report_path=validation_report_path,
        final_report_path=final_report_path,
        warnings=warnings or [],
        errors=errors or [],
        blocking_issues=blocking_issues or [],
        next_actions=next_actions,
        safety_flags=_safety_flags(dry_run=dry_run, confirmations_ok=True),
    )


def dry_run_native_full_preproc(
    project_id: str,
    request: NativeFullPreprocRequest,
    *,
    project_dir: str = "",
) -> NativeFullPreprocResponse:
    request, dparsf_warnings = _apply_dparsf_config(request)
    request = _with_inferred_subject_id(request)
    run_id = request.run_id or _new_run_id(project_id)
    root = _project_root(project_dir, project_id)
    run_dir = Path(request.output_dir).expanduser() if request.output_dir else root / "preprocessing_native_runs" / run_id
    sidecar_path = request.sidecar_json or _default_sidecar_path(request.input_bold)
    sidecar = _read_sidecar(sidecar_path)
    tr = _tr_from_request_or_sidecar(request, sidecar)
    input_bold_exists = _path_exists(request.input_bold)
    input_shape: tuple[int, ...] = (1, 1, 1, 1)
    if input_bold_exists:
        try:
            input_shape = tuple(int(item) for item in load_nifti(request.input_bold).data.shape)
        except Exception:
            # The stage graph will report the malformed input separately; dry
            # run still returns a conservative, inspectable GPU decision.
            pass
    available = {
        "input_bold": input_bold_exists,
        "bold_4d": input_bold_exists,
        "reference_image": input_bold_exists,
        "sidecar_json_or_explicit_tr": bool(_path_exists(sidecar_path) or tr is not None),
        "sidecar_json_with_slice_timing": bool(_path_exists(sidecar_path) and sidecar.get("SliceTiming")),
        "t1w": _path_exists(request.t1w),
        "template": _path_exists(request.template),
        "atlas": _path_exists(request.atlas),
        "tr": tr is not None,
    }

    def mark_planned_outputs(spec: NativeFullStageSpec) -> None:
        for output in spec.produced_outputs:
            available[output] = True
        if any(
            output in spec.produced_outputs
            for output in (
                "bold_4d",
                "normalized_bold",
                "smoothed_bold",
                "residual_bold",
                "detrended_bold",
                "filtered_bold",
            )
        ):
            available["reference_image"] = True

    stage_results: list[NativeFullStageApiResult] = []
    for spec in iter_native_full_stage_specs():
        if not spec.enabled_by_default:
            stage_results.append(_plain_stage(spec, "skipped", warnings=list(spec.notes)))
            continue
        if not _stage_enabled(request, spec.stage_id, default=True):
            stage_results.append(_plain_stage(spec, "skipped", warnings=["stage disabled by DPARSF config or stage_overrides."]))
            continue
        if spec.stage_id == "dummy_scan_removal" and request.remove_first <= 0:
            stage_results.append(_plain_stage(spec, "skipped", warnings=["remove_first=0; stage is not needed."]))
            continue
        missing = [name for name in spec.required_inputs if not available.get(name, False)]
        if spec.stage_id == "slice_timing" and not request.enable_slice_timing:
            stage_results.append(_plain_stage(spec, "skipped", warnings=["slice timing disabled by request."]))
        elif missing:
            stage_results.append(
                _plain_stage(spec, "blocked", blocking_issues=[f"Missing required input: {item}" for item in missing])
            )
        else:
            stage_results.append(_plain_stage(spec, "planned"))
            mark_planned_outputs(spec)
    for stage in stage_results:
        if stage.stage_id == "functional_connectivity":
            # ROI count is not known until atlas extraction; retain the known
            # time dimension and plan conservatively for one ROI.
            shape = (input_shape[3] if len(input_shape) == 4 else 1, 1)
        else:
            shape = input_shape
        stage.result["compute_plan"] = plan_gpu_stage(
            stage.stage_id,
            input_shape=shape,
            policy=request.compute_policy,
        ).as_dict()
    return _build_response(
        project_id=project_id,
        request=request,
        run_id=run_id,
        run_dir=run_dir,
        dry_run=True,
        stage_results=stage_results,
        warnings=[*dparsf_warnings, "Dry-run only; no native preprocessing artifacts were created."],
    )


def _missing_confirmations(request: NativeFullPreprocRequest) -> list[str]:
    confirmations = request.confirmations
    missing: list[str] = []
    for name in (
        "confirm_reviewed_native_execution",
        "confirm_rawdata_readonly",
        "confirm_no_external_tools",
        "confirm_research_use_only",
        "confirm_no_clinical_use",
    ):
        if not bool(getattr(confirmations, name)):
            missing.append(name)
    return missing


def _run_stage(
    spec: NativeFullStageSpec,
    call: Callable[[], NativePreprocStageResult],
) -> tuple[NativeFullStageApiResult, NativePreprocStageResult | None]:
    _emit_stage_progress(spec.stage_id, "running")
    try:
        result = call()
    except Exception as exc:  # defensive truthfulness boundary
        api = _plain_stage(spec, "failed", errors=[str(exc)])
        _emit_stage_progress(spec.stage_id, "failed")
        return api, None
    validation_errors = validate_stage_result_artifacts(result)
    api = _result_to_api(spec, result, validation_errors=validation_errors)
    if validation_errors and result.status in {"succeeded", "warning"}:
        api.status = "failed"
        api.errors.extend(validation_errors)
    _emit_stage_progress(spec.stage_id, api.status)
    return api, result


def execute_native_full_preproc(
    project_id: str,
    request: NativeFullPreprocRequest,
    *,
    project_dir: str = "",
) -> NativeFullPreprocResponse:
    request, dparsf_warnings = _apply_dparsf_config(request)
    request = _with_inferred_subject_id(request)
    run_id = request.run_id or _new_run_id(project_id)
    root = _project_root(project_dir, project_id).resolve()
    run_dir = (
        Path(request.output_dir).expanduser().resolve()
        if request.output_dir
        else root / "preprocessing_native_runs" / run_id
    )

    setup_issues: list[str] = []
    if request.output_dir and not _is_within(run_dir, root):
        setup_issues.append("Native preprocessing output_dir must stay inside the project directory.")
    if _has_rawdata_part(run_dir):
        setup_issues.append("Native preprocessing output_dir must not be under rawdata.")
    setup_issues.extend(
        f"Missing native execution confirmation: {name}" for name in _missing_confirmations(request)
    )
    if setup_issues:
        stage_results = [
            _plain_stage(
                spec,
                "blocked",
                blocking_issues=setup_issues,
            )
            for spec in iter_native_full_stage_specs()
            if spec.enabled_by_default
        ]
        response = _build_response(
            project_id=project_id,
            request=request,
            run_id=run_id,
            run_dir=run_dir,
            dry_run=False,
            stage_results=stage_results,
            blocking_issues=setup_issues,
        )
        response.safety_flags = _safety_flags(dry_run=False, confirmations_ok=False)
        return response

    run_dir.mkdir(parents=True, exist_ok=True)
    context = NativePreprocRunContext.from_output_dir(
        run_dir,
        run_id=run_id,
        subject_id=request.subject_id,
        session_id=request.session_id,
    )
    specs = {spec.stage_id: spec for spec in iter_native_full_stage_specs()}
    sidecar_path = request.sidecar_json or _default_sidecar_path(request.input_bold)
    sidecar = _read_sidecar(sidecar_path)
    tr = _tr_from_request_or_sidecar(request, sidecar)
    stage_results: list[NativeFullStageApiResult] = []
    stage_native_results: dict[str, NativePreprocStageResult] = {}
    warnings: list[str] = list(dparsf_warnings)
    current_bold = _alias_nifti_input(run_dir, request.input_bold, "input_bold")
    motion_parameters = ""
    fd_timeseries = ""
    mean_functional = ""
    t1w_for_spatial = request.t1w
    wm_mask = ""
    csf_mask = ""
    atlas_for_fc = request.atlas
    roi_tsv = ""

    if not _path_exists(request.input_bold):
        result = _blocked_result(context, specs["input_validation"], issues=["Missing readable input_bold."])
        stage_results.append(_result_to_api(specs["input_validation"], result))
        for spec in iter_native_full_stage_specs():
            if spec.stage_id == "input_validation" or not spec.enabled_by_default:
                continue
            stage_results.append(
                _plain_stage(
                    spec,
                    "blocked",
                    blocking_issues=["input_validation did not provide a readable BOLD input."],
                )
            )
        manifest_path = run_dir / "native_full_run_manifest.json"
        response = _build_response(
            project_id=project_id,
            request=request,
            run_id=run_id,
            run_dir=run_dir,
            dry_run=False,
            stage_results=stage_results,
            blocking_issues=["Missing readable input_bold."],
            manifest_path=manifest_path,
        )
        atomic_write_json(manifest_path, response.model_dump(mode="json"), schema_version=1)
        return response

    result = _metadata_result(
        context,
        specs["input_validation"],
        metrics={
            "input_bold": request.input_bold,
            "input_bold_exists": True,
            "input_is_rawdata": _has_rawdata_part(Path(request.input_bold)),
        },
        warnings=["input path contains rawdata; native runner will not write there."]
        if _has_rawdata_part(Path(request.input_bold))
        else [],
    )
    stage_results.append(_result_to_api(specs["input_validation"], result))
    stage_native_results["input_validation"] = result

    stage_results.append(_plain_stage(specs["dicom_to_nifti"], "skipped", warnings=list(specs["dicom_to_nifti"].notes)))

    sidecar_issues: list[str] = []
    if not _path_exists(sidecar_path):
        sidecar_issues.append("Missing sidecar_json and no BOLD-neighbor sidecar was found.")
    if tr is None:
        sidecar_issues.append("Missing RepetitionTime and no explicit tr was provided.")
    if sidecar_issues:
        result = _blocked_result(context, specs["bids_sidecar_validation"], issues=sidecar_issues)
    else:
        result = _metadata_result(
            context,
            specs["bids_sidecar_validation"],
            metrics={
                "sidecar_json": sidecar_path,
                "tr": tr,
                "has_slice_timing": bool(sidecar.get("SliceTiming")),
            },
            warnings=[] if sidecar.get("SliceTiming") else ["SliceTiming is not present; slice_timing may block."],
        )
    stage_results.append(_result_to_api(specs["bids_sidecar_validation"], result))
    stage_native_results["bids_sidecar_validation"] = result

    if not _stage_enabled(request, "dummy_scan_removal", default=True):
        stage_results.append(_plain_stage(specs["dummy_scan_removal"], "skipped", warnings=["dummy_scan_removal disabled by DPARSF config or stage_overrides."]))
    elif request.remove_first > 0:
        api, native = _run_stage(
            specs["dummy_scan_removal"],
            lambda: run_dummy_scan_removal(
                current_bold,
                run_dir,
                remove_first=request.remove_first,
                run_id=run_id,
                subject_id=request.subject_id,
                session_id=request.session_id,
            ),
        )
        stage_results.append(api)
        if native:
            stage_native_results["dummy_scan_removal"] = native
            output = _artifact_path(native, "bold_4d")
            current_bold = _alias_nifti_input(run_dir, output, "dummy_scan_bold") or current_bold
    else:
        stage_results.append(_plain_stage(specs["dummy_scan_removal"], "skipped", warnings=["remove_first=0; stage is not needed."]))

    if not _stage_enabled(request, "slice_timing", default=True):
        stage_results.append(_plain_stage(specs["slice_timing"], "skipped", warnings=["slice_timing disabled by DPARSF config or stage_overrides."]))
    elif request.enable_slice_timing:
        if not sidecar.get("SliceTiming"):
            result = _blocked_result(
                context,
                specs["slice_timing"],
                issues=["SliceTiming is required for native slice timing correction."],
            )
            stage_results.append(_result_to_api(specs["slice_timing"], result))
        else:
            api, native = _run_stage(
                specs["slice_timing"],
                lambda: run_slice_timing_correction(
                    current_bold,
                    run_dir,
                    sidecar_path=sidecar_path,
                    reference_time=request.reference_time,
                    reference_slice_index=request.reference_slice_index,
                    run_id=run_id,
                    subject_id=request.subject_id,
                    session_id=request.session_id,
                ),
            )
            stage_results.append(api)
            if native:
                stage_native_results["slice_timing"] = native
                output = _artifact_path(native, "bold_4d")
                current_bold = _alias_nifti_input(run_dir, output, "slice_timing_bold") or current_bold
    else:
        stage_results.append(_plain_stage(specs["slice_timing"], "skipped", warnings=["slice timing disabled by request."]))

    if not _stage_enabled(request, "realignment", default=True):
        stage_results.append(_plain_stage(specs["realignment"], "skipped", warnings=["realignment disabled by DPARSF config or stage_overrides."]))
    else:
        api, native = _run_stage(
            specs["realignment"],
            lambda: run_realignment(
                current_bold,
                run_dir,
                reference_volume_index=request.reference_volume_index,
                run_id=run_id,
                subject_id=request.subject_id,
                session_id=request.session_id,
            ),
        )
        stage_results.append(api)
        if native and api.status not in {"failed", "blocked"}:
            stage_native_results["realignment"] = native
            current_bold = _alias_nifti_input(run_dir, _artifact_path(native, "bold_4d"), "realigned_bold") or current_bold
            motion_parameters = _artifact_path(native, "motion_parameters")
            mean_functional = _artifact_path(native, "mean_functional")

    if not _stage_enabled(request, "motion_qc", default=True):
        stage_results.append(_plain_stage(specs["motion_qc"], "skipped", warnings=["motion_qc disabled by DPARSF config or stage_overrides."]))
    elif motion_parameters:
        api, native = _run_stage(
            specs["motion_qc"],
            lambda: run_motion_qc(
                motion_parameters,
                run_dir,
                fd_threshold_mm=request.fd_threshold_mm,
                head_radius_mm=request.head_radius_mm,
                run_id=run_id,
                subject_id=request.subject_id,
                session_id=request.session_id,
            ),
        )
        stage_results.append(api)
        if native and api.status not in {"failed", "blocked"}:
            stage_native_results["motion_qc"] = native
            fd_timeseries = _artifact_path(native, "fd_timeseries")
    else:
        stage_results.append(_plain_stage(specs["motion_qc"], "blocked", blocking_issues=["Missing motion_parameters from realignment."]))

    if not _stage_enabled(request, "coregistration", default=True):
        stage_results.append(_plain_stage(specs["coregistration"], "skipped", warnings=["coregistration disabled by DPARSF config or stage_overrides."]))
    elif mean_functional and _path_exists(request.t1w):
        api, native = _run_stage(
            specs["coregistration"],
            lambda: run_coregistration(
                mean_functional,
                request.t1w,
                run_dir,
                run_id=run_id,
                subject_id=request.subject_id,
                session_id=request.session_id,
            ),
        )
        stage_results.append(api)
        if native and api.status not in {"failed", "blocked"}:
            stage_native_results["coregistration"] = native
            t1w_for_spatial = _artifact_path(native, "t1w") or t1w_for_spatial
    else:
        stage_results.append(_plain_stage(specs["coregistration"], "blocked", blocking_issues=["Missing mean_functional or t1w."]))

    if not _stage_enabled(request, "segmentation", default=True):
        stage_results.append(_plain_stage(specs["segmentation"], "skipped", warnings=["segmentation disabled by DPARSF config or stage_overrides."]))
    elif _path_exists(t1w_for_spatial):
        api, native = _run_stage(
            specs["segmentation"],
            lambda: run_segmentation(
                t1w_for_spatial,
                run_dir,
                run_id=run_id,
                subject_id=request.subject_id,
                session_id=request.session_id,
            ),
        )
        stage_results.append(api)
        if native and api.status not in {"failed", "blocked"}:
            stage_native_results["segmentation"] = native
            wm_paths = _artifact_paths(native, "wm_map")
            csf_paths = _artifact_paths(native, "csf_map")
            wm_mask = wm_paths[-1] if wm_paths else ""
            csf_mask = csf_paths[-1] if csf_paths else ""
    else:
        stage_results.append(_plain_stage(specs["segmentation"], "blocked", blocking_issues=["Missing t1w for segmentation."]))

    if not _stage_enabled(request, "normalization", default=True):
        stage_results.append(_plain_stage(specs["normalization"], "skipped", warnings=["normalization disabled by DPARSF config or stage_overrides."]))
    elif _path_exists(t1w_for_spatial) and _path_exists(request.template):
        api, native = _run_stage(
            specs["normalization"],
            lambda: run_affine_normalization(
                t1w_for_spatial,
                current_bold,
                request.template,
                run_dir,
                wm_map=wm_mask or None,
                csf_map=csf_mask or None,
                run_id=run_id,
                subject_id=request.subject_id,
                session_id=request.session_id,
            ),
        )
        stage_results.append(api)
        if native and api.status not in {"failed", "blocked"}:
            stage_native_results["normalization"] = native
            current_bold = _alias_nifti_input(run_dir, _artifact_path(native, "normalized_bold"), "normalized_bold") or current_bold
            normalized_wm_paths = _artifact_paths(native, "wm_map")
            normalized_csf_paths = _artifact_paths(native, "csf_map")
            wm_mask = normalized_wm_paths[-1] if normalized_wm_paths else wm_mask
            csf_mask = normalized_csf_paths[-1] if normalized_csf_paths else csf_mask
    else:
        stage_results.append(_plain_stage(specs["normalization"], "blocked", blocking_issues=["Missing t1w or template for affine normalization."]))

    if not _stage_enabled(request, "smoothing", default=True):
        stage_results.append(_plain_stage(specs["smoothing"], "skipped", warnings=["smoothing disabled by DPARSF config or stage_overrides."]))
    else:
        api, native = _run_stage(
            specs["smoothing"],
            lambda: run_smoothing(
                current_bold,
                run_dir,
                fwhm_mm=request.fwhm_mm,
                run_id=run_id,
                subject_id=request.subject_id,
                session_id=request.session_id,
                compute_policy=request.compute_policy,
            ),
        )
        stage_results.append(api)
        if native and api.status not in {"failed", "blocked"}:
            stage_native_results["smoothing"] = native
            current_bold = _alias_nifti_input(run_dir, _artifact_path(native, "smoothed_bold"), "smoothed_bold") or current_bold

    if not _stage_enabled(request, "nuisance_regression", default=True):
        stage_results.append(_plain_stage(specs["nuisance_regression"], "skipped", warnings=["nuisance_regression disabled by DPARSF config or stage_overrides."]))
    elif motion_parameters:
        api, native = _run_stage(
            specs["nuisance_regression"],
            lambda: run_nuisance_regression(
                current_bold,
                run_dir,
                motion_parameters=motion_parameters,
                wm_mask=wm_mask or None,
                csf_mask=csf_mask or None,
                include_wm=bool(request.include_wm and wm_mask),
                include_csf=bool(request.include_csf and csf_mask),
                include_global_signal=request.include_global_signal,
                polynomial_order=request.polynomial_order,
                fd_timeseries=fd_timeseries or None,
                scrub_threshold_mm=request.fd_threshold_mm,
                compute_policy=request.compute_policy,
                run_id=run_id,
                subject_id=request.subject_id,
                session_id=request.session_id,
            ),
        )
        stage_results.append(api)
        if native and api.status not in {"failed", "blocked"}:
            stage_native_results["nuisance_regression"] = native
            current_bold = _alias_nifti_input(run_dir, _artifact_path(native, "residual_bold"), "residual_bold") or current_bold
    else:
        stage_results.append(_plain_stage(specs["nuisance_regression"], "blocked", blocking_issues=["Missing motion_parameters."]))

    if not _stage_enabled(request, "detrending", default=True):
        stage_results.append(_plain_stage(specs["detrending"], "skipped", warnings=["detrending disabled by DPARSF config or stage_overrides."]))
    else:
        api, native = _run_stage(
            specs["detrending"],
            lambda: run_detrending(
                current_bold,
                run_dir,
                polynomial_order=request.polynomial_order,
                run_id=run_id,
                subject_id=request.subject_id,
                session_id=request.session_id,
            ),
        )
        stage_results.append(api)
        if native and api.status not in {"failed", "blocked"}:
            stage_native_results["detrending"] = native
            current_bold = _alias_nifti_input(run_dir, _artifact_path(native, "detrended_bold"), "detrended_bold") or current_bold

    if not _stage_enabled(request, "temporal_filtering", default=True):
        stage_results.append(_plain_stage(specs["temporal_filtering"], "skipped", warnings=["temporal_filtering disabled by DPARSF config or stage_overrides."]))
    elif tr is None:
        stage_results.append(_plain_stage(specs["temporal_filtering"], "blocked", blocking_issues=["Missing tr for temporal filtering."]))
    else:
        api, native = _run_stage(
            specs["temporal_filtering"],
            lambda: run_temporal_filtering(
                current_bold,
                run_dir,
                tr=tr,
                filter_type=request.temporal_filter_type,
                low_hz=request.low_hz,
                high_hz=request.high_hz,
                method=request.filtering_method,
                tr_source="request" if request.tr is not None else "sidecar",
                run_id=run_id,
                subject_id=request.subject_id,
                session_id=request.session_id,
                compute_policy=request.compute_policy,
            ),
        )
        stage_results.append(api)
        if native and api.status not in {"failed", "blocked"}:
            stage_native_results["temporal_filtering"] = native
            current_bold = _alias_nifti_input(run_dir, _artifact_path(native, "filtered_bold"), "filtered_bold") or current_bold

    if not _stage_enabled(request, "alff", default=True):
        stage_results.append(_plain_stage(specs["alff"], "skipped", warnings=["alff disabled by DPARSF config or stage_overrides."]))
    elif tr is None:
        stage_results.append(_plain_stage(specs["alff"], "blocked", blocking_issues=["Missing tr for ALFF."]))
    else:
        api, native = _run_stage(
            specs["alff"],
            lambda: run_alff(
                current_bold,
                run_dir,
                tr=tr,
                freq_band=(request.low_hz or 0.01, request.high_hz or 0.08),
                run_id=run_id,
                subject_id=request.subject_id,
                session_id=request.session_id,
                compute_policy=request.compute_policy,
            ),
        )
        stage_results.append(api)
        if native:
            stage_native_results["alff"] = native

    if not _stage_enabled(request, "falff", default=True):
        stage_results.append(_plain_stage(specs["falff"], "skipped", warnings=["falff disabled by DPARSF config or stage_overrides."]))
    elif tr is None:
        stage_results.append(_plain_stage(specs["falff"], "blocked", blocking_issues=["Missing tr for fALFF."]))
    else:
        api, native = _run_stage(
            specs["falff"],
            lambda: run_falff(
                current_bold,
                run_dir,
                tr=tr,
                freq_band=(request.low_hz or 0.01, request.high_hz or 0.08),
                run_id=run_id,
                subject_id=request.subject_id,
                session_id=request.session_id,
                compute_policy=request.compute_policy,
            ),
        )
        stage_results.append(api)
        if native:
            stage_native_results["falff"] = native

    if not _stage_enabled(request, "reho", default=True):
        stage_results.append(_plain_stage(specs["reho"], "skipped", warnings=["reho disabled by DPARSF config or stage_overrides."]))
    else:
        api, native = _run_stage(
            specs["reho"],
            lambda: run_reho(
                current_bold,
                run_dir,
                neighborhood=request.reho_neighborhood,
                run_id=run_id,
                subject_id=request.subject_id,
                session_id=request.session_id,
            ),
        )
        stage_results.append(api)
        if native:
            stage_native_results["reho"] = native

    if not _stage_enabled(request, "atlas_resampling", default=True):
        stage_results.append(_plain_stage(specs["atlas_resampling"], "skipped", warnings=["atlas_resampling disabled by DPARSF config or stage_overrides."]))
    elif _path_exists(request.atlas):
        api, native = _run_stage(
            specs["atlas_resampling"],
            lambda: run_atlas_resampling(
                request.atlas,
                current_bold,
                run_dir,
                run_id=run_id,
                subject_id=request.subject_id,
                session_id=request.session_id,
                compute_policy=request.compute_policy,
            ),
        )
        stage_results.append(api)
        if native and api.status not in {"failed", "blocked"}:
            stage_native_results["atlas_resampling"] = native
            atlas_for_fc = _artifact_path(native, "atlas_resampled") or atlas_for_fc
    else:
        stage_results.append(_plain_stage(specs["atlas_resampling"], "blocked", blocking_issues=["Missing atlas for atlas_resampling."]))

    if not _stage_enabled(request, "roi_timeseries", default=True):
        stage_results.append(_plain_stage(specs["roi_timeseries"], "skipped", warnings=["roi_timeseries disabled by DPARSF config or stage_overrides."]))
    elif _path_exists(atlas_for_fc):
        api, native = _run_stage(
            specs["roi_timeseries"],
            lambda: run_roi_timeseries(
                current_bold,
                atlas_for_fc,
                run_dir,
                labels_path=request.atlas_labels or None,
                atlas_name=request.atlas_name,
                run_id=run_id,
                subject_id=request.subject_id,
                session_id=request.session_id,
            ),
        )
        stage_results.append(api)
        if native and api.status not in {"failed", "blocked"}:
            stage_native_results["roi_timeseries"] = native
            roi_tsv = _artifact_path(native, "roi_timeseries")
    else:
        stage_results.append(_plain_stage(specs["roi_timeseries"], "blocked", blocking_issues=["Missing atlas_resampled for ROI extraction."]))

    if not _stage_enabled(request, "functional_connectivity", default=True):
        stage_results.append(_plain_stage(specs["functional_connectivity"], "skipped", warnings=["functional_connectivity disabled by DPARSF config or stage_overrides."]))
    elif roi_tsv:
        api, native = _run_stage(
            specs["functional_connectivity"],
            lambda: run_functional_connectivity(
                roi_tsv,
                run_dir,
                run_id=run_id,
                subject_id=request.subject_id,
                session_id=request.session_id,
                compute_policy=request.compute_policy,
            ),
        )
        stage_results.append(api)
        if native:
            stage_native_results["functional_connectivity"] = native
    else:
        stage_results.append(_plain_stage(specs["functional_connectivity"], "blocked", blocking_issues=["Missing ROI time series for FC."]))

    if not _stage_enabled(request, "subject_qc", default=True):
        stage_results.append(_plain_stage(specs["subject_qc"], "skipped", warnings=["subject_qc disabled by DPARSF config or stage_overrides."]))
    else:
        subject_qc = _metadata_result(
            context,
            specs["subject_qc"],
            metrics={
                "completed_stage_count": sum(1 for item in stage_results if item.status in {"succeeded", "warning"}),
                "blocked_stage_count": sum(1 for item in stage_results if item.status == "blocked"),
                "failed_stage_count": sum(1 for item in stage_results if item.status == "failed"),
            },
        )
        stage_results.append(_result_to_api(specs["subject_qc"], subject_qc))
        stage_native_results["subject_qc"] = subject_qc

    if not _stage_enabled(request, "group_summary", default=True):
        stage_results.append(_plain_stage(specs["group_summary"], "skipped", warnings=["group_summary disabled by DPARSF config or stage_overrides."]))
    else:
        api, native = _run_stage(
            specs["group_summary"],
            lambda: run_group_summary(
                run_dir,
                subject_summaries=[
                    {
                        "subject_id": request.subject_id or "unknown",
                        "status": "succeeded" if not any(item.status in {"blocked", "failed"} for item in stage_results) else "partial",
                    }
                ],
                run_id=run_id,
                subject_id=request.subject_id,
                session_id=request.session_id,
            ),
        )
        stage_results.append(api)
        if native:
            stage_native_results["group_summary"] = native

    safety_flags = _safety_flags(dry_run=False)
    validation_payload = build_full_run_validation_payload(
        project_id=project_id,
        run_id=run_id,
        created_at=_now_iso(),
        stage_results=stage_results,
        safety_flags=safety_flags,
    )
    validation_result: NativePreprocStageResult | None = None
    if _stage_enabled(request, "validation_report", default=True):
        validation_result = _write_report_stage(
            context,
            specs["validation_report"],
            payload=validation_payload,
            artifact_type="validation_report",
            filename="native_preproc_validation_report.json",
        )
        stage_results.append(_result_to_api(specs["validation_report"], validation_result))

    if _stage_enabled(request, "final_report", default=True):
        final_payload = {
            "project_id": project_id,
            "run_id": run_id,
            "created_at": _now_iso(),
            "backend": "native_python",
            "stage_results": [item.model_dump(mode="json") for item in stage_results],
            "validation_summary": validation_payload["summary"],
            "validation_report_path": _artifact_path(validation_result, "validation_report"),
            "report_consistency": {
                "manifest_is_authoritative": True,
                "final_report_excludes_its_own_artifact_by_construction": True,
                "stage_count_before_final_report": len(stage_results),
                "artifact_count_before_final_report": sum(len(item.output_artifacts) for item in stage_results),
            },
            "safety_flags": safety_flags,
            "limitations": validation_payload["limitations"],
        }
        final_result = _write_report_stage(
            context,
            specs["final_report"],
            payload=final_payload,
            artifact_type="final_report",
            filename="native_preproc_final_report.json",
        )
        stage_results.append(_result_to_api(specs["final_report"], final_result))

    manifest_path = run_dir / "native_full_run_manifest.json"
    response = _build_response(
        project_id=project_id,
        request=request,
        run_id=run_id,
        run_dir=run_dir,
        dry_run=False,
        stage_results=stage_results,
        warnings=warnings,
        manifest_path=manifest_path,
    )
    atomic_write_json(manifest_path, response.model_dump(mode="json"), schema_version=1)
    return response


def load_native_full_run_manifest(
    project_id: str,
    run_id: str,
    *,
    project_dir: str = "",
) -> NativeFullPreprocResponse:
    root = _project_root(project_dir, project_id)
    path = root / "preprocessing_native_runs" / run_id / "native_full_run_manifest.json"
    if not path.exists():
        return NativeFullPreprocResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            run_id=run_id,
            blocking_issues=["Native preprocessing run manifest not found."],
            safety_flags=_safety_flags(dry_run=False),
        )
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict) and "_schema_version" in payload and "data" in payload:
        payload = payload["data"]
    return NativeFullPreprocResponse.model_validate(payload)


__all__ = [
    "dry_run_native_full_preproc",
    "execute_native_full_preproc",
    "load_native_full_run_manifest",
]
