"""Pipeline preset registry — contract-only pipeline templates.

These presets define reviewed-plan-compatible DAGs for common research
workflows.  All nodes are contract/planning nodes — they do NOT execute
real SPM/DPABI/MATLAB preprocessing.  They are validated, reviewed, and
dry-run through the existing Plan Review / execute-reviewed flow.
"""

from __future__ import annotations

from typing import Any

from src.backend.app.planner.plan_validator import validate_plan
from src.backend.app.schemas.preset_schemas import (
    PipelinePreset,
    PipelinePresetInstantiateRequest,
    PipelinePresetInstantiateResponse,
    PipelinePresetNode,
)

# ── Preset registry ──────────────────────────────────────────────────────────

_PRESETS: dict[str, PipelinePreset] = {}


def _register(preset: PipelinePreset) -> PipelinePreset:
    _PRESETS[preset.preset_id] = preset
    return preset


_register(
    PipelinePreset(
        preset_id="rsfmri_preproc_mvp",
        name="rs-fMRI Preprocessing MVP",
        modality="rs-fMRI",
        description=(
            "Minimal rs-fMRI preprocessing plan contract for research workflows. "
            "Validates data readiness, BIDS structure, BOLD references, and produces "
            "motion QC, preprocessing, and report plan stubs. "
            "This preset does NOT execute real SPM/DPABI preprocessing."
        ),
        version="0.1.0",
        nodes=[
            PipelinePresetNode(
                id="data_readiness_check",
                name="Data Readiness Check",
                stage="preprocessing",
                backend="contract",
                requires_approval=False,
                executable=False,
                description="Validate project data readiness before preprocessing.",
                inputs=["project_config_path"],
                outputs=["readiness_summary"],
                params={"executable": False, "dry_run_only": True},
                safety_notes=["Read-only — no rawdata modification."],
            ),
            PipelinePresetNode(
                id="bids_validation_check",
                name="BIDS Validation Check",
                stage="preprocessing",
                backend="contract",
                requires_approval=False,
                executable=False,
                description="Validate BIDS-like structure of rawdata.",
                inputs=["rawdata_dir"],
                outputs=["bids_validation_summary"],
                params={"executable": False, "dry_run_only": True},
                safety_notes=["Read-only — scans rawdata structure only."],
            ),
            PipelinePresetNode(
                id="rsfmri_bold_reference_check",
                name="BOLD Reference Readiness",
                stage="preprocessing",
                backend="contract",
                requires_approval=False,
                executable=False,
                description=(
                    "Inspect BOLD NIfTI dimensionality, volume count, "
                    "and sidecar metadata (RepetitionTime, TaskName, "
                    "SliceTiming). Proposes reference strategy without "
                    "computing or writing a reference image."
                ),
                inputs=["bold_nifti", "bold_sidecar_json"],
                outputs=["bold_reference_readiness_report"],
                params={"executable": False, "dry_run_only": True, "inspectable": True},
                safety_notes=[
                    "Read-only — no reference image written.",
                    "Does not compute realignment.",
                    "Does not modify rawdata.",
                    "Use GET /api/projects/{id}/bold-reference/readiness for inspection.",
                ],
            ),
            PipelinePresetNode(
                id="rsfmri_motion_qc_plan",
                name="Motion QC Readiness",
                stage="preprocessing",
                backend="contract",
                requires_approval=False,
                executable=False,
                description=(
                    "Inspect BOLD NIfTI and existing motion parameter / confounds "
                    "TSV files for motion-QC readiness. Reports FD availability, "
                    "sidecar coverage, and missing motion inputs. "
                    "Does NOT execute realignment."
                ),
                inputs=["bold_reference_summary", "motion_params_txt", "confounds_tsv"],
                outputs=["motion_qc_readiness_report"],
                params={"executable": False, "dry_run_only": True, "inspectable": True},
                safety_notes=[
                    "Read-only — no SPM/DPABI execution.",
                    "Does not compute realignment.",
                    "Does not modify rawdata.",
                    "Use GET /api/projects/{id}/motion-qc/readiness for inspection.",
                ],
            ),
            PipelinePresetNode(
                id="rsfmri_preprocessing_plan_stub",
                name="Preprocessing Plan Stub",
                stage="preprocessing",
                backend="contract",
                requires_approval=False,
                executable=False,
                description="Stub for future SPM slice-timing, realign, normalize, smooth steps.",
                inputs=["motion_qc_plan"],
                outputs=["preprocessing_plan_stub"],
                params={"executable": False, "dry_run_only": True},
                safety_notes=["Stub only — real preprocessing not implemented yet."],
            ),
            PipelinePresetNode(
                id="rsfmri_report_plan_stub",
                name="Report Plan Stub",
                stage="postprocessing",
                backend="contract",
                requires_approval=False,
                executable=False,
                description="Stub for future QC report generation.",
                inputs=["preprocessing_plan_stub"],
                outputs=["report_plan_stub"],
                params={"executable": False, "dry_run_only": True},
                safety_notes=["Stub only — report generation not implemented yet."],
            ),
        ],
        non_goals=[
            "Does not execute real SPM/DPABI/MATLAB.",
            "Does not run dcm2niix conversion.",
            "Does not modify rawdata.",
            "Does not produce clinical interpretations.",
        ],
        readiness_requirements=[
            "Rawdata directory exists.",
            "Dataset index has been generated.",
            "Data Readiness status is not blocked.",
            "BIDS validation status is not fail.",
        ],
        safety_flags={
            "contract_only": True,
            "no_external_tools": True,
            "rawdata_read_only": True,
            "requires_user_review": True,
            "execution_not_available": True,
        },
    )
)


# ── Public API ────────────────────────────────────────────────────────────────

def list_presets() -> list[dict[str, Any]]:
    """Return all registered presets as plain dicts."""
    return [preset.model_dump() for preset in _PRESETS.values()]


def get_preset(preset_id: str) -> PipelinePreset | None:
    """Look up a single preset by id."""
    return _PRESETS.get(preset_id)


def instantiate_preset(
    preset_id: str,
    request: PipelinePresetInstantiateRequest,
) -> PipelinePresetInstantiateResponse:
    """Build a reviewed-plan-compatible plan dict from a preset.

    Does NOT execute tools, write files, or call external software.
    """
    warnings: list[str] = []
    errors: list[str] = []

    preset = _PRESETS.get(preset_id)
    if preset is None:
        return PipelinePresetInstantiateResponse(
            ok=False,
            project_id="",
            preset_id=preset_id,
            plan={},
            validation={},
            errors=[f"Preset not found: {preset_id}"],
            next_actions=["Check available presets: GET /api/pipeline-presets"],
            safety_flags={},
        )

    # Build plan dict with linear dependencies
    nodes: list[dict[str, Any]] = []
    for pnode in preset.nodes:
        node: dict[str, Any] = {
            "id": pnode.id,
            "backend": pnode.backend,
            "depends_on": [],
            "params": dict(pnode.params),
        }
        nodes.append(node)

    # Chain dependencies sequentially
    for i in range(1, len(nodes)):
        nodes[i]["depends_on"] = [nodes[i - 1]["id"]]

    plan: dict[str, Any] = {
        "pipeline_id": preset_id,
        "nodes": nodes,
    }

    # Validate the plan
    validation = validate_plan(plan)
    validation_dict = validation.to_dict()

    if not validation.ok:
        for err in validation.errors:
            errors.append(f"[{err.code}] {err.message}")

    next_actions: list[str] = [
        "Copy this plan into the Plan Review Console to save a reviewed plan.",
        "Run dry-run execution check to verify the plan passes all safety gates.",
        "Review readiness requirements before considering real execution.",
    ]
    if not validation.ok:
        next_actions.insert(0, "Resolve validation errors before proceeding.")

    return PipelinePresetInstantiateResponse(
        ok=validation.ok and len(errors) == 0,
        project_id="",
        preset_id=preset_id,
        plan=plan,
        validation=validation_dict,
        warnings=warnings,
        errors=errors,
        next_actions=next_actions,
        safety_flags=dict(preset.safety_flags),
    )
