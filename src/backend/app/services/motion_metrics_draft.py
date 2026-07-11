"""Pure-Python motion metrics draft generator.

Reads existing motion parameter (rp_*.txt) or confounds TSV files,
computes lightweight QC summary metrics, and writes JSON/Markdown
artifacts.  Never runs realignment, never calls external tools.
"""

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.backend.app.schemas.desktop import (
    MotionMetricsDraftArtifact,
    MotionMetricsDraftResponse,
    MotionMetricsSubjectSummary,
)
from src.backend.app.services.mock_store import mock_store
from src.backend.app.services.motion_qc_readiness import build_motion_qc_readiness

_REPORT_ROOT = Path("outputs/reports/motion_metrics_draft")
_MAX_PARSE_BYTES = 10 * 1024 * 1024  # 10 MB cap


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in value)[:80]


def _report_dir(project_id: str) -> Path:
    return (_REPORT_ROOT / _safe_slug(project_id)).resolve()


def _write_json(path: Path, data: Any) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(data, ensure_ascii=False, indent=2)
    path.write_text(encoded, encoding="utf-8")
    return len(encoded.encode("utf-8"))


def _write_markdown(path: Path, text: str) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = text.encode("utf-8")
    path.write_text(text, encoding="utf-8")
    return len(encoded)


def _safe_float(values: list[float]) -> float | None:
    """Return the float if values is non-empty, else None."""
    return values[0] if values else None


def _abs(values: list[float]) -> list[float]:
    return [abs(v) for v in values]


def _parse_spm_rp(path: Path) -> dict[str, Any] | None:
    """Parse SPM rp_*.txt (N rows × 6 columns)."""
    try:
        size = path.stat().st_size
    except OSError:
        return {"error": "File not accessible."}
    if size > _MAX_PARSE_BYTES:
        return {"error": f"File too large ({size} bytes, cap {_MAX_PARSE_BYTES})."}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return {"error": f"Read failed: {exc}"}

    rows: list[list[float]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        try:
            values = [float(p) for p in parts[:6]]
        except ValueError:
            continue
        if len(values) == 6:
            rows.append(values)

    if not rows:
        return {"error": "No valid motion rows found."}

    trans_x = [r[0] for r in rows]
    trans_y = [r[1] for r in rows]
    trans_z = [r[2] for r in rows]
    rot_x   = [r[3] for r in rows]
    rot_y   = [r[4] for r in rows]
    rot_z   = [r[5] for r in rows]

    return {
        "parsed": True,
        "source_type": "spm_rp_txt",
        "row_count": len(rows),
        "volume_count_from_motion_rows": len(rows),
        "has_fd": False,
        "max_abs_translation_mm": _safe_float([max(_abs(trans_x)), max(_abs(trans_y)), max(_abs(trans_z))]) if trans_x else None,
        "mean_abs_translation_mm": _safe_float([sum(_abs(trans_x)) / len(trans_x) if trans_x else 0, sum(_abs(trans_y)) / len(trans_y) if trans_y else 0, sum(_abs(trans_z)) / len(trans_z) if trans_z else 0]) if trans_x else None,
        "max_abs_rotation_rad": _safe_float([max(_abs(rot_x)), max(_abs(rot_y)), max(_abs(rot_z))]) if rot_x else None,
        "mean_abs_rotation_rad": _safe_float([sum(_abs(rot_x)) / len(rot_x) if rot_x else 0, sum(_abs(rot_y)) / len(rot_y) if rot_y else 0, sum(_abs(rot_z)) / len(rot_z) if rot_z else 0]) if rot_x else None,
    }


def _parse_confounds_tsv(path: Path) -> dict[str, Any] | None:
    """Parse confounds TSV, looking for FD and motion columns."""
    try:
        size = path.stat().st_size
    except OSError:
        return {"error": "File not accessible."}
    if size > _MAX_PARSE_BYTES:
        return {"error": f"File too large ({size} bytes, cap {_MAX_PARSE_BYTES})."}

    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            reader = csv.reader(handle, delimiter="\t")
            header = next(reader, [])
            if not header:
                return {"error": "Empty or missing header."}
    except Exception as exc:
        return {"error": f"Read failed: {exc}"}

    fd_cols = {"framewise_displacement", "fd", "FD"}
    mot_cols = {"trans_x", "trans_y", "trans_z", "rot_x", "rot_y", "rot_z"}

    col_index: dict[str, int] = {}
    for idx, col in enumerate(header):
        name = col.strip()
        if name in fd_cols or name in mot_cols or name.lower() in fd_cols:
            col_index[name] = idx

    rows: list[dict[str, float]] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle2:
            rdr = csv.reader(handle2, delimiter="\t")
            next(rdr, None)  # skip header
            for line in rdr:
                row: dict[str, float] = {}
                for name, idx in col_index.items():
                    try:
                        row[name] = float(line[idx])
                    except (IndexError, ValueError):
                        continue
                if row:
                    rows.append(row)
    except Exception:
        pass

    if not rows:
        return {"error": "No valid data rows found."}

    fd_candidates = [r[name] for r in rows for name in r if name in fd_cols]
    has_fd = len(fd_candidates) > 0

    result: dict[str, Any] = {
        "parsed": True,
        "source_type": "confounds_tsv",
        "row_count": len(rows),
        "volume_count_from_motion_rows": len(rows),
        "has_fd": has_fd,
    }

    if has_fd:
        fds = [abs(v) for v in fd_candidates]
        result["fd_mean"] = sum(fds) / len(fds) if fds else None
        result["fd_max"] = max(fds) if fds else None
        result["fd_over_0_2_count"] = sum(1 for v in fds if v > 0.2)
        result["fd_over_0_5_count"] = sum(1 for v in fds if v > 0.5)
        result["fd_over_0_2_fraction"] = sum(1 for v in fds if v > 0.2) / len(fds) if fds else None
        result["fd_over_0_5_fraction"] = sum(1 for v in fds if v > 0.5) / len(fds) if fds else None

    # Translation/rotation from confounds if present
    mt_cols = {k: [r[k] for r in rows if k in r] for k in mot_cols if any(k in r for r in rows)}
    if mt_cols:
        if "trans_x" in mt_cols and "trans_y" in mt_cols and "trans_z" in mt_cols:
            result["max_abs_translation_mm"] = _safe_float([
                max(_abs(mt_cols.get("trans_x", [0]))),
                max(_abs(mt_cols.get("trans_y", [0]))),
                max(_abs(mt_cols.get("trans_z", [0]))),
            ])
            result["mean_abs_translation_mm"] = _safe_float([
                sum(_abs(mt_cols["trans_x"])) / len(mt_cols["trans_x"]) if mt_cols["trans_x"] else 0,
                sum(_abs(mt_cols["trans_y"])) / len(mt_cols["trans_y"]) if mt_cols["trans_y"] else 0,
                sum(_abs(mt_cols["trans_z"])) / len(mt_cols["trans_z"]) if mt_cols["trans_z"] else 0,
            ])
        if "rot_x" in mt_cols and "rot_y" in mt_cols and "rot_z" in mt_cols:
            result["max_abs_rotation_rad"] = _safe_float([
                max(_abs(mt_cols.get("rot_x", [0]))),
                max(_abs(mt_cols.get("rot_y", [0]))),
                max(_abs(mt_cols.get("rot_z", [0]))),
            ])
            result["mean_abs_rotation_rad"] = _safe_float([
                sum(_abs(mt_cols["rot_x"])) / len(mt_cols["rot_x"]) if mt_cols["rot_x"] else 0,
                sum(_abs(mt_cols["rot_y"])) / len(mt_cols["rot_y"]) if mt_cols["rot_y"] else 0,
                sum(_abs(mt_cols["rot_z"])) / len(mt_cols["rot_z"]) if mt_cols["rot_z"] else 0,
            ])

    return result


def _parseable_motion_paths(candidate: dict[str, Any]) -> list[Path]:
    """Return metric sources worth parsing for one BOLD candidate.

    Readiness may surface auxiliary native TSV outputs such as Friston design
    matrices next to the actual FD series.  Prefer the explicit FD source when
    present so those auxiliary files do not become misleading dashboard
    warnings.
    """

    fd_source = candidate.get("fd_source_path")
    if isinstance(fd_source, str) and fd_source:
        return [Path(fd_source)]

    paths: list[Path] = []
    for raw in candidate.get("motion_param_paths", []) or []:
        path = Path(str(raw))
        name = path.name.lower()
        if name.startswith("rp_") and name.endswith(".txt"):
            paths.append(path)
        elif name.endswith(".tsv") and (
            "confound" in name
            or "framewise_displacement" in name
            or "fd" in name
        ):
            paths.append(path)
    return sorted(set(paths))


def _qc_flags(metrics: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    fd = metrics.get("fd_mean")
    if fd is not None and fd > 0.2:
        flags.append("FD mean exceeds 0.2 mm — review suggested.")
    if fd is not None and fd > 0.5:
        flags.append("FD mean exceeds 0.5 mm — significant motion, review suggested.")
    frac = metrics.get("fd_over_0_2_fraction")
    if frac is not None and frac > 0.2:
        flags.append("More than 20% of volumes exceed FD 0.2 mm — review suggested.")
    return flags


def _build_markdown(
    project_id: str, generated_at: str, overall: str,
    warnings_list: list[str], next_actions: list[str],
    summaries: list[dict[str, Any]],
) -> str:
    lines: list[str] = [
        "# Motion Metrics Draft Report",
        "",
        f"**Generated:** {generated_at}",
        f"**Project:** `{project_id}`",
        f"**Status:** {overall}",
        "",
        "---",
        "",
        "## ⚠️ Research-Use Only",
        "",
        "This report is a **QC summary artifact** for research workflows. "
        "It does not constitute clinical interpretation or diagnosis. "
        "No realignment or motion correction has been executed.",
        "",
        "---",
        "",
        "## Safety Flags",
        "",
        "| Flag | Value |",
        "|------|-------|",
        "| read_only_inputs | ✅ |",
        "| rawdata_not_modified | ✅ |",
        "| no_realign_executed | ✅ |",
        "| no_external_tools_executed | ✅ |",
        "| qc_summary_only | ✅ |",
        "| no_clinical_interpretation | ✅ |",
        "",
        "---",
        "",
        "## Subject Summaries",
        "",
    ]

    if summaries:
        lines.extend([
            "| Subject | Source | Rows | FD | Max Trans (mm) | Max Rot (rad) | FD Mean | FD Max | FD>0.2 | QC Flags |",
            "|---------|--------|------|----|----------------|---------------|---------|--------|--------|----------|",
        ])
        for s in summaries[:30]:
            subj = s.get("subject_id") or "-"
            src = s.get("source_type", "-")
            rows = str(s.get("row_count", 0))
            fd = "✓" if s.get("has_fd") else "✗"
            mt = f"{s.get('max_abs_translation_mm', '-'):.2f}" if isinstance(s.get("max_abs_translation_mm"), float) else "-"
            mr = f"{s.get('max_abs_rotation_rad', '-'):.4f}" if isinstance(s.get("max_abs_rotation_rad"), float) else "-"
            fdm = f"{s.get('fd_mean', '-'):.3f}" if isinstance(s.get("fd_mean"), float) else "-"
            fdx = f"{s.get('fd_max', '-'):.3f}" if isinstance(s.get("fd_max"), float) else "-"
            fdc = str(s.get("fd_over_0_2_count", "-"))
            qc = "; ".join(s.get("qc_flags", [])[:2]) or "-"
            lines.append(f"| {subj} | {src} | {rows} | {fd} | {mt} | {mr} | {fdm} | {fdx} | {fdc} | {qc} |")
        lines.append("")
    else:
        lines.append("No motion metrics could be computed from available files.")
        lines.append("")

    if warnings_list:
        lines.extend(["## Warnings", ""])
        for w in warnings_list[:20]:
            lines.append(f"- ⚠️ {w}")
        lines.append("")

    if next_actions:
        lines.extend(["## Next Actions", ""])
        for a in next_actions[:10]:
            lines.append(f"- {a}")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## Non-Goals",
        "",
        "- No realignment executed.",
        "- No motion correction performed.",
        "- No clinical interpretation.",
        "- No rawdata modification.",
        "",
        f"*Report generated {generated_at}*",
    ])
    return "\n".join(lines) + "\n"


def build_motion_metrics_draft(project_id: str) -> MotionMetricsDraftResponse:
    """Generate motion metrics draft from existing motion/confounds files."""

    now = _now_iso()
    warnings: list[str] = []
    errors: list[str] = []

    project = mock_store.get_project(project_id)
    if project is None:
        return MotionMetricsDraftResponse(
            ok=False, project_id=project_id, status="blocked", generated_at=now,
            report_dir="", json_path="", markdown_path="",
            errors=[f"Project not found: {project_id}"],
            safety_flags=_safety_flags(),
        )

    readiness = build_motion_qc_readiness(project_id)
    ready_dict = readiness.model_dump()

    summaries: list[dict[str, Any]] = []
    parsed_count = 0
    fd_count = 0

    for candidate in ready_dict.get("candidates", []):
        motion_paths = _parseable_motion_paths(candidate)
        if not motion_paths:
            continue
        for mp in motion_paths:
            path = mp
            subj = candidate.get("subject_id")
            sess = candidate.get("session_id")
            bold = candidate.get("bold_path")

            result = None
            name = path.name.lower()
            if name.startswith("rp_") and name.endswith(".txt"):
                result = _parse_spm_rp(path)
            elif name.endswith(".tsv"):
                result = _parse_confounds_tsv(path)
            else:
                continue

            if result is None:
                continue
            if "error" in result:
                warnings.append(f"{path.name}: {result['error']}")
                summaries.append({
                    "subject_id": subj, "session_id": sess, "bold_path": bold,
                    "source_path": str(path), "source_type": "unknown",
                    "parsed": False, "row_count": 0, "has_fd": False,
                    "warnings": [result["error"]],
                    "qc_flags": [],
                })
                continue

            result["subject_id"] = subj
            result["session_id"] = sess
            result["bold_path"] = bold
            result["source_path"] = str(path)
            result.setdefault("qc_flags", [])
            result["qc_flags"] = _qc_flags(result)
            result.setdefault("warnings", [])
            summaries.append(result)
            parsed_count += 1
            if result.get("has_fd"):
                fd_count += 1

    # Status
    if not summaries or parsed_count == 0:
        overall = "blocked"
    elif parsed_count < len(summaries):
        overall = "warning"
    else:
        overall = "ready"

    next_actions: list[str] = []
    if fd_count == 0:
        next_actions.append("No FD data available. Run realignment to generate FD values.")
    if parsed_count > 0 and fd_count > 0:
        next_actions.append(f"{fd_count} candidate(s) have FD data. Review FD threshold counts for potential high-motion subjects.")
    if any(s.get("qc_flags") for s in summaries):
        next_actions.append("Review flagged subjects — FD thresholds exceeded.")

    # Write artifacts
    report_dir = _report_dir(project_id)
    json_path = report_dir / "motion_metrics_draft.json"
    md_path = report_dir / "motion_metrics_draft.md"

    json_data: dict[str, Any] = {
        "project_id": project_id, "generated_at": now, "status": overall,
        "safety_flags": _safety_flags(),
        "candidate_count": len(summaries), "parsed_count": parsed_count,
        "fd_available_count": fd_count, "summaries": summaries,
        "warnings": warnings[:30], "next_actions": next_actions[:10],
    }

    md_text = _build_markdown(project_id, now, overall, warnings, next_actions, summaries)

    json_size = _write_json(json_path, json_data)
    md_size = _write_markdown(md_path, md_text)

    artifacts = [
        {"kind": "json", "path": str(json_path), "exists": json_path.is_file(), "size_bytes": json_size},
        {"kind": "markdown", "path": str(md_path), "exists": md_path.is_file(), "size_bytes": md_size},
    ]

    return MotionMetricsDraftResponse(
        ok=True, project_id=project_id, status=overall, generated_at=now,
        report_dir=str(report_dir), json_path=str(json_path), markdown_path=str(md_path),
        artifacts=[MotionMetricsDraftArtifact(**a) for a in artifacts],
        candidate_count=len(summaries), parsed_count=parsed_count,
        fd_available_count=fd_count,
        summaries=[MotionMetricsSubjectSummary(**s) for s in summaries],
        warnings=warnings[:30], errors=errors[:20],
        next_actions=next_actions[:10],
        safety_flags=_safety_flags(),
        report_markdown=md_text,
    )


def _safety_flags() -> dict[str, bool]:
    return {
        "read_only_inputs": True,
        "rawdata_not_modified": True,
        "no_realign_executed": True,
        "no_external_tools_executed": True,
        "qc_summary_only": True,
        "no_clinical_interpretation": True,
    }
