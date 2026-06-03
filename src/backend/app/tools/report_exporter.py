from __future__ import annotations
import shutil, zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from src.backend.app.tools.artifact_utils import read_json_artifact, sha256_file, write_json_artifact

TEXT_EXTENSIONS = {".json",".md",".csv",".tsv",".txt",".log",".yaml",".yml"}
EXCLUDED_EXTENSIONS = {".nii",".gz",".mat"}

def _now_id() -> str: return datetime.now().strftime("rsfmri_export_%Y%m%d_%H%M%S")
def _iso_now() -> str: return datetime.now().isoformat(timespec="seconds")
def _copy_file(source: Path, destination: Path) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, destination)
    return {"relative_path": None, "source_path": str(source), "size_bytes": int(destination.stat().st_size), "sha256": sha256_file(destination)}

def _safe_collect_files(base: Path, patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    if not base.exists(): return files
    for pattern in patterns: files.extend(sorted(base.glob(pattern)))
    seen = set(); out = []
    for p in files:
        if p.is_file() and p not in seen: out.append(p); seen.add(p)
    return out

def _discover_subjects(derivatives: Path) -> list[str]:
    subjects = set()
    for bn in ["rsfmri_qc","rsfmri_metrics","rsfmri_fc","rsfmri_confounds"]:
        b = derivatives / bn
        if not b.exists(): continue
        for c in b.iterdir():
            if c.is_dir() and c.name.startswith("sub-"): subjects.add(c.name)
    return sorted(subjects)

def _stage_summary(gs: dict[str, Any] | None) -> str:
    if not gs: return "No group summary."
    counts = gs.get("stage_status_counts", {})
    if not isinstance(counts, dict): return "No stage counts."
    lines = ["| Stage | PASS | WARNING | FAIL | MISSING |", "|---|---:|---:|---:|---:|"]
    for stage, item in counts.items():
        item = item or {}
        lines.append(f"| {stage} | {item.get('PASS',0)} | {item.get('WARNING',0)} | {item.get('FAIL',0)} | {item.get('MISSING',0)} |")
    return "\n".join(lines)

def _write_readme(path: Path, export_id: str, summary: dict[str, Any]) -> None:
    lines = [f"# rs-fMRI Report Package: {export_id}", "", "Engineering validation outputs for synthetic rs-fMRI pipeline.", "", "## Contents", "", "- `MANIFEST.json`: file manifest with checksums", "- `index.md`: human-readable index", "- `export_summary.json`: exporter summary", "- `summary/`: group and stage-level reports", "- `subjects/`: subject-level QC and confounds", "- `metrics/`: subject metrics result JSON", "- `fc/`: functional connectivity results", "- `contracts/`: DPABI and GPU backend contracts", "- `pipeline_runs/`: pipeline run summaries", "- `tables/`: CSV/TSV tables", "- `checksums/SHA256SUMS.txt`: checksums", "", "## Safety", "", "Generated from synthetic derivative outputs only. Does not include rawdata and does not make clinical conclusions.", "", "## Export Summary", "", f"- Exported subjects: {summary.get('exported_subjects')}", f"- Exported files: {summary.get('exported_files_total')}", f"- Excluded files: {summary.get('excluded_files_total')}", f"- Warnings: {len(summary.get('warnings',[]))}", f"- Errors: {len(summary.get('errors',[]))}"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def _write_index(path: Path, export_id: str, gs: dict[str, Any] | None, es: dict[str, Any]) -> None:
    lines = [f"# rs-fMRI Dataset Report Index", "", f"- Export ID: `{export_id}`", f"- Created: `{es.get('created_at')}`", f"- Subjects: {es.get('exported_subjects')}", f"- Files: {es.get('exported_files_total')}", "", "## Dataset Overview", ""]
    if gs: lines += [f"- Subjects total: {gs.get('subjects_total')}", f"- With QC: {gs.get('subjects_with_any_qc')}", f"- Warnings: {gs.get('warnings_total')}", f"- Errors: {gs.get('errors_total')}"]
    else: lines.append("Group summary not available.")
    lines += ["", "## Stage Status", "", _stage_summary(gs), "", "## Included Files", "", "- `summary/group_summary/dataset_summary.json`", "- `summary/group_summary/dashboard_data.json`", "- `summary/group_summary/dataset_summary_report.md`", "- `tables/subject_metrics_table.csv`", "- `contracts/`", "", "## Limitations", "", "- Engineering validation only, not clinical report.", "- No rawdata included.", "- No statistical inference performed.", "- No SPM/MATLAB/DPABI/GPU execution."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def _zip_directory(source_dir: Path, zip_path: Path) -> None:
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(source_dir.rglob("*")):
            if p.is_file(): zf.write(p, arcname=str(p.relative_to(source_dir)))

def _register(copied: list[dict[str, Any]], pkg: Path, src: Path, dest: Path, category: str) -> None:
    info = _copy_file(src, dest); info["relative_path"] = str(dest.relative_to(pkg)); info["category"] = category
    copied.append(info)

def export_rsfmri_report_package(derivatives_dir: str = "./derivatives", reports_dir: str = "./reports", work_dir: str = "./work", exports_dir: str = "./exports", export_id: str | None = None, include_subject_qc: bool = True, include_metrics: bool = True, include_fc: bool = True, include_contracts: bool = True, include_pipeline_runs: bool = True) -> dict[str, Any]:
    d = Path(derivatives_dir); rpt = Path(reports_dir); w = Path(work_dir); e = Path(exports_dir)
    eid = export_id or _now_id(); proot = e / "rsfmri_report_package"; pkg = proot / eid; zp = proot / f"{eid}.zip"
    pkg.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []; errors: list[str] = []; copied: list[dict[str, Any]] = []; excluded: list[dict[str, Any]] = []
    subs = _discover_subjects(d)

    # Group summary
    gb = rpt / "rsfmri" / "group_summary"; gfs = _safe_collect_files(gb, ["*.json","*.md","*.csv"])
    if not gfs: warnings.append("No group summary found. Run Step 47 first.")
    for s in gfs:
        dst = pkg / "summary" / "group_summary" / s.name; _register(copied, pkg, s, dst, "group_summary")
        if s.name == "subject_metrics_table.csv": _register(copied, pkg, s, pkg / "tables" / "subject_metrics_table.csv", "table")
    for s in _safe_collect_files(rpt / "rsfmri", ["*.json","*.md"]):
        if "group_summary" in s.parts: continue
        _register(copied, pkg, s, pkg / "summary" / "stage_reports" / s.name, "stage_report")

    # Subject QC & confounds
    if include_subject_qc:
        for sid in subs:
            for s in _safe_collect_files(d / "rsfmri_qc" / sid, ["*.json","*.md"]): _register(copied, pkg, s, pkg / "subjects" / sid / "qc" / s.name, "subject_qc")
            for s in _safe_collect_files(d / "rsfmri_confounds" / sid, ["*.json","*.tsv","*.csv","*.md"]): _register(copied, pkg, s, pkg / "subjects" / sid / "confounds" / s.name, "confounds")

    # Metrics
    if include_metrics:
        for sid in subs:
            md = d / "rsfmri_metrics" / sid
            for s in _safe_collect_files(md, ["*.json","*.md","*.tsv","*.csv"]): _register(copied, pkg, s, pkg / "metrics" / sid / s.name, "metrics")
            if md.exists():
                for s in sorted(md.glob("*")):
                    if s.is_file() and s.suffix in EXCLUDED_EXTENSIONS: excluded.append({"source_path": str(s), "reason": "Binary metric image excluded."})

    # FC
    if include_fc:
        for sid in subs:
            fd = d / "rsfmri_fc" / sid
            for s in _safe_collect_files(fd, ["*.json","*.tsv","*.csv","*.md"]): _register(copied, pkg, s, pkg / "fc" / sid / s.name, "functional_connectivity")
            if fd.exists():
                for s in sorted(fd.glob("*")):
                    if s.is_file() and s.suffix in EXCLUDED_EXTENSIONS: excluded.append({"source_path": str(s), "reason": "Binary FC image excluded."})

    # Contracts
    if include_contracts:
        dc = _safe_collect_files(w / "dpabi" / "contracts", ["*.json"]); gc = _safe_collect_files(w / "gpu" / "contracts", ["*.json"])
        if not dc and not gc: warnings.append("No DPABI/GPU contracts found.")
        for s in dc: _register(copied, pkg, s, pkg / "contracts" / "dpabi" / s.name, "dpabi_contract")
        for s in gc: _register(copied, pkg, s, pkg / "contracts" / "gpu" / s.name, "gpu_contract")

    # Pipeline runs
    if include_pipeline_runs:
        rps = sorted((w / "pipeline_runs").glob("*/summary.json")) if (w / "pipeline_runs").exists() else []
        if not rps: warnings.append("No pipeline run summaries found.")
        for s in rps[-50:]: _register(copied, pkg, s, pkg / "pipeline_runs" / f"{s.parent.name}_summary.json", "pipeline_run")

    # Checksums
    csd = pkg / "checksums"; csd.mkdir(parents=True, exist_ok=True); csp = csd / "SHA256SUMS.txt"
    cl = [f"{item['sha256']}  {item['relative_path']}" for item in copied]
    csp.write_text("\n".join(cl) + ("\n" if cl else ""), encoding="utf-8")
    copied.append({"relative_path": str(csp.relative_to(pkg)), "source_path": None, "size_bytes": int(csp.stat().st_size), "sha256": sha256_file(csp), "category": "checksum"})

    gs = read_json_artifact(pkg / "summary" / "group_summary" / "dataset_summary.json")
    es = {"ok": len(copied) > 1, "node_id": "rsfmri_report_exporter", "backend": "python", "export_id": eid, "package_dir": str(pkg), "zip_path": str(zp), "created_at": _iso_now(), "exported_subjects": subs, "exported_subjects_total": len(subs), "exported_files_total": len(copied), "excluded_files_total": len(excluded), "warnings": warnings, "errors": errors}
    if len(copied) <= 1: es["ok"] = False; warnings.append("No source files exported.")

    rp = pkg / "README.md"; ip = pkg / "index.md"; ep = pkg / "export_summary.json"; mp = pkg / "MANIFEST.json"
    _write_readme(rp, eid, es); _write_index(ip, eid, gs, es)
    for gp, cat in [(rp, "package_readme"), (ip, "package_index")]: copied.append({"relative_path": str(gp.relative_to(pkg)), "source_path": None, "size_bytes": int(gp.stat().st_size), "sha256": sha256_file(gp), "category": cat})
    es["exported_files_total"] = len(copied) + 2
    write_json_artifact(ep, es)
    copied.append({"relative_path": str(ep.relative_to(pkg)), "source_path": None, "size_bytes": int(ep.stat().st_size), "sha256": sha256_file(ep), "category": "export_summary"})

    manifest = {"package_id": eid, "export_id": eid, "created_at": es["created_at"], "source_roots": {"derivatives": str(d), "reports": str(rpt), "work": str(w)}, "safety": {"rawdata_included": False, "rawdata_modified": False, "derivatives_modified": False, "reports_modified": False, "work_modified": False, "spm_executed": False, "matlab_executed": False, "dpabi_executed": False, "gpu_executed": False, "files_deleted": False, "clinical_conclusions_generated": False, "statistical_inference_performed": False}, "files": copied, "excluded_files": excluded, "warnings": warnings, "errors": errors}
    write_json_artifact(mp, manifest)
    copied.append({"relative_path": str(mp.relative_to(pkg)), "source_path": None, "size_bytes": int(mp.stat().st_size), "sha256": sha256_file(mp), "category": "manifest"})
    manifest["files"] = copied; write_json_artifact(mp, manifest)
    cl2 = [f"{item['sha256']}  {item['relative_path']}" for item in copied if item["relative_path"] != "checksums/SHA256SUMS.txt"]
    csp.write_text("\n".join(cl2) + ("\n" if cl2 else ""), encoding="utf-8")
    _zip_directory(pkg, zp)

    es["zip_size_bytes"] = int(zp.stat().st_size) if zp.exists() else None
    es["outputs"] = [str(pkg), str(zp), str(mp), str(rp), str(ip), str(ep), str(csp)]
    write_json_artifact(ep, es)
    return es

def _read_export(pkg: Path) -> dict[str, Any]:
    s = read_json_artifact(pkg / "export_summary.json") or {}; m = read_json_artifact(pkg / "MANIFEST.json")
    ip = pkg / "index.md"; rp = pkg / "README.md"
    return {"ok": bool(s), "export_id": pkg.name, "package_dir": str(pkg), "zip_path": str(pkg.parent / f"{pkg.name}.zip"), "export_summary": s, "manifest": m, "index_md": ip.read_text(encoding="utf-8") if ip.exists() else None, "readme_md": rp.read_text(encoding="utf-8") if rp.exists() else None}

def list_rsfmri_report_exports(exports_dir: str = "./exports") -> dict[str, Any]:
    proot = Path(exports_dir) / "rsfmri_report_package"; packages = []
    if proot.exists():
        for c in sorted(proot.iterdir()):
            if c.is_dir():
                s = read_json_artifact(c / "export_summary.json") or {}
                packages.append({"export_id": c.name, "package_dir": str(c), "zip_path": str(proot / f"{c.name}.zip"), "created_at": s.get("created_at"), "ok": s.get("ok"), "exported_files_total": s.get("exported_files_total"), "exported_subjects_total": s.get("exported_subjects_total")})
    return {"ok": True, "exports_total": len(packages), "exports": packages}

def get_latest_rsfmri_report_export(exports_dir: str = "./exports") -> dict[str, Any]:
    proot = Path(exports_dir) / "rsfmri_report_package"
    if not proot.exists(): return {"ok": False, "errors": ["No exports found."], "warnings": []}
    pkgs = sorted([c for c in proot.iterdir() if c.is_dir()])
    if not pkgs: return {"ok": False, "errors": ["No exports found."], "warnings": []}
    return _read_export(pkgs[-1])
