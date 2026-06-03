from __future__ import annotations
import csv
from pathlib import Path
from statistics import mean
from typing import Any

from src.backend.app.tools.artifact_utils import read_json_artifact, write_json_artifact

STAGE_ORDER = ["slice_timing","motion","registration","segmentation","normalization","smoothing","confounds","nuisance_regression","temporal_filtering","alff_falff","reho","functional_connectivity"]
STAGE_FILES = {
    "slice_timing": ("slice_timing_qc.json", ["slice_timing_status","slice_timing_qc_status"]),
    "motion": ("motion_qc.json", ["motion_qc_status","motion_status"]),
    "registration": ("registration_qc.json", ["registration_qc_status"]),
    "segmentation": ("tissue_qc.json", ["segmentation_qc_status"]),
    "normalization": ("normalization_qc.json", ["normalization_qc_status"]),
    "smoothing": ("smoothing_qc.json", ["smoothing_qc_status"]),
    "nuisance_regression": ("nuisance_regression_qc.json", ["regression_qc_status"]),
    "temporal_filtering": ("temporal_filtering_qc.json", ["filtering_qc_status"]),
    "alff_falff": ("alff_falff_qc.json", ["alff_qc_status"]),
    "reho": ("reho_qc.json", ["reho_qc_status"]),
    "functional_connectivity": ("functional_connectivity_qc.json", ["fc_qc_status"]),
}

def _safe_float(value: Any) -> float | None:
    if value is None: return None
    try: return float(value)
    except Exception: return None

def _mean(values: list[Any]) -> float | None:
    nums = [_safe_float(v) for v in values]; nums = [v for v in nums if v is not None]
    return float(mean(nums)) if nums else None

def _discover_subjects(derivatives: Path) -> list[str]:
    subjects = set()
    for base_name in ["rsfmri_qc","rsfmri_preproc","rsfmri_metrics","rsfmri_fc","rsfmri_confounds"]:
        base = derivatives / base_name
        if not base.exists(): continue
        for child in base.iterdir():
            if child.is_dir() and child.name.startswith("sub-"): subjects.add(child.name)
    return sorted(subjects)

def _status_from_payload(payload: dict[str, Any] | None, keys: list[str]) -> str:
    if not payload: return "MISSING"
    for k in keys:
        v = payload.get(k)
        if isinstance(v, str) and v: return v.upper()
    if payload.get("ok") is True: return "PASS"
    if payload.get("ok") is False: return "FAIL"
    return "UNKNOWN"

def _wc(payload: dict[str, Any] | None) -> int:
    if not payload: return 0
    w = payload.get("warnings", []); return len(w) if isinstance(w, list) else 0

def _ec(payload: dict[str, Any] | None) -> int:
    if not payload: return 0
    e = payload.get("errors", []); return len(e) if isinstance(e, list) else 0

def _read_subject_qc(derivatives: Path, subject_id: str) -> dict[str, Any]:
    qc_dir = derivatives / "rsfmri_qc" / subject_id; conf_dir = derivatives / "rsfmri_confounds" / subject_id
    payloads: dict[str, Any] = {}
    for stage, (fn, _) in STAGE_FILES.items(): payloads[stage] = {"path": str(qc_dir / fn), "payload": read_json_artifact(qc_dir / fn)}
    payloads["confounds"] = {"path": str(conf_dir / "confound_qc.json"), "payload": read_json_artifact(conf_dir / "confound_qc.json")}
    return payloads

def _extract_row(subject_id: str, payloads: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {"subject_id": subject_id}; wt = 0; et = 0
    for stage in STAGE_ORDER:
        if stage == "confounds": payload = payloads.get(stage, {}).get("payload"); status = _status_from_payload(payload, ["confound_qc_status"])
        else:
            _, keys = STAGE_FILES.get(stage, ("", [])); payload = payloads.get(stage, {}).get("payload"); status = _status_from_payload(payload, keys)
        row[f"{stage}_status"] = status; wt += _wc(payload); et += _ec(payload)
    row["warnings_total"] = wt; row["errors_total"] = et

    mo = payloads.get("motion",{}).get("payload") or {}; se = payloads.get("segmentation",{}).get("payload") or {}
    no = payloads.get("normalization",{}).get("payload") or {}; sm = payloads.get("smoothing",{}).get("payload") or {}
    co = payloads.get("confounds",{}).get("payload") or {}; nu = payloads.get("nuisance_regression",{}).get("payload") or {}
    fi = payloads.get("temporal_filtering",{}).get("payload") or {}; al = payloads.get("alff_falff",{}).get("payload") or {}
    rh = payloads.get("reho",{}).get("payload") or {}; fc = payloads.get("functional_connectivity",{}).get("payload") or {}

    row["mean_fd"] = _safe_float(mo.get("mean_fd")) or _safe_float(mo.get("framewise_displacement_mean")) or _safe_float(mo.get("fd_mean"))
    row["max_fd"] = _safe_float(mo.get("max_fd")) or _safe_float(mo.get("framewise_displacement_max")) or _safe_float(mo.get("fd_max"))
    row["gm_volume_mm3"] = _safe_float(se.get("gm_volume_mm3")); row["wm_volume_mm3"] = _safe_float(se.get("wm_volume_mm3")); row["csf_volume_mm3"] = _safe_float(se.get("csf_volume_mm3"))
    row["normalization_finite_fraction"] = _safe_float(no.get("finite_fraction")); row["smoothing_variance_ratio"] = _safe_float(sm.get("variance_reduction_ratio"))
    row["confound_rows"] = _safe_float((co.get("qc") or {}).get("rows")); row["confound_columns"] = _safe_float((co.get("qc") or {}).get("columns")); row["confound_rank"] = _safe_float((co.get("qc") or {}).get("rank"))
    row["regression_variance_ratio"] = _safe_float(nu.get("variance_ratio")); row["filtering_retained_frequency_fraction"] = _safe_float(fi.get("retained_frequency_fraction"))
    row["filtering_variance_ratio"] = _safe_float(fi.get("variance_ratio")); row["alff_mean"] = _safe_float(al.get("alff_mean")); row["falff_mean"] = _safe_float(al.get("falff_mean"))
    row["reho_mean"] = _safe_float(rh.get("reho_mean")); row["reho_valid_voxel_count"] = _safe_float(rh.get("valid_voxel_count"))
    row["fc_roi_count"] = _safe_float(fc.get("roi_count")); row["fc_empty_roi_count"] = _safe_float(fc.get("empty_roi_count")); row["fc_diagonal_mean"] = _safe_float(fc.get("diagonal_mean"))
    return row

def _status_counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out = {}
    for stage in STAGE_ORDER:
        counts = {"PASS":0,"WARNING":0,"FAIL":0,"MISSING":0,"UNKNOWN":0}
        for r in rows:
            s = str(r.get(f"{stage}_status","UNKNOWN")).upper(); counts[s] = counts.get(s,0) + 1
        out[stage] = counts
    return out

def _completeness(rows: list[dict[str, Any]]) -> dict[str, Any]:
    matrix = []
    for r in rows:
        stages = [{"stage": s, "status": str(r.get(f"{s}_status","MISSING")).upper(), "complete": str(r.get(f"{s}_status","MISSING")).upper() in {"PASS","WARNING"}} for s in STAGE_ORDER]
        matrix.append({"subject_id": r["subject_id"], "stages": stages})
    return {"stage_order": STAGE_ORDER, "subjects": matrix}

def _contracts(work: Path) -> dict[str, Any]:
    cpaths = []
    for base in [work / "dpabi" / "contracts", work / "gpu" / "contracts"]:
        if not base.exists(): continue
        cpaths.extend(sorted(base.glob("*.json")))
    contracts = []
    for path in cpaths:
        p = read_json_artifact(path)
        contracts.append({"path": str(path), "exists": path.exists(), "backend_id": p.get("backend_id") if p else None, "status": p.get("status") if p else None, "execution_allowed": p.get("execution_allowed") if p else None, "gpu_executed": p.get("gpu_executed") if p else None, "dpabi_executed": (p.get("safety") or {}).get("dpabi_executed") if p else None, "payload_ok": p.get("ok") if p else False})
    return {"contracts_total": len(contracts), "contracts": contracts}

def _runs(work: Path, max_runs: int = 20) -> list[dict[str, Any]]:
    rp = sorted((work / "pipeline_runs").glob("*/summary.json"))[-max_runs:]
    runs = []
    for path in rp:
        p = read_json_artifact(path)
        if not p: continue
        runs.append({"path": str(path), "status": p.get("status"), "pipeline_id": p.get("pipeline_id"), "run_id": p.get("run_id"), "started_at": p.get("started_at"), "finished_at": p.get("finished_at")})
    return runs

def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = ["subject_id", *[f"{s}_status" for s in STAGE_ORDER], "warnings_total","errors_total","mean_fd","max_fd","gm_volume_mm3","wm_volume_mm3","csf_volume_mm3","normalization_finite_fraction","smoothing_variance_ratio","confound_rows","confound_columns","confound_rank","regression_variance_ratio","filtering_retained_frequency_fraction","filtering_variance_ratio","alff_mean","falff_mean","reho_mean","reho_valid_voxel_count","fc_roi_count","fc_empty_roi_count","fc_diagonal_mean"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in rows: w.writerow({k: r.get(k) for k in fields})

def _write_md(path: Path, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    lines = ["# rs-fMRI Group Dataset Summary", "", "## Overview", "", f"- Subjects total: {summary.get('subjects_total')}", f"- Subjects with QC: {summary.get('subjects_with_any_qc')}", f"- Warnings: {summary.get('warnings_total')}", f"- Errors: {summary.get('errors_total')}", "", "## Key Metrics", ""]
    for k, v in summary.get("metric_means", {}).items(): lines.append(f"- {k}: {v}")
    lines += ["", "## Stage Status Counts", "", "| Stage | PASS | WARNING | FAIL | MISSING |", "|---|---:|---:|---:|---:|"]
    for stage, counts in summary.get("stage_status_counts", {}).items(): lines.append(f"| {stage} | {counts.get('PASS',0)} | {counts.get('WARNING',0)} | {counts.get('FAIL',0)} | {counts.get('MISSING',0)} |")
    lines += ["", "## Subject Table", "", "| Subject | FC | ALFF/fALFF | ReHo | Warnings | Errors |", "|---|---|---|---|---:|---:|"]
    for r in rows: lines.append(f"| {r.get('subject_id')} | {r.get('functional_connectivity_status')} | {r.get('alff_falff_status')} | {r.get('reho_status')} | {r.get('warnings_total')} | {r.get('errors_total')} |")
    lines += ["", "## Safety", "", "Read-only aggregation. No rawdata modification, no SPM/MATLAB/DPABI/GPU execution, no statistical inference."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def build_group_dataset_summary(derivatives_dir: str = "./derivatives", reports_dir: str = "./reports", work_dir: str = "./work") -> dict[str, Any]:
    d = Path(derivatives_dir); rpt = Path(reports_dir); w = Path(work_dir)
    out = rpt / "rsfmri" / "group_summary"; out.mkdir(parents=True, exist_ok=True)
    dsj = out / "dataset_summary.json"; ddj = out / "dashboard_data.json"; smc = out / "subject_metrics_table.csv"
    pcj = out / "pipeline_completeness.json"; coj = out / "contracts_overview.json"; rm = out / "dataset_summary_report.md"

    subs = _discover_subjects(d); rows = []
    for sid in subs: rows.append(_extract_row(sid, _read_subject_qc(d, sid)))

    sc = _status_counts(rows); comp = _completeness(rows); ct = _contracts(w); pr = _runs(w)
    mm = {"mean_fd": _mean([r.get("mean_fd") for r in rows]),"max_fd": _mean([r.get("max_fd") for r in rows]),"gm_volume_mm3": _mean([r.get("gm_volume_mm3") for r in rows]),"wm_volume_mm3": _mean([r.get("wm_volume_mm3") for r in rows]),"csf_volume_mm3": _mean([r.get("csf_volume_mm3") for r in rows]),"normalization_finite_fraction": _mean([r.get("normalization_finite_fraction") for r in rows]),"smoothing_variance_ratio": _mean([r.get("smoothing_variance_ratio") for r in rows]),"regression_variance_ratio": _mean([r.get("regression_variance_ratio") for r in rows]),"filtering_retained_frequency_fraction": _mean([r.get("filtering_retained_frequency_fraction") for r in rows]),"filtering_variance_ratio": _mean([r.get("filtering_variance_ratio") for r in rows]),"alff_mean": _mean([r.get("alff_mean") for r in rows]),"falff_mean": _mean([r.get("falff_mean") for r in rows]),"reho_mean": _mean([r.get("reho_mean") for r in rows]),"reho_valid_voxel_count": _mean([r.get("reho_valid_voxel_count") for r in rows]),"fc_roi_count": _mean([r.get("fc_roi_count") for r in rows]),"fc_empty_roi_count": _mean([r.get("fc_empty_roi_count") for r in rows]),"fc_diagonal_mean": _mean([r.get("fc_diagonal_mean") for r in rows])}
    wt = int(sum(int(r.get("warnings_total",0) or 0) for r in rows)); et = int(sum(int(r.get("errors_total",0) or 0) for r in rows))
    swq = sum(1 for r in rows if any(str(r.get(f"{s}_status")) != "MISSING" for s in STAGE_ORDER))

    summary = {"ok": True, "node_id": "group_dataset_summary", "backend": "python", "subjects_total": len(subs), "subjects_with_any_qc": swq, "stage_order": STAGE_ORDER, "stage_status_counts": sc, "warnings_total": wt, "errors_total": et, "metric_means": mm, "contracts_overview": ct, "pipeline_runs": pr, "outputs": [str(dsj),str(ddj),str(smc),str(pcj),str(coj),str(rm)], "warnings": [], "errors": []}
    dashboard = {"summary_cards": {"subjects_total": len(subs), "subjects_with_any_qc": swq, "warnings_total": wt, "errors_total": et, "contracts_total": ct.get("contracts_total")}, "stage_order": STAGE_ORDER, "stage_status_counts": sc, "metric_means": mm, "subject_rows": rows, "pipeline_completeness": comp, "contracts_overview": ct, "pipeline_runs": pr}

    write_json_artifact(dsj, summary)
    write_json_artifact(ddj, dashboard)
    write_json_artifact(pcj, comp)
    write_json_artifact(coj, ct)
    _write_csv(smc, rows); _write_md(rm, summary, rows)
    return summary
