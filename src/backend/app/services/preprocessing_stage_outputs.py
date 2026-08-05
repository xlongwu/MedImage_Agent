"""Preprocessing Stage Output Registration Service — Phase 5F.

Registers sandbox SPM Slice Timing + Realign outputs as next-stage
preprocessing input. No additional execution. Rawdata unchanged.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC
from pathlib import Path
from typing import Any

from src.backend.app.runtime.atomic_file import atomic_write_json
from src.backend.app.schemas.preprocessing_stage_outputs import (
    StageOutputRegistrationRequest,
    StageOutputRegistrationResponse,
    registration_safety_flags,
)
from src.backend.app.services.mock_store import mock_store
from src.backend.app.services.preprocessing_artifact_registry import (
    REGISTRY_FILENAME,
    append_stage_output_artifacts,
    parse_bids_entities,
)
from src.backend.app.tools.motion_qc import (
    compute_motion_qc_for_subject,
    write_motion_qc_dataset_report,
)


def _now_iso() -> str:
    from datetime import datetime

    return datetime.now(UTC).isoformat()


def _write_json(path: Path, data: dict[str, Any]) -> None:
    atomic_write_json(path, data, schema_version=1)


def _run_dir(effective_project_dir: str, run_id: str) -> Path:
    if effective_project_dir:
        return Path(effective_project_dir) / "preprocessing_runs" / run_id
    return Path(f"outputs/preprocessing_runs/{run_id}")


def _append_registered_artifacts(
    *,
    project_id: str,
    run_id: str,
    effective_project_dir: str,
    stage_id: str,
    output_paths_by_type: dict[str, list[Path]],
    execution_id: str,
    backend: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    filtered = {
        artifact_type: paths for artifact_type, paths in output_paths_by_type.items() if paths
    }
    if not filtered:
        return
    run_dir = _run_dir(effective_project_dir, run_id)
    exec_dir = run_dir / "spm_exec" / execution_id
    provenance_path = (
        str(exec_dir / "provenance.json") if (exec_dir / "provenance.json").exists() else ""
    )
    qc_path = str(exec_dir / "qc.json") if (exec_dir / "qc.json").exists() else ""
    append_stage_output_artifacts(
        registry_path=run_dir / REGISTRY_FILENAME,
        project_id=project_id,
        preprocessing_run_id=run_id,
        stage_id=stage_id,
        output_paths_by_type=filtered,
        project_dir=effective_project_dir,
        source_execution_id=execution_id,
        backend=backend,
        provenance_path=provenance_path,
        qc_path=qc_path,
        metadata=metadata or {},
    )


def _subject_id_for_motion_file(path: Path) -> str:
    entities = parse_bids_entities(path)
    if entities.subject_id:
        return entities.subject_id
    for part in reversed(path.parts):
        if part.startswith("sub-"):
            return part
    stem = path.stem
    if stem.startswith("rp_"):
        stem = stem[3:]
    return stem.split("_")[0] or "unknown-subject"


def _compute_motion_qc_artifacts(
    *,
    motion_files: list[Path],
    effective_project_dir: str,
    run_id: str,
) -> tuple[list[Path], list[Path], list[Path], list[Path], list[str]]:
    if not motion_files:
        return (
            [],
            [],
            [],
            [],
            ["No motion parameter files found; motion QC could not be generated."],
        )
    run_dir = _run_dir(effective_project_dir, run_id)
    derivatives_dir = (
        Path(effective_project_dir) / "derivatives"
        if effective_project_dir
        else run_dir / "derivatives"
    )
    report_dir = run_dir / "reports"
    qc_jsons: list[Path] = []
    qc_markdowns: list[Path] = []
    fd_tsvs: list[Path] = []
    summaries: list[Path] = []
    warnings: list[str] = []

    for motion_file in motion_files:
        subject_id = _subject_id_for_motion_file(motion_file)
        result = compute_motion_qc_for_subject(
            subject_id=subject_id,
            motion_parameter_file=str(motion_file),
            derivatives_dir=str(derivatives_dir),
        )
        for output in result.get("outputs", []):
            path = Path(str(output))
            if path.name == "motion_qc.json":
                qc_jsons.append(path)
            elif path.name == "motion_qc.md":
                qc_markdowns.append(path)
            elif path.name == "fd_timeseries.tsv":
                fd_tsvs.append(path)
        if not result.get("ok"):
            warnings.extend(str(item) for item in result.get("errors", []))

    dataset_report = write_motion_qc_dataset_report(str(derivatives_dir), str(report_dir))
    for output in dataset_report.get("outputs", []):
        path = Path(str(output))
        if path.name == "motion_qc_summary.json":
            summaries.append(path)
        elif path.suffix.lower() == ".md":
            qc_markdowns.append(path)
    warnings.extend(str(item) for item in dataset_report.get("warnings", []))
    warnings.extend(str(item) for item in dataset_report.get("errors", []))
    return qc_jsons, fd_tsvs, summaries, qc_markdowns, warnings


def register_sandbox_spm_outputs(
    project_id: str, run_id: str, request: StageOutputRegistrationRequest, *, project_dir: str = ""
) -> StageOutputRegistrationResponse:
    blocking: list[str] = []
    warnings: list[str] = []
    if not request.execution_id:
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["execution_id is required."],
            safety_flags=registration_safety_flags(),
        )

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")

    # Locate execution directory
    exec_dir = (
        Path(effective_pd) / "preprocessing_runs" / run_id / "spm_exec" / request.execution_id
    )
    if not exec_dir.exists():
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            preprocessing_run_id=run_id,
            execution_id=request.execution_id,
            blocking_issues=[f"Execution dir not found: {exec_dir}"],
            safety_flags=registration_safety_flags(),
        )

    # Verify execution succeeded (or fake-runner success)
    manifest_path = exec_dir / "manifest.json"
    if manifest_path.exists():
        mf = json.loads(manifest_path.read_text())
        if mf.get("status") not in ("succeeded", "generated", "dry_run_preview"):
            blocking.append(f"Execution status is {mf.get('status')}, not succeeded.")

    sandbox_out = exec_dir / "sandbox_output"
    if not sandbox_out.exists():
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=[f"Sandbox output dir not found: {sandbox_out}"],
            safety_flags=registration_safety_flags(),
        )

    # Discover output BOLD files (ra/r/a prefixes from SPM)
    bold_outputs: list[Path] = []
    motion_files: list[Path] = []
    mean_images: list[Path] = []
    for p in sorted(sandbox_out.rglob("*")):
        if not p.is_file():
            continue
        name = p.name
        if p.suffix in (".nii", ".gz") or "".join(p.suffixes).lower() in (".nii", ".nii.gz"):
            if name.lower().startswith(("ra", "r", "a")) and (
                "bold" in name.lower() or "rest" in name.lower()
            ):
                bold_outputs.append(p)
            elif name.lower().startswith("mean"):
                mean_images.append(p)
        elif name.startswith("rp_") and name.endswith(".txt"):
            motion_files.append(p)

    if not bold_outputs:
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["No output BOLD files found in sandbox output."],
            safety_flags=registration_safety_flags(),
        )

    # Create stage output registry
    stage_out_id = (
        "so-"
        + hashlib.sha256(f"{project_id}:{run_id}:{request.execution_id}".encode()).hexdigest()[:10]
    )
    reg_dir = (
        Path(effective_pd)
        / "preprocessing_runs"
        / run_id
        / "registered_stage_outputs"
        / stage_out_id
        if effective_pd
        else Path(f"outputs/stage_outputs/{stage_out_id}")
    )
    reg_dir.mkdir(parents=True, exist_ok=True)

    _write_json(
        reg_dir / "stage_output_registry.json",
        {
            "stage_output_id": stage_out_id,
            "source_execution": request.execution_id,
            "stage": "slice_timing_realign",
            "status": "registered",
            "created_at": _now_iso(),
        },
    )
    motion_qc_jsons, fd_tsvs, motion_qc_summaries, motion_qc_markdowns, motion_qc_warnings = (
        _compute_motion_qc_artifacts(
            motion_files=motion_files,
            effective_project_dir=effective_pd,
            run_id=run_id,
        )
    )
    warnings.extend(motion_qc_warnings)

    _write_json(
        reg_dir / "next_stage_input_manifest.json",
        {
            "next_stage_input_dir": str(sandbox_out),
            "bold_count": len(bold_outputs),
            "motion_files": [str(f) for f in motion_files],
            "mean_images": [str(f) for f in mean_images],
            "motion_qc_jsons": [str(f) for f in motion_qc_jsons],
            "fd_timeseries": [str(f) for f in fd_tsvs],
            "motion_qc_summaries": [str(f) for f in motion_qc_summaries],
        },
    )
    _write_json(
        reg_dir / "subject_output_summary.json",
        {"total": len(bold_outputs), "outputs": [str(p) for p in bold_outputs]},
    )
    (reg_dir / "README.md").write_text(
        "# Stage Output Registration\nSandbox outputs registered. No additional execution. Rawdata unchanged.\n"
    )
    _append_registered_artifacts(
        project_id=project_id,
        run_id=run_id,
        effective_project_dir=effective_pd,
        stage_id="realignment",
        output_paths_by_type={
            "realigned_bold": bold_outputs,
            "motion_parameters": motion_files,
            "mean_bold": mean_images,
            "qc_json": motion_qc_jsons,
            "fd_timeseries": fd_tsvs,
            "motion_qc_summary": motion_qc_summaries,
            "qc_markdown": motion_qc_markdowns,
        },
        execution_id=request.execution_id,
        backend="spm12",
        metadata={
            "stage_output_id": stage_out_id,
            "registration_stage": "slice_timing_realign",
            "motion_qc_generated": bool(fd_tsvs),
        },
    )

    # Update run metadata
    if isinstance(project.metadata, dict):
        project.metadata["current_functional_input_source"] = "sandbox_spm_slice_timing_realign"
        project.metadata["current_functional_input_dir"] = str(sandbox_out)
        project.metadata["next_stage_input_registered"] = stage_out_id

    return StageOutputRegistrationResponse(
        ok=True,
        status="registered",
        project_id=project_id,
        preprocessing_run_id=run_id,
        execution_id=request.execution_id,
        registered_stage_output_id=stage_out_id,
        stage_output_dir=str(reg_dir),
        next_stage_input_dir=str(sandbox_out),
        subject_count=len(bold_outputs),
        registered_bold_outputs=[str(p) for p in bold_outputs],
        motion_files=[str(f) for f in motion_files],
        mean_images=[str(f) for f in mean_images],
        warnings=warnings,
        next_actions=[
            "Review registered outputs and motion QC.",
            "Plan nuisance regression with motion parameters.",
        ],
        safety_flags=registration_safety_flags(),
    )


def register_coreg_norm_outputs(
    project_id: str, run_id: str, request: StageOutputRegistrationRequest, *, project_dir: str = ""
) -> StageOutputRegistrationResponse:
    blocking: list[str] = []
    _warnings: list[str] = []
    if not request.execution_id:
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["execution_id is required."],
            safety_flags=registration_safety_flags(),
        )

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")

    exec_dir = (
        Path(effective_pd) / "preprocessing_runs" / run_id / "spm_exec" / request.execution_id
    )
    if not exec_dir.exists():
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            preprocessing_run_id=run_id,
            blocking_issues=[f"Execution dir not found: {exec_dir}"],
            safety_flags=registration_safety_flags(),
        )

    manifest_path = exec_dir / "manifest.json"
    if manifest_path.exists():
        mf = json.loads(manifest_path.read_text())
        if mf.get("status") not in ("succeeded", "generated"):
            blocking.append(f"Execution status is {mf.get('status')}, not succeeded.")

    sandbox_out = exec_dir / "sandbox_output"
    if not sandbox_out.exists():
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=[f"Sandbox output dir not found: {sandbox_out}"],
            safety_flags=registration_safety_flags(),
        )

    nifti_outputs = [p for p in sorted(sandbox_out.rglob("*.nii*")) if p.is_file()]
    norm_bolds = [
        p
        for p in nifti_outputs
        if ("bold" in p.name.lower() or "rest" in p.name.lower()) and p.name.lower().startswith("w")
    ]
    t1w_outputs = [
        p
        for p in nifti_outputs
        if "t1" in p.name.lower() and not p.name.lower().startswith(("c1", "c2", "c3", "y_"))
    ]
    seg_maps = [
        p
        for p in nifti_outputs
        if p.name.lower().startswith(("c1", "c2", "c3", "y_"))
        or "deformation" in p.name.lower()
        or "segmentation" in p.name.lower()
    ]

    if not norm_bolds and not t1w_outputs and not seg_maps:
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["No coregistration, segmentation, or normalization outputs found."],
            safety_flags=registration_safety_flags(),
        )

    stage_out_id = (
        "cn-so-"
        + hashlib.sha256(f"{project_id}:{run_id}:{request.execution_id}".encode()).hexdigest()[:10]
    )
    reg_dir = (
        Path(effective_pd)
        / "preprocessing_runs"
        / run_id
        / "registered_stage_outputs"
        / stage_out_id
        if effective_pd
        else Path(f"outputs/stage_outputs/{stage_out_id}")
    )
    reg_dir.mkdir(parents=True, exist_ok=True)

    _write_json(
        reg_dir / "coreg_norm_stage_output_registry.json",
        {
            "stage_output_id": stage_out_id,
            "source_execution": request.execution_id,
            "stage": "coreg_norm",
            "status": "registered",
        },
    )
    _write_json(
        reg_dir / "next_stage_input_manifest.json",
        {
            "next_stage_input_dir": str(sandbox_out),
            "func_count": len(norm_bolds),
            "t1w_count": len(t1w_outputs),
            "segmentation_maps": len(seg_maps),
        },
    )
    (reg_dir / "README.md").write_text("# Coreg/Norm Stage Output Registration\n")
    if t1w_outputs:
        _append_registered_artifacts(
            project_id=project_id,
            run_id=run_id,
            effective_project_dir=effective_pd,
            stage_id="t1_coregistration",
            output_paths_by_type={"coregistered_t1w": t1w_outputs},
            execution_id=request.execution_id,
            backend="spm12",
            metadata={"stage_output_id": stage_out_id, "registration_stage": "coreg_norm"},
        )
    if seg_maps:
        _append_registered_artifacts(
            project_id=project_id,
            run_id=run_id,
            effective_project_dir=effective_pd,
            stage_id="segmentation",
            output_paths_by_type={"segmentation_maps": seg_maps},
            execution_id=request.execution_id,
            backend="spm12",
            metadata={"stage_output_id": stage_out_id, "registration_stage": "coreg_norm"},
        )
    if norm_bolds:
        _append_registered_artifacts(
            project_id=project_id,
            run_id=run_id,
            effective_project_dir=effective_pd,
            stage_id="normalization",
            output_paths_by_type={"normalized_bold": norm_bolds},
            execution_id=request.execution_id,
            backend="spm12",
            metadata={"stage_output_id": stage_out_id, "registration_stage": "coreg_norm"},
        )

    if isinstance(project.metadata, dict):
        project.metadata["current_functional_input_source"] = "sandbox_spm_coreg_norm"
        project.metadata["current_functional_input_dir"] = str(sandbox_out)

    return StageOutputRegistrationResponse(
        ok=True,
        status="registered",
        project_id=project_id,
        preprocessing_run_id=run_id,
        execution_id=request.execution_id,
        registered_stage_output_id=stage_out_id,
        stage_output_dir=str(reg_dir),
        next_stage_input_dir=str(sandbox_out),
        subject_count=len(norm_bolds),
        registered_bold_outputs=[str(p) for p in norm_bolds],
        motion_files=[str(p) for p in t1w_outputs],
        mean_images=[str(p) for p in seg_maps],
        next_actions=["Review outputs.", "Plan smoothing dry-run."],
        safety_flags=registration_safety_flags(),
    )


def register_smoothing_outputs(
    project_id: str, run_id: str, request: StageOutputRegistrationRequest, *, project_dir: str = ""
) -> StageOutputRegistrationResponse:
    if not request.execution_id:
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["execution_id is required."],
            safety_flags=registration_safety_flags(),
        )

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")

    exec_dir = (
        Path(effective_pd) / "preprocessing_runs" / run_id / "spm_exec" / request.execution_id
    )
    if not exec_dir.exists():
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=[f"Execution dir not found: {exec_dir}"],
            safety_flags=registration_safety_flags(),
        )

    manifest_path = exec_dir / "manifest.json"
    if manifest_path.exists():
        mf = json.loads(manifest_path.read_text())
        if mf.get("status") not in ("succeeded", "generated"):
            return StageOutputRegistrationResponse(
                ok=False,
                status="blocked",
                project_id=project_id,
                blocking_issues=[f"Execution not succeeded: {mf.get('status')}"],
                safety_flags=registration_safety_flags(),
            )

    sandbox_out = exec_dir / "sandbox_output"
    if not sandbox_out.exists():
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["Sandbox output dir not found."],
            safety_flags=registration_safety_flags(),
        )

    smoothed = [
        p
        for p in sorted(sandbox_out.rglob("*.nii*"))
        if p.is_file() and ("bold" in p.name.lower() or "rest" in p.name.lower())
    ]
    if not smoothed:
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["No smoothed outputs found."],
            safety_flags=registration_safety_flags(),
        )

    stage_out_id = (
        "sm-so-"
        + hashlib.sha256(f"{project_id}:{run_id}:{request.execution_id}".encode()).hexdigest()[:10]
    )
    reg_dir = (
        Path(effective_pd)
        / "preprocessing_runs"
        / run_id
        / "registered_stage_outputs"
        / stage_out_id
        if effective_pd
        else Path(f"outputs/stage_outputs/{stage_out_id}")
    )
    reg_dir.mkdir(parents=True, exist_ok=True)

    _write_json(
        reg_dir / "smoothing_stage_output_registry.json",
        {
            "stage_output_id": stage_out_id,
            "source_execution": request.execution_id,
            "stage": "smoothing",
        },
    )
    _write_json(
        reg_dir / "next_stage_input_manifest.json",
        {"next_stage_input_dir": str(sandbox_out), "smoothed_count": len(smoothed)},
    )
    (reg_dir / "README.md").write_text("# Smoothing Stage Output Registration\n")
    _append_registered_artifacts(
        project_id=project_id,
        run_id=run_id,
        effective_project_dir=effective_pd,
        stage_id="spatial_smoothing",
        output_paths_by_type={"smoothed_bold": smoothed},
        execution_id=request.execution_id,
        backend="spm12",
        metadata={"stage_output_id": stage_out_id},
    )

    if isinstance(project.metadata, dict):
        project.metadata["current_functional_input_source"] = "sandbox_spm_smoothing"
        project.metadata["current_functional_input_dir"] = str(sandbox_out)

    return StageOutputRegistrationResponse(
        ok=True,
        status="registered",
        project_id=project_id,
        preprocessing_run_id=run_id,
        execution_id=request.execution_id,
        registered_stage_output_id=stage_out_id,
        stage_output_dir=str(reg_dir),
        next_stage_input_dir=str(sandbox_out),
        subject_count=len(smoothed),
        registered_bold_outputs=[str(p) for p in smoothed],
        next_actions=["Review outputs.", "Plan nuisance regression dry-run."],
        safety_flags=registration_safety_flags(),
    )


def register_nuisance_outputs(
    project_id: str, run_id: str, request: StageOutputRegistrationRequest, *, project_dir: str = ""
) -> StageOutputRegistrationResponse:
    if not request.execution_id:
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["execution_id is required."],
            safety_flags=registration_safety_flags(),
        )

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")

    exec_dir = (
        Path(effective_pd) / "preprocessing_runs" / run_id / "spm_exec" / request.execution_id
    )
    if not exec_dir.exists():
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=[f"Execution dir not found: {exec_dir}"],
            safety_flags=registration_safety_flags(),
        )

    manifest_path = exec_dir / "manifest.json"
    metadata_only = False
    if manifest_path.exists():
        mf = json.loads(manifest_path.read_text())
        metadata_only = mf.get("metadata_only", False)
        if mf.get("status") not in ("succeeded", "warning", "generated"):
            return StageOutputRegistrationResponse(
                ok=False,
                status="blocked",
                project_id=project_id,
                blocking_issues=[f"Execution not succeeded: {mf.get('status')}"],
                safety_flags=registration_safety_flags(),
            )

    sandbox_out = exec_dir / "sandbox_output"
    if not sandbox_out.exists():
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["Sandbox output dir not found."],
            safety_flags=registration_safety_flags(),
        )

    # For metadata-only execution, register as not_ready
    stage_out_id = (
        "nr-so-"
        + hashlib.sha256(f"{project_id}:{run_id}:{request.execution_id}".encode()).hexdigest()[:10]
    )
    reg_dir = (
        Path(effective_pd)
        / "preprocessing_runs"
        / run_id
        / "registered_stage_outputs"
        / stage_out_id
        if effective_pd
        else Path(f"outputs/stage_outputs/{stage_out_id}")
    )
    reg_dir.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    if metadata_only:
        warnings.append(
            "Nuisance regression was metadata-only; numerical regression not yet applied."
        )
        _write_json(
            reg_dir / "nuisance_stage_output_registry.json",
            {
                "stage_output_id": stage_out_id,
                "status": "not_ready_for_filtering",
                "metadata_only": True,
            },
        )
    else:
        _write_json(
            reg_dir / "nuisance_stage_output_registry.json",
            {"stage_output_id": stage_out_id, "status": "registered"},
        )
        denoised = [p for p in sorted(sandbox_out.rglob("*.nii*")) if p.is_file()]
        confounds = [p for p in sorted(sandbox_out.rglob("*.tsv")) if p.is_file()]
        _append_registered_artifacts(
            project_id=project_id,
            run_id=run_id,
            effective_project_dir=effective_pd,
            stage_id="nuisance_regression",
            output_paths_by_type={
                "denoised_bold": denoised,
                "confounds_tsv": confounds,
            },
            execution_id=request.execution_id,
            backend="python",
            metadata={"stage_output_id": stage_out_id},
        )

    (reg_dir / "README.md").write_text("# Nuisance Regression Output Registration\n")

    if isinstance(project.metadata, dict):
        project.metadata["current_functional_input_source"] = "sandbox_python_nuisance_regression"
        if not metadata_only:
            project.metadata["current_functional_input_dir"] = str(sandbox_out)

    return StageOutputRegistrationResponse(
        ok=True,
        status="registered" if not metadata_only else "warning",
        project_id=project_id,
        preprocessing_run_id=run_id,
        execution_id=request.execution_id,
        registered_stage_output_id=stage_out_id,
        stage_output_dir=str(reg_dir),
        next_stage_input_dir=str(sandbox_out) if not metadata_only else "",
        warnings=warnings,
        next_actions=[
            "Review status.",
            "Plan temporal filtering dry-run."
            if not metadata_only
            else "Numerical regression needed before filtering.",
        ],
        safety_flags=registration_safety_flags(),
    )


def register_filtering_outputs(
    project_id: str, run_id: str, request: StageOutputRegistrationRequest, *, project_dir: str = ""
) -> StageOutputRegistrationResponse:
    if not request.execution_id:
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["execution_id is required."],
            safety_flags=registration_safety_flags(),
        )

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")

    exec_dir = (
        Path(effective_pd) / "preprocessing_runs" / run_id / "spm_exec" / request.execution_id
    )
    if not exec_dir.exists():
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=[f"Execution dir not found: {exec_dir}"],
            safety_flags=registration_safety_flags(),
        )

    manifest_path = exec_dir / "manifest.json"
    metadata_only = False
    if manifest_path.exists():
        mf = json.loads(manifest_path.read_text())
        metadata_only = mf.get("metadata_only", False)

    sandbox_out = exec_dir / "sandbox_output"
    if not sandbox_out.exists():
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["Sandbox output dir not found."],
            safety_flags=registration_safety_flags(),
        )

    stage_out_id = (
        "tf-so-"
        + hashlib.sha256(f"{project_id}:{run_id}:{request.execution_id}".encode()).hexdigest()[:10]
    )
    reg_dir = (
        Path(effective_pd)
        / "preprocessing_runs"
        / run_id
        / "registered_stage_outputs"
        / stage_out_id
        if effective_pd
        else Path(f"outputs/stage_outputs/{stage_out_id}")
    )
    reg_dir.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    if metadata_only:
        warnings.append("Filtering was metadata-only; not ready for ALFF/ReHo.")

    _write_json(
        reg_dir / "filtering_stage_output_registry.json",
        {
            "stage_output_id": stage_out_id,
            "status": "registered" if not metadata_only else "not_ready_for_alff_reho",
        },
    )
    (reg_dir / "README.md").write_text("# Temporal Filtering Output Registration\n")
    if not metadata_only:
        filtered = [p for p in sorted(sandbox_out.rglob("*.nii*")) if p.is_file()]
        _append_registered_artifacts(
            project_id=project_id,
            run_id=run_id,
            effective_project_dir=effective_pd,
            stage_id="temporal_filtering",
            output_paths_by_type={"filtered_bold": filtered},
            execution_id=request.execution_id,
            backend="python",
            metadata={"stage_output_id": stage_out_id},
        )

    if isinstance(project.metadata, dict):
        project.metadata["current_functional_input_source"] = "sandbox_python_temporal_filtering"
        if not metadata_only:
            project.metadata["current_functional_input_dir"] = str(sandbox_out)

    return StageOutputRegistrationResponse(
        ok=True,
        status="registered" if not metadata_only else "warning",
        project_id=project_id,
        preprocessing_run_id=run_id,
        execution_id=request.execution_id,
        registered_stage_output_id=stage_out_id,
        stage_output_dir=str(reg_dir),
        next_stage_input_dir=str(sandbox_out) if not metadata_only else "",
        warnings=warnings,
        next_actions=[
            "Review.",
            "Plan ALFF/ReHo dry-run."
            if not metadata_only
            else "Real filtering needed before ALFF/ReHo.",
        ],
        safety_flags=registration_safety_flags(),
    )


def register_alff_reho_outputs(
    project_id: str, run_id: str, request: StageOutputRegistrationRequest, *, project_dir: str = ""
) -> StageOutputRegistrationResponse:
    if not request.execution_id:
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["execution_id is required."],
            safety_flags=registration_safety_flags(),
        )

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")

    exec_dir = (
        Path(effective_pd) / "preprocessing_runs" / run_id / "spm_exec" / request.execution_id
    )
    if not exec_dir.exists():
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=[f"Execution dir not found: {exec_dir}"],
            safety_flags=registration_safety_flags(),
        )

    sandbox_out = exec_dir / "sandbox_output"
    if not sandbox_out.exists():
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["Sandbox output not found."],
            safety_flags=registration_safety_flags(),
        )

    stage_out_id = (
        "ar-so-"
        + hashlib.sha256(f"{project_id}:{run_id}:{request.execution_id}".encode()).hexdigest()[:10]
    )
    reg_dir = (
        Path(effective_pd)
        / "preprocessing_runs"
        / run_id
        / "registered_stage_outputs"
        / stage_out_id
        if effective_pd
        else Path(f"outputs/stage_outputs/{stage_out_id}")
    )
    reg_dir.mkdir(parents=True, exist_ok=True)

    nifti_outputs = [p for p in sorted(sandbox_out.rglob("*.nii*")) if p.is_file()]
    alff_files = [
        p
        for p in nifti_outputs
        if "desc-alff_map" in p.name.lower()
        or p.name.lower().startswith("alff_")
        or p.name.lower() in {"alff.nii", "alff.nii.gz"}
    ]
    falff_files = [
        p
        for p in nifti_outputs
        if "desc-falff_map" in p.name.lower()
        or p.name.lower().startswith(("falff_", "falff"))
        or p.name.lower() in {"falff.nii", "falff.nii.gz"}
    ]
    reho_files = [
        p
        for p in nifti_outputs
        if "desc-reho_map" in p.name.lower()
        or p.name.lower().startswith("reho_")
        or p.name.lower() in {"reho.nii", "reho.nii.gz"}
    ]
    alff_provenance = [p for p in sorted(sandbox_out.rglob("*alff*provenance.json")) if p.is_file()]
    reho_provenance = [p for p in sorted(sandbox_out.rglob("*reho*provenance.json")) if p.is_file()]
    stage_manifests = [
        p
        for p in [
            exec_dir / "manifest.json",
            exec_dir / "metric_plan.json",
            exec_dir / "subject_status.json",
        ]
        if p.exists()
    ]
    metric_ready = len(alff_files) > 0 or len(falff_files) > 0 or len(reho_files) > 0

    _write_json(
        reg_dir / "alff_reho_stage_output_registry.json",
        {
            "stage_output_id": stage_out_id,
            "metric_outputs_ready": metric_ready,
            "alff_count": len(alff_files),
            "falff_count": len(falff_files),
            "reho_count": len(reho_files),
        },
    )
    (reg_dir / "README.md").write_text("# ALFF/ReHo Output Registration\n")
    _append_registered_artifacts(
        project_id=project_id,
        run_id=run_id,
        effective_project_dir=effective_pd,
        stage_id="alff_falff",
        output_paths_by_type={
            "alff_map": alff_files,
            "falff_map": falff_files,
            "provenance_json": alff_provenance,
            "stage_manifest": stage_manifests,
        },
        execution_id=request.execution_id,
        backend="python",
        metadata={"stage_output_id": stage_out_id},
    )
    _append_registered_artifacts(
        project_id=project_id,
        run_id=run_id,
        effective_project_dir=effective_pd,
        stage_id="reho",
        output_paths_by_type={
            "reho_map": reho_files,
            "provenance_json": reho_provenance,
            "stage_manifest": stage_manifests,
        },
        execution_id=request.execution_id,
        backend="python",
        metadata={"stage_output_id": stage_out_id},
    )

    return StageOutputRegistrationResponse(
        ok=True,
        status="registered" if metric_ready else "warning",
        project_id=project_id,
        preprocessing_run_id=run_id,
        execution_id=request.execution_id,
        registered_stage_output_id=stage_out_id,
        stage_output_dir=str(reg_dir),
        registered_bold_outputs=[str(p) for p in [*alff_files, *falff_files, *reho_files]],
        warnings=[]
        if metric_ready
        else ["ALFF/ReHo execution was metadata-only; metric maps not generated."],
        next_actions=["Review outputs.", "Plan FC dry-run using filtered functional inputs."],
        safety_flags=registration_safety_flags(),
    )


def register_fc_outputs(
    project_id: str, run_id: str, request: StageOutputRegistrationRequest, *, project_dir: str = ""
) -> StageOutputRegistrationResponse:
    if not request.execution_id:
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["execution_id is required."],
            safety_flags=registration_safety_flags(),
        )

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")

    exec_dir = (
        Path(effective_pd) / "preprocessing_runs" / run_id / "spm_exec" / request.execution_id
    )
    if not exec_dir.exists():
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=[f"Execution dir not found: {exec_dir}"],
            safety_flags=registration_safety_flags(),
        )

    sandbox_out = exec_dir / "sandbox_output"
    if not sandbox_out.exists():
        return StageOutputRegistrationResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["Sandbox output not found."],
            safety_flags=registration_safety_flags(),
        )

    fc_files = [
        p
        for p in sorted(sandbox_out.rglob("*"))
        if p.is_file()
        and (
            p.name.startswith("correlation_matrix.")
            or p.name.endswith("_desc-fc_matrix.npy")
            or p.name.endswith("_desc-fc_matrix.tsv")
            or p.name.startswith("FC_matrix_")
        )
    ]
    fz_files = [
        p
        for p in sorted(sandbox_out.rglob("*"))
        if p.is_file()
        and (
            p.name.startswith("fisher_z_matrix.")
            or p.name.endswith("_desc-fisherz_matrix.npy")
            or p.name.endswith("_desc-fisherz_matrix.tsv")
            or p.name.startswith("FC_FisherZ_")
        )
    ]
    roi_ts_files = [p for p in sorted(sandbox_out.rglob("roi_timeseries.tsv")) if p.is_file()]
    label_files = [
        p
        for p in sorted(sandbox_out.rglob("*"))
        if p.is_file() and p.name in {"labels.json", "labels.tsv", "roi_definitions.json"}
    ]
    provenance_files = [p for p in sorted(sandbox_out.rglob("*provenance.json")) if p.is_file()]
    ready = len(fc_files) > 0

    stage_out_id = (
        "fc-so-"
        + hashlib.sha256(f"{project_id}:{run_id}:{request.execution_id}".encode()).hexdigest()[:10]
    )
    reg_dir = (
        Path(effective_pd)
        / "preprocessing_runs"
        / run_id
        / "registered_stage_outputs"
        / stage_out_id
        if effective_pd
        else Path(f"outputs/stage_outputs/{stage_out_id}")
    )
    reg_dir.mkdir(parents=True, exist_ok=True)

    _write_json(
        reg_dir / "fc_stage_output_registry.json",
        {
            "stage_output_id": stage_out_id,
            "fc_outputs_ready": ready,
            "fc_matrix_count": len(fc_files),
            "fisher_z_count": len(fz_files),
        },
    )
    (reg_dir / "README.md").write_text("# FC Output Registration\n")
    _append_registered_artifacts(
        project_id=project_id,
        run_id=run_id,
        effective_project_dir=effective_pd,
        stage_id="functional_connectivity",
        output_paths_by_type={
            "roi_timeseries": roi_ts_files,
            "fc_matrix": fc_files,
            "fisher_z_matrix": fz_files,
            "roi_labels": label_files,
            "provenance_json": provenance_files,
        },
        execution_id=request.execution_id,
        backend="python",
        metadata={"stage_output_id": stage_out_id},
    )

    return StageOutputRegistrationResponse(
        ok=True,
        status="registered" if ready else "warning",
        project_id=project_id,
        preprocessing_run_id=run_id,
        execution_id=request.execution_id,
        registered_stage_output_id=stage_out_id,
        stage_output_dir=str(reg_dir),
        registered_bold_outputs=[str(p) for p in fc_files],
        warnings=[] if ready else ["FC execution was metadata-only; no matrices generated."],
        next_actions=["Review FC outputs.", "Group analysis requires explicit opt-in."],
        safety_flags=registration_safety_flags(),
    )
