"""Shared helpers for native preprocessing stage modules."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.backend.app.native_preproc.orchestrator.artifact_registry import write_stage_sidecars
from src.backend.app.native_preproc.orchestrator.state import (
    NativePreprocRunContext,
    package_versions,
    utc_now_iso,
)
from src.backend.app.schemas.native_preproc import (
    NativePreprocCapabilityLevel,
    NativePreprocProvenance,
    NativePreprocQC,
    NativePreprocStageId,
    NativePreprocStageResult,
    NativePreprocStageStatus,
)


def context_from_output_dir(
    output_dir: str | Path,
    *,
    run_id: str = "native_preproc_run",
    subject_id: str = "",
    session_id: str = "",
) -> NativePreprocRunContext:
    return NativePreprocRunContext.from_output_dir(
        output_dir,
        run_id=run_id,
        subject_id=subject_id,
        session_id=session_id,
    )


def provenance(
    *,
    stage_id: NativePreprocStageId,
    parameters: dict[str, Any],
    input_artifact_ids: list[str] | None = None,
    output_checksums: dict[str, str] | None = None,
    warnings: list[str] | None = None,
    dtype: str = "float32",
    backend: str = "native_python",
    subject_id: str = "",
    session_id: str = "",
) -> NativePreprocProvenance:
    return NativePreprocProvenance(
        algorithm_id=f"native_preproc.{stage_id}",
        algorithm_version="phase02_v1",
        implementation="native_python",
        input_artifact_ids=input_artifact_ids or [],
        parameters=parameters,
        backend=backend,  # type: ignore[arg-type]
        precision=dtype,
        dtype=dtype,
        package_versions=package_versions("numpy", "scipy", "nibabel", "cupy"),
        warnings=warnings or [],
        output_checksums=output_checksums or {},
        subject_id=subject_id,
        session_id=session_id,
        created_at=utc_now_iso(),
    )


def stage_result(
    context: NativePreprocRunContext,
    *,
    stage_id: NativePreprocStageId,
    parameters: dict[str, Any],
    status: NativePreprocStageStatus,
    capability_level: NativePreprocCapabilityLevel,
    qc: NativePreprocQC,
    input_artifacts: list[Any] | None = None,
    output_artifacts: list[Any] | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    backend: str = "native_python",
) -> NativePreprocStageResult:
    compute = parameters.get("compute") if isinstance(parameters.get("compute"), dict) else None
    if backend == "gpu" and compute is not None:
        try:
            from src.backend.app.native_preproc.orchestrator.gpu_performance_model import (
                record_gpu_measurement,
            )

            measurement = record_gpu_measurement(context.root_dir.parent, compute)
            if measurement is not None:
                parameters = {**parameters, "gpu_performance_measurement": measurement}
        except Exception:
            # Feedback telemetry must never invalidate a numerical artifact.
            pass
    result = NativePreprocStageResult(
        stage_id=stage_id,
        backend=backend,  # type: ignore[arg-type]
        input_artifacts=input_artifacts or [],
        output_artifacts=output_artifacts or [],
        parameters=parameters,
        status=status,
        capability_level=capability_level,
        validation_status="not_validated",
        warnings=warnings or [],
        errors=errors or [],
        provenance=provenance(
            stage_id=stage_id,
            parameters=parameters,
            input_artifact_ids=[artifact.artifact_id for artifact in input_artifacts or []],
            output_checksums={
                artifact.artifact_id: artifact.checksum for artifact in output_artifacts or [] if artifact.checksum
            },
            warnings=warnings or [],
            backend=backend,
            subject_id=context.subject_id,
            session_id=context.session_id,
        ),
        qc=qc,
    )
    write_stage_sidecars(context, result)
    return result
