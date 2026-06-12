"""QC Dashboard Report — aggregate project-level QC summary.

Composes existing read-only services into one consolidated report.
Never calls external tools, never modifies rawdata.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.backend.app.schemas.desktop import (
    QcDashboardCacheSummary,
    QcDashboardModuleSummary,
    QcDashboardReportArtifact,
    QcDashboardReportResponse,
)
from src.backend.app.services.mock_store import mock_store
from src.backend.app.services.qc_dashboard_fingerprint import (
    collect_qc_dashboard_fingerprint_roots,
)
from src.backend.app.services.qc_dashboard_module_cache import (
    build_module_cache_key,
    load_module_cache,
    save_module_cache,
)
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
    return datetime.now(timezone.utc).isoformat()


def _safe_slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in value)[:80]


def _run_data_readiness(project_id: str) -> dict[str, Any]:
    from src.backend.app.services.data_readiness import build_data_readiness
    r = build_data_readiness(project_id)
    d = r.model_dump()
    checks = d.get("checks", []) or []
    checks_total = len(checks)
    checks_passed = sum(1 for c in checks if c.get("status") == "pass")
    return {
        "status": _normalize_status(d.get("status", "unknown")),
        "ok": d.get("ok", False),
        "summary": f"Images: {d.get('image_source_count', 0)}, Subjects: {d.get('subject_count', 0)}",
        "key_metrics": {
            "image_count": d.get("image_source_count", 0),
            "subject_count": d.get("subject_count", 0),
            "checks_total": checks_total,
            "checks_passed": checks_passed,
        },
        "warnings": d.get("warnings", [])[:10],
        "errors": d.get("errors", [])[:10],
        "next_actions": d.get("next_actions", [])[:5],
    }


def _normalize_status(raw: str) -> str:
    """Normalize status strings from sub-services to the dashboard literal."""
    mapping = {"fail": "blocked", "pass": "ready", "warn": "warning"}
    return mapping.get(raw, raw)


def _run_bids_validation(project_id: str) -> dict[str, Any]:
    from src.backend.app.services.bids_validation import validate_bids
    project = mock_store.get_project(project_id)
    roots: list[str] = []
    if project:
        metadata = project.metadata if isinstance(project.metadata, dict) else {}
        rawdata = metadata.get("rawdata_dir")
        if rawdata and isinstance(rawdata, str):
            roots.append(rawdata)
    try:
        import_roots = mock_store.list_import_paths(project_id)
        for r in import_roots:
            if r not in roots:
                roots.append(r)
    except Exception:
        pass
    r = validate_bids(roots)
    d = r.model_dump()
    return {
        "status": _normalize_status(d.get("status", "unknown")),
        "ok": d.get("ok", False),
        "summary": f"Issues: {d.get('issues_count', 0)}, Warnings: {d.get('warning_count', 0)}",
        "key_metrics": {
            "issues_count": d.get("issues_count", 0),
            "warning_count": d.get("warning_count", 0),
        },
        "warnings": d.get("warnings", [])[:10],
        "errors": d.get("errors", [])[:10],
        "next_actions": d.get("next_actions", [])[:5],
    }


def _run_conversion_dry_run(project_id: str) -> dict[str, Any]:
    from src.backend.app.services.conversion_planner import plan_conversion
    from src.backend.app.schemas.desktop import ConversionDryRunRequest
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
        return {"status": "not_run", "ok": False, "summary": str(exc)[:200],
                "key_metrics": {}, "warnings": [], "errors": [str(exc)], "next_actions": []}


def _run_nifti_qc_snapshot(project_id: str) -> dict[str, Any]:
    from src.backend.app.services.nifti_qc_snapshot import build_nifti_qc_snapshot
    r = build_nifti_qc_snapshot(project_id)
    d = r.model_dump()
    return {
        "status": d.get("status", "unknown"),
        "ok": d.get("ok", False),
        "summary": f"Images: {d.get('image_count', 0)}, Readable: {d.get('readable_count', 0)}",
        "key_metrics": {
            "image_count": d.get("image_count", 0),
            "readable_count": d.get("readable_count", 0),
            "four_d_count": d.get("four_d_count", 0),
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
        return {"status": "not_run", "ok": False, "summary": str(exc)[:200],
                "key_metrics": {}, "warnings": [], "errors": [str(exc)], "next_actions": []}


def _run_rsfmri_qc_planning(project_id: str) -> dict[str, Any]:
    try:
        from src.backend.app.services.rsfmri_qc_planning_report import build_rsfmri_qc_planning_report
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
        return {"status": "not_run", "ok": False, "summary": str(exc)[:200],
                "key_metrics": {}, "warnings": [], "errors": [str(exc)], "next_actions": []}


def _build_markdown(
    project_id: str, generated_at: str, overall_status: str,
    modules: list[dict[str, Any]],
    ready: int, warning: int, blocked: int, unknown: int,
    all_warnings: list[str], all_errors: list[str],
    next_actions: list[str],
) -> str:
    lines = [
        f"# QC Dashboard Summary Report",
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
        na = (m.get("next_actions") or ["—"])[:1]
        lines.append(
            f"| {m['name']} | {m['status']} | {m.get('summary', '')[:60]} "
            f"| {len(m.get('warnings', []))} | {na[0][:50] if na else '—'} |"
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

    lines.extend([
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
    ])

    return "\n".join(lines) + "\n"


def build_qc_dashboard_report(project_id: str, cache_mode: str = "off") -> QcDashboardReportResponse:
    project = mock_store.get_project(project_id)
    if project is None:
        return QcDashboardReportResponse(
            ok=False, project_id=project_id, status="blocked",
            generated_at=_now_iso(), report_dir="", json_path="", markdown_path="",
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
        metadata = (project.metadata if isinstance(project.metadata, dict) else {}) if project else {}
        roots = collect_qc_dashboard_fingerprint_roots(metadata)
        fp = build_rawdata_fingerprint(roots)
        fingerprint_str = fp.fingerprint

    for mod in _MODULES:
        fn_name = mod["fn"]
        fn = globals().get(fn_name)
        if fn is None:
            modules.append({
                "id": mod["id"], "name": mod["name"],
                "status": "not_run", "ok": False,
                "summary": f"Internal: {fn_name} not found",
                "key_metrics": {}, "warnings": [], "errors": [],
                "next_actions": [],
            })
            continue

        # ── Module-level caching for nifti_qc_snapshot ──
        cache_rec: Any = None
        if mod["id"] == "nifti_qc_snapshot" and cache_mode != "off":
            cache_key = build_module_cache_key(
                project_id=project_id, module_id="nifti_qc_snapshot",
                fingerprint=fingerprint_str,
            )
            if cache_mode == "prefer":
                cached_payload, cache_rec = load_module_cache(
                    project_id=project_id, module_id="nifti_qc_snapshot",
                    cache_key=cache_key,
                )
                if cached_payload is not None:
                    result = cached_payload
                    module_hits["nifti_qc_snapshot"] = True
                    cache_records.append(cache_rec)
                    modules.append({
                        "id": mod["id"], "name": mod["name"],
                        "status": result.get("status", "unknown"),
                        "ok": result.get("ok", False),
                        "summary": result.get("summary", ""),
                        "key_metrics": result.get("key_metrics", {}),
                        "warnings": result.get("warnings", []),
                        "errors": result.get("errors", []),
                        "next_actions": result.get("next_actions", []),
                    })
                    continue  # skip execution for this module

        try:
            result = fn(project_id)
        except Exception as exc:
            result = {
                "status": "unknown", "ok": False,
                "summary": f"Error: {exc}",
                "key_metrics": {}, "warnings": [], "errors": [str(exc)],
                "next_actions": [],
            }

        # ── Save cache on refresh for nifti_qc_snapshot ──
        if mod["id"] == "nifti_qc_snapshot" and cache_mode == "refresh" and fingerprint_str:
            cache_key = build_module_cache_key(
                project_id=project_id, module_id="nifti_qc_snapshot",
                fingerprint=fingerprint_str,
            )
            cache_rec = save_module_cache(
                project_id=project_id, module_id="nifti_qc_snapshot",
                cache_key=cache_key, payload=result,
                fingerprint=fingerprint_str,
            )
            cache_records.append(cache_rec)

        modules.append({
            "id": mod["id"],
            "name": mod["name"],
            "status": result["status"],
            "ok": result["ok"],
            "summary": result["summary"],
            "key_metrics": result["key_metrics"],
            "warnings": result["warnings"],
            "errors": result["errors"],
            "next_actions": result["next_actions"],
        })

        all_warnings.extend(result["warnings"][:5])
        all_errors.extend(result["errors"][:5])

    # Overall status
    essential_ids = {m["id"] for m in _MODULES if m["essential"]}
    blocked_count = sum(1 for m in modules if m["status"] == "blocked" and m["id"] in essential_ids)
    non_essential_ready_or_warn = [
        m for m in modules
        if m["id"] not in essential_ids and m["status"] in ("ready", "warning")
    ]
    warning_count = sum(1 for m in modules if m["status"] == "warning")
    ready_count = sum(1 for m in modules if m["status"] == "ready")
    unknown_count = sum(1 for m in modules if m["status"] not in ("ready", "warning", "blocked", "not_run"))

    if blocked_count > 0:
        overall_status = "blocked"
    elif warning_count > 0:
        overall_status = "warning"
    elif ready_count > 0:
        overall_status = "ready"
    else:
        overall_status = "unknown"

    # Deduplicate next actions while preserving order
    seen_actions = set()
    next_actions = []
    for m in modules:
        for a in m.get("next_actions", [])[:2]:
            if a:
                normalized = a.strip().lower()
                if normalized not in seen_actions:
                    seen_actions.add(normalized)
                    next_actions.append(a)

    _PRIORITY_TERMS = [
        "dicom-to-bids",
        "dicom-to-nifti",
        "conversion dry-run",
        "conversion preflight",
        "run conversion",
        "persist review package",
        "register converted",
        "create preprocessing run",
    ]

    def _action_priority(act: str) -> int:
        act_lower = act.lower()
        for idx, term in enumerate(_PRIORITY_TERMS):
            if term in act_lower:
                return idx
        return len(_PRIORITY_TERMS)

    next_actions.sort(key=_action_priority)
    next_actions = next_actions[:5]

    # Build markdown
    markdown = _build_markdown(
        project_id, now, overall_status, modules,
        ready_count, warning_count, blocked_count, unknown_count,
        all_warnings, all_errors,
        next_actions,
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
    }
    json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")

    model_modules = [
        QcDashboardModuleSummary(
            module_id=m["id"], name=m["name"], status=m["status"],
            ok=m["ok"], summary=m["summary"],
            key_metrics=m["key_metrics"],
            warnings=m["warnings"], errors=m["errors"],
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
            cache_mode, cache_records=cache_records, module_hits=module_hits,
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

    markdown = ""
    if md_path.is_file():
        try:
            markdown = md_path.read_text(encoding="utf-8")
        except Exception:
            markdown = ""

    modules_raw = data.get("modules", []) or []
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

    return QcDashboardReportResponse(
        ok=data.get("overall_status", "unknown") != "blocked",
        project_id=data.get("project_id", project_id),
        status=data.get("overall_status", "ready"),
        generated_at=data.get("generated_at", ""),
        report_dir=str(report_dir),
        json_path=str(json_path),
        markdown_path=str(md_path),
        artifacts=[
            QcDashboardReportArtifact(kind="json", path=str(json_path), exists=True, size_bytes=json_stat.st_size),
            QcDashboardReportArtifact(kind="markdown", path=str(md_path), exists=md_path.is_file(), size_bytes=md_stat.st_size if md_stat else None),
        ],
        modules=model_modules,
        ready_count=data.get("ready_count", 0),
        warning_count=data.get("warning_count", 0),
        blocked_count=data.get("blocked_count", 0),
        unknown_count=data.get("unknown_count", 0),
        overall_warnings=data.get("warnings", []),
        overall_errors=data.get("errors", []),
        next_actions=[],
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
        cache_warnings.append(
            "Cache mode 'prefer' is accepted, but no cached data was found."
        )
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
