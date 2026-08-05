"""QC Dashboard Report — aggregate project-level QC summary.

Composes existing read-only services into one consolidated report.
Never calls external tools, never modifies rawdata.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.backend.app.schemas.desktop import (
    QcDashboardCacheSummary,
    QcDashboardModuleSummary,
    QcDashboardReportArtifact,
    QcDashboardReportResponse,
)
from src.backend.app.services.image_preview import list_image_sources
from src.backend.app.services.mock_store import mock_store
from src.backend.app.services.qc_dashboard_fingerprint import (
    collect_qc_dashboard_fingerprint_roots,
)
from src.backend.app.services.qc_dashboard_module_cache import (
    build_module_cache_key,
    load_module_cache,
    save_module_cache,
)
from src.backend.app.services.qc_evidence_roots import collect_qc_evidence_roots
from src.backend.app.services.rawdata_fingerprint import (
    build_rawdata_fingerprint,
)

_REPORT_DIR = Path("outputs/reports/qc_dashboard")

_MODULES = [
    {
        "id": "data_readiness",
        "name": "Data Readiness",
        "fn": "_run_data_readiness",
        "essential": True,
    },
    {
        "id": "bids_validation",
        "name": "BIDS Validation",
        "fn": "_run_bids_validation",
        "essential": True,
    },
    {
        "id": "conversion_dry_run",
        "name": "Conversion Dry-run",
        "fn": "_run_conversion_dry_run",
        "essential": False,
    },
    {
        "id": "nifti_qc_snapshot",
        "name": "NIfTI QC Snapshot",
        "fn": "_run_nifti_qc_snapshot",
        "essential": True,
    },
    {
        "id": "bold_reference_readiness",
        "name": "BOLD Reference Readiness",
        "fn": "_run_bold_reference_readiness",
        "essential": True,
    },
    {
        "id": "motion_qc_readiness",
        "name": "Motion QC Readiness",
        "fn": "_run_motion_qc_readiness",
        "essential": True,
    },
    {
        "id": "motion_metrics_draft",
        "name": "Motion Metrics Draft",
        "fn": "_run_motion_metrics_draft",
        "essential": False,
    },
    {
        "id": "rsfmri_qc_planning",
        "name": "rs-fMRI QC Planning",
        "fn": "_run_rsfmri_qc_planning",
        "essential": False,
    },
]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _safe_slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in value)[:80]


_CONVERSION_GUIDANCE_TERMS = (
    "conversion",
    "dicom-to-bids",
    "dicom-to-nifti",
    "funraw/t1raw",
    "no nifti image sources",
    "image sources were not discovered",
    "imported directory contains nifti",
    "import or configure a project with nifti",
)


_STALE_MOTION_WARNING_TERMS = (
    "no valid data rows found",
    "desc-motion_parameters.tsv",
    "desc-friston24_regressors.tsv",
)

_NATIVE_PREPROC_STALE_NEXT_ACTION_TERMS = (
    "generate a reviewed preprocessing plan",
    "generate a preprocessing plan",
    "create preprocessing run",
    "create a preprocessing run",
    "motion qc computation can proceed",
    "ready for reference planning",
    "candidate(s) have fd data",
    "review fd threshold counts",
)

_NATIVE_PREPROC_REVIEW_ACTION = "Review generated native preprocessing artifacts."
_NATIVE_PREPROC_QC_REVIEW_ACTION = "Review generated native preprocessing and QC artifacts."
_NATIVE_PREPROC_FC_REVIEW_ACTION = "Review generated native preprocessing, QC, and FC artifacts."

_PRIORITY_TERMS = [
    "review generated native preprocessing",
    "dicom-to-bids",
    "dicom-to-nifti",
    "conversion dry-run",
    "conversion preflight",
    "run conversion",
    "persist review package",
    "register converted",
    "create preprocessing run",
]

_REGISTERED_BIDS_ROOT_FIELDS = (
    "preprocessing_input_dir",
    "converted_bids_dir",
    "last_conversion_output_root",
)


def _registered_nifti_evidence(project_id: str) -> dict[str, Any]:
    roots = collect_qc_evidence_roots(project_id, include_native_outputs=False)
    if not roots:
        return {
            "available": False,
            "roots": [],
            "image_count": 0,
            "subject_count": 0,
            "sequence_count": 0,
        }
    try:
        sources = list_image_sources(project_id=project_id, search_roots=roots)
    except Exception:
        return {
            "available": False,
            "roots": [str(root) for root in roots],
            "image_count": 0,
            "subject_count": 0,
            "sequence_count": 0,
        }
    source_roots = sorted({item.source_root for item in sources.manifest if item.source_root})
    return {
        "available": len(sources.manifest) > 0,
        "roots": source_roots,
        "image_count": len(sources.manifest),
        "subject_count": len(sources.subjects),
        "sequence_count": len(sources.sequences),
    }


def _has_subject_dirs(root: Path) -> bool:
    try:
        return any(child.is_dir() and child.name.startswith("sub-") for child in root.iterdir())
    except OSError:
        return False


def _looks_like_bids_dataset_root(root: Path) -> bool:
    try:
        return root.is_dir() and (
            (root / "dataset_description.json").is_file() or _has_subject_dirs(root)
        )
    except OSError:
        return False


def _find_bids_validation_root(
    raw_root: str | Path | None,
    *,
    require_bids_layout: bool,
) -> str | None:
    raw_text = str(raw_root or "").strip()
    if not raw_text:
        return None
    try:
        root = Path(raw_text).expanduser().resolve()
        if not root.exists():
            return None
        if root.is_file():
            root = root.parent
    except (OSError, RuntimeError, ValueError):
        return None

    for candidate in (root, *root.parents):
        if _looks_like_bids_dataset_root(candidate):
            return str(candidate)

    if require_bids_layout:
        return None
    return str(root) if root.is_dir() else None


def _append_unique_root(roots: list[str], root: str | None) -> None:
    if root and root not in roots:
        roots.append(root)


def _is_conversion_guidance(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in _CONVERSION_GUIDANCE_TERMS)


def _filter_conversion_guidance(items: list[str]) -> list[str]:
    return [item for item in items if not _is_conversion_guidance(str(item))]


def _is_stale_motion_metrics_warning(text: str) -> bool:
    lowered = text.lower()
    return "no valid data rows" in lowered and any(
        term in lowered for term in _STALE_MOTION_WARNING_TERMS[1:]
    )


def _filter_stale_motion_warnings(items: list[str]) -> list[str]:
    return [item for item in items if not _is_stale_motion_metrics_warning(str(item))]


def _latest_native_preprocessing_evidence(project_id: str) -> dict[str, Any]:
    unavailable = {
        "available": False,
        "status": "",
        "run_id": "",
        "artifact_count": 0,
        "completed_stages": set(),
        "stage_statuses": {},
    }
    project = mock_store.get_project(project_id)
    metadata = project.metadata if project and isinstance(project.metadata, dict) else {}
    project_dir = str(metadata.get("project_dir") or "")
    try:
        from src.backend.app.services.native_preproc_full import get_latest_native_full_run

        run = get_latest_native_full_run(project_id, project_dir=project_dir)
    except Exception:
        return unavailable

    stage_statuses = {
        str(stage.stage_id): str(stage.status)
        for stage in run.stage_results
        if getattr(stage, "stage_id", "")
    }
    completed_stages = {str(stage_id) for stage_id in run.completed_stages}
    computed_stages = {
        stage_id
        for stage_id, status in stage_statuses.items()
        if status in {"succeeded", "warning", "simplified"}
    }
    evidence = {
        "available": (
            not run.dry_run
            and run.status in {"succeeded", "partial"}
            and int(run.artifact_count or 0) > 0
        ),
        "status": str(run.status or ""),
        "run_id": str(run.run_id or ""),
        "artifact_count": int(run.artifact_count or 0),
        "completed_stages": completed_stages | computed_stages,
        "stage_statuses": stage_statuses,
    }
    return evidence


def _is_stale_after_native_preproc_action(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in _NATIVE_PREPROC_STALE_NEXT_ACTION_TERMS)


def _native_preproc_review_action(native_evidence: dict[str, Any]) -> str:
    stages = native_evidence.get("completed_stages")
    completed_stages = stages if isinstance(stages, set) else set()
    if "functional_connectivity" in completed_stages:
        return _NATIVE_PREPROC_FC_REVIEW_ACTION
    if "motion_qc" in completed_stages:
        return _NATIVE_PREPROC_QC_REVIEW_ACTION
    return _NATIVE_PREPROC_REVIEW_ACTION


def _postprocess_next_actions(
    actions: list[str],
    *,
    native_evidence: dict[str, Any] | None = None,
) -> list[str]:
    native_available = bool(native_evidence and native_evidence.get("available"))
    processed: list[str] = []
    seen_actions: set[str] = set()

    def add_action(action: str) -> None:
        action_text = str(action or "").strip()
        if not action_text:
            return
        normalized = action_text.lower()
        if normalized in seen_actions:
            return
        seen_actions.add(normalized)
        processed.append(action_text)

    if native_available and native_evidence is not None:
        add_action(_native_preproc_review_action(native_evidence))

    for action in actions:
        action_text = str(action or "").strip()
        if native_available and _is_stale_after_native_preproc_action(action_text):
            continue
        add_action(action_text)

    processed.sort(key=_action_priority)
    return processed


def _action_priority(act: str) -> int:
    act_lower = act.lower()
    for idx, term in enumerate(_PRIORITY_TERMS):
        if term in act_lower:
            return idx
    return len(_PRIORITY_TERMS)


def _module_markdown_next_action(
    module: dict[str, Any],
    *,
    native_evidence: dict[str, Any] | None = None,
) -> str:
    native_available = bool(native_evidence and native_evidence.get("available"))
    for action in module.get("next_actions", []) or []:
        action_text = str(action or "").strip()
        if not action_text:
            continue
        if native_available and _is_stale_after_native_preproc_action(action_text):
            continue
        return action_text
    return "—"


def _module_warning_count(module: dict[str, Any]) -> int:
    metrics = module.get("key_metrics")
    if isinstance(metrics, dict):
        value = metrics.get("warning_count")
        if isinstance(value, bool):
            value = None
        if isinstance(value, int):
            return max(value, 0)
        if isinstance(value, float):
            return max(int(value), 0)
    return len(module.get("warnings", []) or [])


def _module_warning_summary(module: dict[str, Any]) -> str | None:
    count = _module_warning_count(module)
    warning_text_count = len(module.get("warnings", []) or [])
    if count <= 0 or count <= warning_text_count:
        return None
    module_name = str(module.get("name") or module.get("id") or "Module")
    module_id = str(module.get("id") or module.get("module_id") or "")
    if module_id == "nifti_qc_snapshot":
        return f"{module_name} reports {count} image-level warning(s)."
    return f"{module_name} reports {count} warning(s)."


def _with_module_warning_summaries(
    warnings: list[str],
    modules: list[dict[str, Any]],
) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()

    def add_warning(value: str | None) -> None:
        warning = str(value or "").strip()
        if not warning:
            return
        normalized = warning.lower()
        if normalized in seen:
            return
        seen.add(normalized)
        result.append(warning)

    for warning in warnings:
        add_warning(warning)
    for module in modules:
        add_warning(_module_warning_summary(module))
    return result


def _fd_count_from_modules(modules: list[dict[str, Any]]) -> int:
    for module in modules:
        if module.get("id", module.get("module_id")) != "motion_qc_readiness":
            continue
        metrics = module.get("key_metrics") if isinstance(module.get("key_metrics"), dict) else {}
        value = metrics.get("fd_available_count")
        if isinstance(value, int):
            return value
    return 0


def _normalize_legacy_latest_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Clean stale dashboard artifacts without recomputing sub-services.

    Older reports included native auxiliary motion TSV files as failed parse
    warnings even when an explicit FD timeseries was available.  Loading those
    persisted reports should not re-surface stale warnings after the parser
    contract has been tightened.
    """

    modules = list(data.get("modules", []) or [])
    fd_count = _fd_count_from_modules(modules)
    changed = False

    for module in modules:
        module_id = module.get("id", module.get("module_id"))
        if module_id != "motion_metrics_draft":
            continue
        warnings = [str(item) for item in module.get("warnings", []) or []]
        filtered = _filter_stale_motion_warnings(warnings)
        if filtered == warnings:
            continue
        changed = True
        module["warnings"] = filtered
        if not filtered and not (module.get("errors") or []):
            module["status"] = "ready"
            module["ok"] = True
            if fd_count > 0:
                module["summary"] = (
                    f"Candidates: {fd_count}, Parsed: {fd_count}, FD available: {fd_count}"
                )
                metrics = module.get("key_metrics")
                if not isinstance(metrics, dict):
                    metrics = {}
                metrics.update(
                    {
                        "candidate_count": fd_count,
                        "parsed_count": fd_count,
                        "fd_available_count": fd_count,
                    }
                )
                module["key_metrics"] = metrics

    if not changed:
        return data

    data["modules"] = modules
    data["warnings"] = _filter_stale_motion_warnings(
        [str(item) for item in data.get("warnings", []) or []]
    )

    essential_ids = {m["id"] for m in _MODULES if m["essential"]}
    ready_count = sum(1 for m in modules if m.get("status") == "ready")
    warning_count = sum(1 for m in modules if m.get("status") == "warning")
    blocked_count = sum(
        1
        for m in modules
        if m.get("status") == "blocked" and m.get("id", m.get("module_id")) in essential_ids
    )
    unknown_count = sum(
        1 for m in modules if m.get("status") not in ("ready", "warning", "blocked", "not_run")
    )
    if blocked_count > 0:
        overall_status = "blocked"
    elif warning_count > 0:
        overall_status = "warning"
    elif ready_count > 0:
        overall_status = "ready"
    else:
        overall_status = "unknown"

    data["ready_count"] = ready_count
    data["warning_count"] = warning_count
    data["blocked_count"] = blocked_count
    data["unknown_count"] = unknown_count
    data["overall_status"] = overall_status
    return data


def _run_data_readiness(project_id: str) -> dict[str, Any]:
    from src.backend.app.services.data_readiness import build_data_readiness

    r = build_data_readiness(project_id)
    d = r.model_dump()
    evidence = _registered_nifti_evidence(project_id)
    checks = d.get("checks", []) or []
    checks_total = len(checks)
    checks_passed = sum(1 for c in checks if c.get("status") == "pass")
    warnings = d.get("warnings", [])[:10]
    next_actions = d.get("next_actions", [])[:5]
    status = _normalize_status(d.get("status", "unknown"))
    image_count = d.get("image_source_count", 0)
    subject_count = d.get("subject_count", 0)
    sequence_count = d.get("sequence_count", 0)
    summary = f"Images: {image_count}, Subjects: {subject_count}"
    if evidence["available"]:
        warnings = _filter_conversion_guidance(warnings)
        next_actions = _filter_conversion_guidance(next_actions)
        image_count = evidence["image_count"]
        subject_count = evidence["subject_count"]
        sequence_count = evidence["sequence_count"]
        summary = f"Registered input NIfTI evidence: {image_count}, Subjects: {subject_count}"
        if status in ("blocked", "warning"):
            status = "warning" if warnings else "ready"
    return {
        "status": status,
        "ok": d.get("ok", False),
        "summary": summary,
        "key_metrics": {
            "image_count": image_count,
            "subject_count": subject_count,
            "sequence_count": sequence_count,
            "checks_total": checks_total,
            "checks_passed": checks_passed,
        },
        "warnings": warnings,
        "errors": d.get("errors", [])[:10],
        "next_actions": next_actions,
    }


def _normalize_status(raw: str) -> str:
    """Normalize status strings from sub-services to the dashboard literal."""
    mapping = {"fail": "blocked", "pass": "ready", "warn": "warning"}
    return mapping.get(raw, raw)


def _run_bids_validation(project_id: str) -> dict[str, Any]:
    from src.backend.app.services.bids_validation import validate_bids

    evidence = _registered_nifti_evidence(project_id)
    project = mock_store.get_project(project_id)
    metadata = project.metadata if project and isinstance(project.metadata, dict) else {}
    roots: list[str] = []
    if evidence["available"]:
        for field in _REGISTERED_BIDS_ROOT_FIELDS:
            _append_unique_root(
                roots,
                _find_bids_validation_root(
                    metadata.get(field),
                    require_bids_layout=True,
                ),
            )
        for source_root in evidence.get("roots", []):
            _append_unique_root(
                roots,
                _find_bids_validation_root(
                    source_root,
                    require_bids_layout=True,
                ),
            )
    elif project:
        rawdata = metadata.get("rawdata_dir")
        if rawdata and isinstance(rawdata, str):
            _append_unique_root(
                roots,
                _find_bids_validation_root(rawdata, require_bids_layout=False),
            )
        try:
            import_roots = mock_store.list_import_paths(project_id)
            for import_root in import_roots:
                _append_unique_root(
                    roots,
                    _find_bids_validation_root(
                        import_root,
                        require_bids_layout=False,
                    ),
                )
        except Exception:
            pass
    r = validate_bids(roots)
    d = r.model_dump()
    issues_count = d.get("issues_count")
    if not isinstance(issues_count, int):
        issues_count = len(d.get("issues", []) or [])
    warning_count = d.get("warning_count")
    if not isinstance(warning_count, int):
        warning_count = sum(
            1 for issue in d.get("issues", []) or [] if issue.get("severity") == "warning"
        )
    return {
        "status": _normalize_status(d.get("status", "unknown")),
        "ok": d.get("ok", False),
        "summary": f"Issues: {issues_count}, Warnings: {warning_count}",
        "key_metrics": {
            "issues_count": issues_count,
            "warning_count": warning_count,
        },
        "warnings": d.get("warnings", [])[:10],
        "errors": d.get("errors", [])[:10],
        "next_actions": d.get("next_actions", [])[:5],
    }


def _run_conversion_dry_run(project_id: str) -> dict[str, Any]:
    evidence = _registered_nifti_evidence(project_id)
    if evidence["available"]:
        return {
            "status": "ready",
            "ok": True,
            "summary": "Registered BIDS/NIfTI evidence is available; conversion is not required for this QC report.",
            "key_metrics": {
                "image_count": evidence["image_count"],
                "subject_count": evidence["subject_count"],
            },
            "warnings": [],
            "errors": [],
            "next_actions": [],
        }
    from src.backend.app.schemas.desktop import ConversionDryRunRequest
    from src.backend.app.services.conversion_planner import plan_conversion

    try:
        r = plan_conversion(project_id, ConversionDryRunRequest())
        d = r.model_dump()
        return {
            "status": d.get("status", "unknown"),
            "ok": d.get("ok", False),
            "summary": f"Roots: {d.get('roots_count', 0)}, BIDS ready: {d.get('bids_ready_count', 0)}",
            "key_metrics": {
                "roots_count": d.get("roots_count", 0),
                "bids_ready_count": d.get("bids_ready_count", 0),
            },
            "warnings": d.get("warnings", [])[:10],
            "errors": d.get("errors", [])[:10],
            "next_actions": d.get("next_actions", [])[:5],
        }
    except Exception as exc:
        return {
            "status": "not_run",
            "ok": False,
            "summary": str(exc)[:200],
            "key_metrics": {},
            "warnings": [],
            "errors": [str(exc)],
            "next_actions": [],
        }


def _run_nifti_qc_snapshot(project_id: str) -> dict[str, Any]:
    from src.backend.app.services.nifti_qc_snapshot import build_nifti_qc_snapshot

    r = build_nifti_qc_snapshot(project_id)
    d = r.model_dump()
    return {
        "status": d.get("status", "unknown"),
        "ok": d.get("ok", False),
        "summary": (
            f"Input images: {d.get('image_count', 0)}, "
            f"Readable: {d.get('readable_count', 0)}"
        ),
        "key_metrics": {
            "image_count": d.get("image_count", 0),
            "readable_count": d.get("readable_count", 0),
            "four_d_count": d.get("four_d_count", 0),
            "warning_count": d.get("warning_count", 0),
        },
        "warnings": d.get("warnings", [])[:10],
        "errors": d.get("errors", [])[:10],
        "next_actions": d.get("next_actions", [])[:5],
    }


def _run_bold_reference_readiness(project_id: str) -> dict[str, Any]:
    from src.backend.app.services.bold_reference_readiness import build_bold_reference_readiness

    r = build_bold_reference_readiness(project_id)
    d = r.model_dump()
    return {
        "status": d.get("status", "unknown"),
        "ok": d.get("ok", False),
        "summary": f"Candidates: {d.get('candidate_count', 0)}, Valid: {d.get('valid_count', 0)}",
        "key_metrics": {
            "candidate_count": d.get("candidate_count", 0),
            "valid_count": d.get("valid_count", 0),
        },
        "warnings": d.get("warnings", [])[:10],
        "errors": d.get("errors", [])[:10],
        "next_actions": d.get("next_actions", [])[:5],
    }


def _run_motion_qc_readiness(project_id: str) -> dict[str, Any]:
    from src.backend.app.services.motion_qc_readiness import build_motion_qc_readiness

    r = build_motion_qc_readiness(project_id)
    d = r.model_dump()
    return {
        "status": d.get("status", "unknown"),
        "ok": d.get("ok", False),
        "summary": f"BOLD files: {d.get('bold_file_count', 0)}, FD available: {d.get('fd_available_count', 0)}",
        "key_metrics": {
            "bold_file_count": d.get("bold_file_count", 0),
            "fd_available_count": d.get("fd_available_count", 0),
        },
        "warnings": d.get("warnings", [])[:10],
        "errors": d.get("errors", [])[:10],
        "next_actions": d.get("next_actions", [])[:5],
    }


def _run_motion_metrics_draft(project_id: str) -> dict[str, Any]:
    try:
        from src.backend.app.services.motion_metrics_draft import build_motion_metrics_draft

        r = build_motion_metrics_draft(project_id)
        d = r.model_dump()
        return {
            "status": d.get("status", "unknown"),
            "ok": d.get("ok", False),
            "summary": f"Candidates: {d.get('candidate_count', 0)}, Parsed: {d.get('parsed_count', 0)}, FD available: {d.get('fd_available_count', 0)}",
            "key_metrics": {
                "candidate_count": d.get("candidate_count", 0),
                "parsed_count": d.get("parsed_count", 0),
            },
            "warnings": d.get("warnings", [])[:10],
            "errors": d.get("errors", [])[:10],
            "next_actions": d.get("next_actions", [])[:5],
        }
    except Exception as exc:
        return {
            "status": "not_run",
            "ok": False,
            "summary": str(exc)[:200],
            "key_metrics": {},
            "warnings": [],
            "errors": [str(exc)],
            "next_actions": [],
        }


def _run_rsfmri_qc_planning(project_id: str) -> dict[str, Any]:
    try:
        from src.backend.app.services.rsfmri_qc_planning_report import (
            build_rsfmri_qc_planning_report,
        )

        r = build_rsfmri_qc_planning_report(project_id)
        d = r.model_dump()
        return {
            "status": d.get("status", "unknown"),
            "ok": d.get("ok", False),
            "summary": f"Report generated: {d.get('report_dir', 'N/A')}",
            "key_metrics": {},
            "warnings": d.get("warnings", [])[:10],
            "errors": d.get("errors", [])[:10],
            "next_actions": d.get("next_actions", [])[:5],
        }
    except Exception as exc:
        return {
            "status": "not_run",
            "ok": False,
            "summary": str(exc)[:200],
            "key_metrics": {},
            "warnings": [],
            "errors": [str(exc)],
            "next_actions": [],
        }


def _build_markdown(
    project_id: str,
    generated_at: str,
    overall_status: str,
    modules: list[dict[str, Any]],
    ready: int,
    warning: int,
    blocked: int,
    unknown: int,
    all_warnings: list[str],
    all_errors: list[str],
    next_actions: list[str],
    native_evidence: dict[str, Any] | None = None,
) -> str:
    lines = [
        "# QC Dashboard Summary Report",
        "",
        f"- **Project**: {project_id}",
        f"- **Generated**: {generated_at}",
        f"- **Overall Status**: {overall_status}",
        f"- **Modules**: {len(modules)}",
        f"- **Ready**: {ready} | **Warning**: {warning} | **Blocked**: {blocked} | **Unknown**: {unknown}",
        "",
        "> ⚠️ Research-use only. Not for clinical diagnosis or clinical decision-making.",
        "",
        "## Module Summary",
        "",
        "| Module | Status | Summary | Warnings | Next Action |",
        "| --- | --- | --- | --- | --- |",
    ]
    for m in modules:
        next_action = _module_markdown_next_action(
            m,
            native_evidence=native_evidence,
        )
        lines.append(
            f"| {m['name']} | {m['status']} | {m.get('summary', '')[:60]} "
            f"| {_module_warning_count(m)} | {next_action[:50]} |"
        )

    lines.extend(["", "## Overall Warnings", ""])
    for w in all_warnings[:15]:
        lines.append(f"- {w}")
    if not all_warnings:
        lines.append("- None")

    lines.extend(["", "## Overall Errors", ""])
    for e in all_errors[:15]:
        lines.append(f"- {e}")
    if not all_errors:
        lines.append("- None")

    lines.extend(["", "## Next Actions", ""])
    for i, a in enumerate(next_actions[:10], 1):
        lines.append(f"{i}. {a}")
    if not next_actions:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Safety Flags",
            "",
            "- read_only_inputs: true",
            "- rawdata_not_modified: true",
            "- no_preprocessing_executed: true",
            "- no_external_tools_executed: true",
            "- qc_dashboard_report_only: true",
            "- clinical_use_prohibited: true",
            "",
            "## Non-Goals",
            "",
            "- No preprocessing was executed.",
            "- No clinical interpretation was made.",
            "- No rawdata was modified.",
            "- No external tools (MATLAB/SPM/DPABI/GPU) were called.",
        ]
    )

    return "\n".join(lines) + "\n"


def build_qc_dashboard_report(
    project_id: str, cache_mode: str = "off"
) -> QcDashboardReportResponse:
    project = mock_store.get_project(project_id)
    if project is None:
        return QcDashboardReportResponse(
            ok=False,
            project_id=project_id,
            status="blocked",
            generated_at=_now_iso(),
            report_dir="",
            json_path="",
            markdown_path="",
            overall_errors=[f"Project not found: {project_id}"],
            safety_flags=_safety_flags(),
        )

    now = _now_iso()
    modules: list[dict[str, Any]] = []
    all_warnings: list[str] = []
    all_errors: list[str] = []
    cache_records: list[Any] = []
    module_hits: dict[str, bool] = {}

    # Compute fingerprint for caching
    fingerprint_str: str | None = None
    if cache_mode != "off":
        metadata = (
            (project.metadata if isinstance(project.metadata, dict) else {}) if project else {}
        )
        roots = collect_qc_dashboard_fingerprint_roots(metadata)
        fp = build_rawdata_fingerprint(roots)
        fingerprint_str = fp.fingerprint

    for mod in _MODULES:
        fn_name = mod["fn"]
        fn = globals().get(fn_name)
        if fn is None:
            modules.append(
                {
                    "id": mod["id"],
                    "name": mod["name"],
                    "status": "not_run",
                    "ok": False,
                    "summary": f"Internal: {fn_name} not found",
                    "key_metrics": {},
                    "warnings": [],
                    "errors": [],
                    "next_actions": [],
                }
            )
            continue

        # ── Module-level caching for nifti_qc_snapshot ──
        cache_rec: Any = None
        if mod["id"] == "nifti_qc_snapshot" and cache_mode != "off":
            cache_key = build_module_cache_key(
                project_id=project_id,
                module_id="nifti_qc_snapshot",
                fingerprint=fingerprint_str,
            )
            if cache_mode == "prefer":
                cached_payload, cache_rec = load_module_cache(
                    project_id=project_id,
                    module_id="nifti_qc_snapshot",
                    cache_key=cache_key,
                )
                if cached_payload is not None:
                    result = cached_payload
                    module_hits["nifti_qc_snapshot"] = True
                    cache_records.append(cache_rec)
                    modules.append(
                        {
                            "id": mod["id"],
                            "name": mod["name"],
                            "status": result.get("status", "unknown"),
                            "ok": result.get("ok", False),
                            "summary": result.get("summary", ""),
                            "key_metrics": result.get("key_metrics", {}),
                            "warnings": result.get("warnings", []),
                            "errors": result.get("errors", []),
                            "next_actions": result.get("next_actions", []),
                        }
                    )
                    continue  # skip execution for this module

        try:
            result = fn(project_id)
        except Exception as exc:
            result = {
                "status": "unknown",
                "ok": False,
                "summary": f"Error: {exc}",
                "key_metrics": {},
                "warnings": [],
                "errors": [str(exc)],
                "next_actions": [],
            }

        # ── Save cache on refresh for nifti_qc_snapshot ──
        if mod["id"] == "nifti_qc_snapshot" and cache_mode == "refresh" and fingerprint_str:
            cache_key = build_module_cache_key(
                project_id=project_id,
                module_id="nifti_qc_snapshot",
                fingerprint=fingerprint_str,
            )
            cache_rec = save_module_cache(
                project_id=project_id,
                module_id="nifti_qc_snapshot",
                cache_key=cache_key,
                payload=result,
                fingerprint=fingerprint_str,
            )
            cache_records.append(cache_rec)

        modules.append(
            {
                "id": mod["id"],
                "name": mod["name"],
                "status": result["status"],
                "ok": result["ok"],
                "summary": result["summary"],
                "key_metrics": result["key_metrics"],
                "warnings": result["warnings"],
                "errors": result["errors"],
                "next_actions": result["next_actions"],
            }
        )

        all_warnings.extend(result["warnings"][:5])
        all_errors.extend(result["errors"][:5])

    all_warnings = _with_module_warning_summaries(all_warnings, modules)

    # Overall status
    essential_ids = {m["id"] for m in _MODULES if m["essential"]}
    blocked_count = sum(1 for m in modules if m["status"] == "blocked" and m["id"] in essential_ids)
    _non_essential_ready_or_warn = [
        m for m in modules if m["id"] not in essential_ids and m["status"] in ("ready", "warning")
    ]
    warning_count = sum(1 for m in modules if m["status"] == "warning")
    ready_count = sum(1 for m in modules if m["status"] == "ready")
    unknown_count = sum(
        1 for m in modules if m["status"] not in ("ready", "warning", "blocked", "not_run")
    )

    if blocked_count > 0:
        overall_status = "blocked"
    elif warning_count > 0:
        overall_status = "warning"
    elif ready_count > 0:
        overall_status = "ready"
    else:
        overall_status = "unknown"

    # Deduplicate next actions while preserving order.
    raw_next_actions = []
    for m in modules:
        for a in m.get("next_actions", [])[:2]:
            if a:
                raw_next_actions.append(str(a))
    native_evidence = _latest_native_preprocessing_evidence(project_id)
    next_actions = _postprocess_next_actions(
        raw_next_actions,
        native_evidence=native_evidence,
    )
    next_actions = next_actions[:5]

    # Build markdown
    markdown = _build_markdown(
        project_id,
        now,
        overall_status,
        modules,
        ready_count,
        warning_count,
        blocked_count,
        unknown_count,
        all_warnings,
        all_errors,
        next_actions,
        native_evidence=native_evidence,
    )

    # Write report artifacts
    report_dir = _REPORT_DIR / _safe_slug(project_id)
    report_dir.mkdir(parents=True, exist_ok=True)

    json_path = report_dir / "qc_dashboard_report.json"
    md_path = report_dir / "qc_dashboard_report.md"

    json_payload = {
        "project_id": project_id,
        "generated_at": now,
        "overall_status": overall_status,
        "modules": modules,
        "ready_count": ready_count,
        "warning_count": warning_count,
        "blocked_count": blocked_count,
        "unknown_count": unknown_count,
        "warnings": all_warnings,
        "errors": all_errors,
        "next_actions": next_actions,
    }
    json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")

    model_modules = [
        QcDashboardModuleSummary(
            module_id=m["id"],
            name=m["name"],
            status=m["status"],
            ok=m["ok"],
            summary=m["summary"],
            key_metrics=m["key_metrics"],
            warnings=m["warnings"],
            errors=m["errors"],
            next_actions=m["next_actions"],
        )
        for m in modules
    ]

    return QcDashboardReportResponse(
        ok=overall_status != "blocked",
        project_id=project_id,
        status=overall_status,
        generated_at=now,
        report_dir=str(report_dir),
        json_path=str(json_path),
        markdown_path=str(md_path),
        artifacts=[
            QcDashboardReportArtifact(kind="json", path=str(json_path), exists=True),
            QcDashboardReportArtifact(kind="markdown", path=str(md_path), exists=True),
        ],
        modules=model_modules,
        ready_count=ready_count,
        warning_count=warning_count,
        blocked_count=blocked_count,
        unknown_count=unknown_count,
        overall_warnings=all_warnings[:30],
        overall_errors=all_errors[:30],
        next_actions=next_actions,
        safety_flags=_safety_flags(),
        report_markdown=markdown,
        cache=_build_cache_summary(
            cache_mode,
            cache_records=cache_records,
            module_hits=module_hits,
        ),
    )


def load_latest_qc_dashboard_report(project_id: str) -> QcDashboardReportResponse | None:
    """Load the most recently generated QC dashboard report from disk.

    Reads qc_dashboard_report.json and qc_dashboard_report.md from the
    safe report directory.  Never regenerates sub-services, never writes
    files, never calls external tools.

    Returns None if no report exists.
    """
    report_dir = _REPORT_DIR / _safe_slug(project_id)
    json_path = report_dir / "qc_dashboard_report.json"
    md_path = report_dir / "qc_dashboard_report.md"

    if not json_path.is_file():
        return None

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    before_normalize = json.dumps(data, ensure_ascii=False, sort_keys=True)
    data = _normalize_legacy_latest_payload(data)
    legacy_normalized = json.dumps(data, ensure_ascii=False, sort_keys=True) != before_normalize
    next_actions_before = [str(item) for item in data.get("next_actions", []) or []]
    native_evidence = _latest_native_preprocessing_evidence(
        str(data.get("project_id") or project_id)
    )
    next_actions_after = _postprocess_next_actions(
        next_actions_before,
        native_evidence=native_evidence,
    )[:5]
    if next_actions_after != next_actions_before:
        data["next_actions"] = next_actions_after
        legacy_normalized = True

    markdown = ""
    if md_path.is_file():
        try:
            markdown = md_path.read_text(encoding="utf-8")
        except Exception:
            markdown = ""

    modules_raw = data.get("modules", []) or []
    warnings_before = [str(item) for item in data.get("warnings", []) or []]
    warnings_after = _with_module_warning_summaries(warnings_before, modules_raw)
    if warnings_after != warnings_before:
        data["warnings"] = warnings_after
        legacy_normalized = True
    model_modules = [
        QcDashboardModuleSummary(
            module_id=m.get("id", m.get("module_id", "?")),
            name=m.get("name", m.get("id", "?")),
            status=m.get("status", "unknown"),
            ok=m.get("ok", False),
            summary=m.get("summary", ""),
            key_metrics=m.get("key_metrics", {}),
            warnings=m.get("warnings", []),
            errors=m.get("errors", []),
            next_actions=m.get("next_actions", []),
        )
        for m in modules_raw
    ]

    json_stat = json_path.stat()
    md_stat = md_path.stat() if md_path.is_file() else None
    if legacy_normalized or bool(native_evidence and native_evidence.get("available")):
        markdown = _build_markdown(
            data.get("project_id", project_id),
            data.get("generated_at", ""),
            data.get("overall_status", "ready"),
            modules_raw,
            data.get("ready_count", 0),
            data.get("warning_count", 0),
            data.get("blocked_count", 0),
            data.get("unknown_count", 0),
            data.get("warnings", []),
            data.get("errors", []),
            data.get("next_actions", []),
            native_evidence=native_evidence,
        )

    return QcDashboardReportResponse(
        ok=data.get("overall_status", "unknown") != "blocked",
        project_id=data.get("project_id", project_id),
        status=data.get("overall_status", "ready"),
        generated_at=data.get("generated_at", ""),
        report_dir=str(report_dir),
        json_path=str(json_path),
        markdown_path=str(md_path),
        artifacts=[
            QcDashboardReportArtifact(
                kind="json", path=str(json_path), exists=True, size_bytes=json_stat.st_size
            ),
            QcDashboardReportArtifact(
                kind="markdown",
                path=str(md_path),
                exists=md_path.is_file(),
                size_bytes=md_stat.st_size if md_stat else None,
            ),
        ],
        modules=model_modules,
        ready_count=data.get("ready_count", 0),
        warning_count=data.get("warning_count", 0),
        blocked_count=data.get("blocked_count", 0),
        unknown_count=data.get("unknown_count", 0),
        overall_warnings=data.get("warnings", []),
        overall_errors=data.get("errors", []),
        next_actions=data.get("next_actions", []),
        safety_flags=_safety_flags(),
        report_markdown=markdown or None,
        cache=QcDashboardCacheSummary(mode="off", hit=False),
    )


def _build_cache_summary(
    mode: str,
    cache_records: list[Any] | None = None,
    module_hits: dict[str, bool] | None = None,
) -> QcDashboardCacheSummary:
    cache_warnings: list[str] = []
    if mode == "prefer" and not cache_records:
        cache_warnings.append("Cache mode 'prefer' is accepted, but no cached data was found.")
    return QcDashboardCacheSummary(
        mode=mode,
        hit=False,
        module_hits=module_hits or {},
        module_records=list(cache_records or []),
        cache_warnings=cache_warnings,
    )


def _safety_flags() -> dict[str, bool]:
    return {
        "read_only_inputs": True,
        "rawdata_not_modified": True,
        "no_preprocessing_executed": True,
        "no_external_tools_executed": True,
        "qc_dashboard_report_only": True,
        "clinical_use_prohibited": True,
    }
