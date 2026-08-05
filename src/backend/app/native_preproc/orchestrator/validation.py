"""Artifact validation helpers for native preprocessing."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from src.backend.app.native_preproc.io.nifti_io import nifti_summary
from src.backend.app.schemas.native_preproc import (
    NativePreprocArtifactRef,
    NativePreprocStageResult,
)

_NIFTI_TYPES = {
    "bold_4d",
    "t1w",
    "mean_functional",
    "brain_mask",
    "gm_map",
    "wm_map",
    "csf_map",
    "normalized_bold",
    "smoothed_bold",
    "residual_bold",
    "detrended_bold",
    "filtered_bold",
    "alff_map",
    "falff_map",
    "reho_map",
    "atlas",
    "atlas_resampled",
}

_NPY_TYPES = {
    "fc_matrix",
    "fisher_z_matrix",
}


def validate_artifact_ref(artifact: NativePreprocArtifactRef) -> list[str]:
    errors: list[str] = []
    path = Path(artifact.path)
    if not path.exists():
        return [f"missing artifact: {path}"]
    if path.stat().st_size <= 0:
        errors.append(f"empty artifact: {path}")
    if artifact.artifact_type in _NIFTI_TYPES:
        try:
            summary = nifti_summary(path)
        except Exception as exc:
            errors.append(f"cannot reload NIfTI artifact {path}: {exc}")
        else:
            if artifact.shape and artifact.shape != summary["shape"]:
                errors.append(f"shape mismatch for {path}: {artifact.shape} != {summary['shape']}")
            if artifact.dtype and artifact.dtype != summary["dtype"]:
                errors.append(f"dtype mismatch for {path}: {artifact.dtype} != {summary['dtype']}")
    if artifact.artifact_type in _NPY_TYPES:
        try:
            array = np.load(path)
        except Exception as exc:
            errors.append(f"cannot reload NumPy artifact {path}: {exc}")
        else:
            shape = [int(value) for value in array.shape]
            dtype = str(array.dtype)
            if artifact.shape and artifact.shape != shape:
                errors.append(f"shape mismatch for {path}: {artifact.shape} != {shape}")
            if artifact.dtype and artifact.dtype != dtype:
                errors.append(f"dtype mismatch for {path}: {artifact.dtype} != {dtype}")
    return errors


def validate_stage_result_artifacts(result: NativePreprocStageResult) -> list[str]:
    errors: list[str] = []
    for artifact in result.output_artifacts:
        errors.extend(validate_artifact_ref(artifact))
    if result.status == "succeeded" and not result.output_artifacts:
        errors.append("succeeded stage has no output artifacts")
    return errors


def _stage_to_mapping(stage: Any) -> Mapping[str, Any]:
    if isinstance(stage, Mapping):
        return stage
    if hasattr(stage, "model_dump"):
        return stage.model_dump(mode="json")
    raise TypeError(f"Unsupported native stage result payload: {type(stage)!r}")


def _artifact_to_mapping(artifact: Any) -> Mapping[str, Any]:
    if isinstance(artifact, Mapping):
        return artifact
    if hasattr(artifact, "model_dump"):
        return artifact.model_dump(mode="json")
    raise TypeError(f"Unsupported native artifact payload: {type(artifact)!r}")


def _validate_artifact_mapping(artifact: Mapping[str, Any]) -> list[str]:
    try:
        ref = NativePreprocArtifactRef.model_validate(dict(artifact))
    except Exception as exc:
        return [f"invalid artifact reference schema: {exc}"]
    return validate_artifact_ref(ref)


def _truthfulness_errors(
    stage: Mapping[str, Any],
    *,
    reference_validated_stage_ids: set[str],
) -> list[str]:
    stage_id = str(stage.get("stage_id") or "")
    status = str(stage.get("status") or "")
    capability_level = str(stage.get("capability_level") or "")
    validation_status = str(stage.get("validation_status") or "")
    output_artifacts = list(stage.get("output_artifacts") or [])
    validation_errors = list(stage.get("validation_errors") or [])

    numeric_levels = {
        "computed",
        "numerically_implemented",
        "simplified",
        "affine_only",
        "validated",
        "reference_validated",
    }
    non_numeric_levels = {"unavailable", "scaffolded", "metadata_only"}
    errors: list[str] = []
    if status == "metadata_only" and capability_level in numeric_levels:
        errors.append(f"{stage_id}: metadata_only stage claims numeric capability {capability_level}")
    if status in {"succeeded", "warning"} and capability_level in non_numeric_levels:
        errors.append(f"{stage_id}: successful stage has non-numeric capability {capability_level}")
    if status in {"succeeded", "warning"} and capability_level in numeric_levels and not output_artifacts:
        errors.append(f"{stage_id}: numeric successful stage has no output artifact")
    if status in {"succeeded", "warning"} and validation_errors:
        errors.append(f"{stage_id}: successful stage has validation errors")
    if (
        capability_level == "reference_validated" or validation_status == "reference_validated"
    ) and stage_id not in reference_validated_stage_ids:
        errors.append(f"{stage_id}: reference_validated claim has no passed reference comparison evidence")
    return errors


def build_full_run_validation_payload(
    *,
    project_id: str,
    run_id: str,
    created_at: str,
    stage_results: Sequence[Any],
    safety_flags: Mapping[str, bool],
    reference_comparisons: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a full-run validation report without upgrading reference status.

    This report validates the artifacts and truthfulness of the native full run.
    Reference validation remains opt-in: stages can only claim
    ``reference_validated`` when a passed comparison is supplied here.
    """

    stages = [_stage_to_mapping(stage) for stage in stage_results]
    comparisons = [dict(item) for item in (reference_comparisons or [])]
    passed_reference_stage_ids = {
        str(item.get("stage_id"))
        for item in comparisons
        if bool(item.get("passed")) and item.get("stage_id")
    }
    artifact_checks: list[dict[str, Any]] = []
    stage_checks: list[dict[str, Any]] = []
    all_artifact_errors: list[str] = []
    all_truthfulness_errors: list[str] = []

    for stage in stages:
        stage_id = str(stage.get("stage_id") or "")
        artifacts = [_artifact_to_mapping(artifact) for artifact in stage.get("output_artifacts") or []]
        artifact_errors: list[str] = []
        for artifact in artifacts:
            errors = _validate_artifact_mapping(artifact)
            artifact_errors.extend(errors)
            path = Path(str(artifact.get("path") or ""))
            artifact_checks.append(
                {
                    "stage_id": stage_id,
                    "artifact_type": artifact.get("artifact_type", ""),
                    "path": str(path),
                    "exists": path.exists(),
                    "non_empty": path.exists() and path.stat().st_size > 0,
                    "shape": list(artifact.get("shape") or []),
                    "dtype": artifact.get("dtype", ""),
                    "checksum": artifact.get("checksum", ""),
                    "errors": errors,
                }
            )
        truthfulness_errors = _truthfulness_errors(
            stage,
            reference_validated_stage_ids=passed_reference_stage_ids,
        )
        all_artifact_errors.extend(f"{stage_id}: {error}" for error in artifact_errors)
        all_truthfulness_errors.extend(truthfulness_errors)
        stage_checks.append(
            {
                "stage_id": stage_id,
                "status": stage.get("status", ""),
                "capability_level": stage.get("capability_level", ""),
                "validation_status": stage.get("validation_status", ""),
                "artifact_count": len(artifacts),
                "artifact_errors": artifact_errors,
                "truthfulness_errors": truthfulness_errors,
            }
        )

    required_safety_flags = {
        "rawdata_readonly_confirmed": True,
        "no_external_tools_executed": True,
        "no_matlab_spm_dpabi": True,
        "third_party_runtime_not_used": True,
        "research_use_only": True,
        "clinical_use_prohibited": True,
    }
    safety_checks = [
        {
            "flag": flag,
            "expected": expected,
            "actual": bool(safety_flags.get(flag)),
            "passed": bool(safety_flags.get(flag)) is expected,
        }
        for flag, expected in required_safety_flags.items()
    ]
    reference_failed = [item for item in comparisons if not bool(item.get("passed"))]
    reference_status = (
        "not_provided"
        if not comparisons
        else "failed"
        if reference_failed
        else "passed"
    )
    validation_failed = bool(
        all_artifact_errors
        or all_truthfulness_errors
        or any(not item["passed"] for item in safety_checks)
        or reference_failed
    )
    capability_summary: dict[str, list[str]] = {}
    for stage in stages:
        capability_summary.setdefault(str(stage.get("capability_level") or ""), []).append(
            str(stage.get("stage_id") or "")
        )

    return {
        "report_type": "native_preproc_full_validation",
        "project_id": project_id,
        "run_id": run_id,
        "created_at": created_at,
        "overall_status": "failed" if validation_failed else "pass",
        "summary": {
            "stage_count": len(stages),
            "artifact_count": len(artifact_checks),
            "artifact_failed_count": len(all_artifact_errors),
            "truthfulness_failed_count": len(all_truthfulness_errors),
            "safety_failed_count": sum(1 for item in safety_checks if not item["passed"]),
            "reference_validation_status": reference_status,
        },
        "stage_checks": stage_checks,
        "artifact_validation": {
            "status": "failed" if all_artifact_errors else "pass",
            "failed_count": len(all_artifact_errors),
            "errors": all_artifact_errors,
            "artifacts": artifact_checks,
        },
        "truthfulness": {
            "status": "failed" if all_truthfulness_errors else "pass",
            "failed_count": len(all_truthfulness_errors),
            "errors": all_truthfulness_errors,
            "capability_summary": capability_summary,
        },
        "safety_checks": safety_checks,
        "reference_validation": {
            "status": reference_status,
            "comparisons": comparisons,
            "note": (
                "No approved SPM/DPABI or independent reference fixture was supplied; "
                "native stages remain synthetic/E2E tested, not reference_validated."
                if not comparisons
                else ""
            ),
        },
        "limitations": [
            "This report validates local native Python artifacts and status truthfulness.",
            "It is not GUI workflow validation.",
            "It is not GPU validation.",
            "It is not cross-platform release validation.",
            "It is not SPM/DPABI reference validation unless reference comparisons are present and passed.",
        ],
    }
