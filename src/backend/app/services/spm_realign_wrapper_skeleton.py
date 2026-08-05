"""SPM realign wrapper skeleton — non-executing preview generator.

Generates a command-template identifier, MATLAB batch preview, and
provenance preview from the dry-run manifest.  Never calls MATLAB/SPM,
never writes files, never creates directories.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.backend.app.schemas.desktop import (
    SpmRealignProvenancePreview,
    SpmRealignWrapperSkeletonResponse,
)
from src.backend.app.services.mock_store import mock_store
from src.backend.app.services.spm_realign_dry_run import (
    build_spm_realign_dry_run,
)
from src.backend.app.services.spm_realign_manifest_adapter import (
    build_output_manifest_from_dry_run_input,
)
from src.backend.app.services.spm_realign_params import (
    validate_spm_realign_params,
)

COMMAND_TEMPLATE_ID = "spm12_realign_estwrite_v1"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def build_spm_realign_batch_preview_result(
    inputs: list[dict[str, Any]] | None = None,
    params: dict[str, Any] | None = None,
    predicted_outputs: list[dict[str, Any]] | None = None,
    command_template_id: str = COMMAND_TEMPLATE_ID,
) -> dict[str, Any]:
    """Generate a deterministic, non-executing MATLAB batch preview.

    Returns a dict with `preview`, `cleaned_params`, `param_warnings`,
    and `param_errors`.  The `preview` string includes a visible banner
    when parameter validation errors/warnings are present.

    Pure function — no file I/O, no subprocess, no side effects.
    """
    safe_inputs = [i for i in (inputs or []) if isinstance(i, dict)]
    cleaned, param_warnings, param_errors = validate_spm_realign_params(params or {})
    p = dict(cleaned)

    # ── Build the preview string ──
    lines: list[str] = [
        "% PREVIEW ONLY — NOT EXECUTED",
        f"% Command template: {command_template_id}",
        "%",
        "% This is a safe MATLAB batch preview.  It describes what a",
        "% future SPM realignment wrapper WOULD submit.  No MATLAB",
        "% process has been started and no files have been created.",
    ]

    # Surface parameter validation issues prominently
    if param_errors:
        lines.extend(["", "% " + "=" * 58])
        lines.append("% PARAMETER VALIDATION ERRORS — PREVIEW USES CANONICAL DEFAULTS")
        for err in param_errors[:10]:
            lines.append(f"%   ERROR: {err}")
        lines.append("% " + "=" * 58)
    if param_warnings:
        lines.extend(["%", "% PARAMETER VALIDATION WARNINGS:"])
        for warn in param_warnings[:10]:
            lines.append(f"%   WARNING: {warn}")

    lines.extend(
        [
            "%",
            "%% Realign: Estimate & Reslice",
            "matlabbatch{1}.spm.spatial.realign.estwrite.data = {",
        ]
    )

    for inp in safe_inputs[:10]:
        bp = inp.get("bold_path", "MISSING")
        lines.append(f"    {{'{bp},1'}}; ...")

    lines.extend(
        [
            "    };",
            "",
            f"matlabbatch{{1}}.spm.spatial.realign.estwrite.eoptions.quality = {p['quality']};",
            f"matlabbatch{{1}}.spm.spatial.realign.estwrite.eoptions.sep = {p['separation_mm']};",
            f"matlabbatch{{1}}.spm.spatial.realign.estwrite.eoptions.fwhm = {p['fwhm_mm']};",
            f"matlabbatch{{1}}.spm.spatial.realign.estwrite.eoptions.rtm = {int(p['register_to_mean'])};",
            f"matlabbatch{{1}}.spm.spatial.realign.estwrite.eoptions.interp = {p['interpolation']};",
            f"matlabbatch{{1}}.spm.spatial.realign.estwrite.eoptions.wrap = {p['wrap']};",
            f"matlabbatch{{1}}.spm.spatial.realign.estwrite.eoptions.weight = {p['weight_image'] or '[]'};",
            "",
            "matlabbatch{1}.spm.spatial.realign.estwrite.roptions.which = [2 1];",
            f"matlabbatch{{1}}.spm.spatial.realign.estwrite.roptions.interp = {p['interpolation']};",
            f"matlabbatch{{1}}.spm.spatial.realign.estwrite.roptions.wrap = {p['wrap']};",
            f"matlabbatch{{1}}.spm.spatial.realign.estwrite.roptions.mask = {int(p['estimate_reslice'])};",
            "matlabbatch{1}.spm.spatial.realign.estwrite.roptions.prefix = 'r';",
        ]
    )

    if predicted_outputs:
        lines.extend(["", "%% Predicted outputs:", ""])
        for out in predicted_outputs[:25]:
            lines.append(f"%  [{out.get('kind', '?')}] {out.get('path', '?')}")

    lines.extend(
        [
            "",
            "%% Execution:",
            "% spm('defaults', 'FMRI');",
            "% spm_jobman('run', matlabbatch);",
            "%",
            "% END OF PREVIEW",
        ]
    )

    return {
        "preview": "\n".join(lines) + "\n",
        "cleaned_params": cleaned,
        "param_warnings": param_warnings,
        "param_errors": param_errors,
    }


def build_spm_realign_batch_preview(
    inputs: list[dict[str, Any]] | None = None,
    params: dict[str, Any] | None = None,
    predicted_outputs: list[dict[str, Any]] | None = None,
    command_template_id: str = COMMAND_TEMPLATE_ID,
) -> str:
    """Backward-compatible string-returning wrapper."""
    return str(
        build_spm_realign_batch_preview_result(
            inputs=inputs,
            params=params,
            predicted_outputs=predicted_outputs,
            command_template_id=command_template_id,
        )["preview"]
    )


def build_spm_realign_wrapper_skeleton(
    project_id: str,
    params: dict[str, Any] | None = None,
) -> SpmRealignWrapperSkeletonResponse:
    """Generate a non-executing wrapper skeleton from the dry-run manifest."""

    now = _now_iso()
    _warnings: list[str] = []
    errors: list[str] = []

    project = mock_store.get_project(project_id)
    if project is None:
        return SpmRealignWrapperSkeletonResponse(
            ok=False,
            project_id=project_id,
            status="blocked",
            generated_at=now,
            command_template_id=COMMAND_TEMPLATE_ID,
            dry_run=None,
            matlab_batch_preview="",
            provenance_preview=SpmRealignProvenancePreview(
                command_template_id=COMMAND_TEMPLATE_ID,
                project_id=project_id,
                params=params or {},
                environment_status="unknown",
                approval_required=True,
                audit_required=True,
                execution_enabled=False,
                safe_allowlist_enabled=False,
            ),
            errors=[f"Project not found: {project_id}"],
            safety_flags=_safety_flags(),
        )

    # Validate params
    cleaned, param_warnings, param_errors = validate_spm_realign_params(params or {})
    if param_errors:
        return SpmRealignWrapperSkeletonResponse(
            ok=False,
            project_id=project_id,
            status="blocked",
            generated_at=now,
            command_template_id=COMMAND_TEMPLATE_ID,
            dry_run=None,
            matlab_batch_preview="",
            provenance_preview=SpmRealignProvenancePreview(
                command_template_id=COMMAND_TEMPLATE_ID,
                project_id=project_id,
                params=cleaned,
                environment_status="unknown",
                approval_required=True,
                audit_required=True,
                execution_enabled=False,
                safe_allowlist_enabled=False,
                warnings=param_warnings,
            ),
            warnings=param_warnings,
            errors=param_errors,
            safety_flags=_safety_flags(),
        )

    dry_run = build_spm_realign_dry_run(project_id, cleaned)
    dry_run_dict = dry_run.model_dump()
    dry_run_status = dry_run_dict.get("status", "unknown")

    # Generate batch preview
    batch_result = build_spm_realign_batch_preview_result(
        inputs=dry_run_dict.get("inputs", []),
        params=cleaned,
        predicted_outputs=None,  # predicted outputs come from dry-run dict
        command_template_id=COMMAND_TEMPLATE_ID,
    )
    matlab_batch = batch_result["preview"]
    param_warnings.extend(batch_result.get("param_warnings", []))

    all_warnings: list[str] = list(param_warnings)
    all_warnings.extend(dry_run_dict.get("warnings", [])[:15])

    next_actions: list[str] = []
    if dry_run_status == "blocked":
        next_actions.append("Resolve dry-run blocking issues before generating a wrapper skeleton.")
    if param_warnings:
        next_actions.append("Review parameter warnings.")
    next_actions.append("This is a preview only — no MATLAB/SPM execution has occurred.")

    provenance = SpmRealignProvenancePreview(
        command_template_id=COMMAND_TEMPLATE_ID,
        project_id=project_id,
        params=cleaned,
        input_count=dry_run_dict.get("input_count", 0),
        predicted_output_count=sum(
            len(inp.get("predicted_outputs", [])) for inp in dry_run_dict.get("inputs", [])
        ),
        environment_status=dry_run_dict.get("environment_status"),
        approval_required=True,
        audit_required=True,
        execution_enabled=False,
        safe_allowlist_enabled=False,
        warnings=param_warnings[:10],
    )

    # Build output manifests from dry-run predicted outputs
    output_root = dry_run_dict.get("output_root_preview") or ""
    manifests: list[Any] = []
    total_items = 0
    total_missing = 0
    total_would_overwrite = 0

    for inp in dry_run_dict.get("inputs", [])[:50]:
        if not isinstance(inp, dict):
            continue
        manifest = build_output_manifest_from_dry_run_input(
            project_id=project_id,
            run_id="dry_run_preview",
            input_preview=inp,
            output_root=output_root,
        )
        manifests.append(manifest)
        total_items += len(manifest.items)
        total_missing += manifest.missing_required_count
        total_would_overwrite += sum(1 for i in manifest.items if i.warnings)

    manifest_summary: dict[str, Any] = {
        "manifest_count": len(manifests),
        "total_items": total_items,
        "missing_required_count": total_missing,
        "verified_count": 0,
        "would_overwrite_count": total_would_overwrite,
    }

    return SpmRealignWrapperSkeletonResponse(
        ok=dry_run.ok and not param_errors,
        project_id=project_id,
        status=dry_run_status,
        generated_at=now,
        node_id="spm_realign_subject",
        command_template_id=COMMAND_TEMPLATE_ID,
        dry_run=dry_run,
        matlab_batch_preview=matlab_batch,
        provenance_preview=provenance,
        output_manifests=manifests,
        manifest_summary=manifest_summary,
        warnings=all_warnings[:30],
        errors=errors[:20],
        next_actions=next_actions[:10],
        safety_flags=_safety_flags(),
    )


def _safety_flags() -> dict[str, bool]:
    return {
        "preview_only": True,
        "no_matlab_called": True,
        "no_spm_called": True,
        "no_files_created": True,
        "rawdata_not_modified": True,
        "not_safe_allowlisted": True,
        "execution_disabled": True,
    }
