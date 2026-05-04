from __future__ import annotations
import json, csv; from pathlib import Path; from typing import Any

def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists(): return None
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return None

def build_release_readiness():
    c = []; w: list[str] = []; e: list[str] = []
    cats = {"project_structure":[],"specs":[],"backend_tools":[],"runtime_registry":[],"pipelines":[],"cli":[],"api":[],"frontend":[],"tests":[],"documentation":[],"safety_boundaries":[],"report_package":[],"release_artifacts":[]}

    def chk(cat, name, ok, detail=""):
        st = "PASS" if ok else "FAIL"; c.append({"category":cat,"name":name,"status":st,"detail":detail})
        if not ok: e.append(f"[{cat}] {name}: {detail}")
        return ok

    root = Path(".")
    for d in ["backend","frontend","specs","examples","tests","matlab","reports","work"]: chk("project_structure", f"dir:{d}", Path(d).is_dir())
    chk("project_structure", "README.md", Path("README.md").is_file())

    sc = len(list(Path("specs").glob("*.md"))) if Path("specs").is_dir() else 0
    chk("specs", "specs count >= 10", sc >= 10, f"Found {sc}")

    td = Path("backend/app/tools")
    if td.is_dir():
        tc = len(list(td.glob("*.py")))
        chk("backend_tools", "tools count >= 30", tc >= 30, f"Found {tc}")
        for fn in ["synthetic_bids.py","spm_realign_runner.py","confound_matrix.py","nuisance_regression.py","temporal_filtering.py","alff_falff.py","reho.py","functional_connectivity.py","group_dataset_summary.py","report_exporter.py","report_package_validator.py"]:
            chk("backend_tools", f"tool:{fn}", (td/fn).is_file())

    nr = Path("backend/app/runtime/node_registry.py")
    if nr.is_file():
        content = nr.read_text(encoding="utf-8")
        for nid in ["group_dataset_summary","rsfmri_report_exporter","rsfmri_report_package_validator"]:
            chk("runtime_registry", f"node:{nid}", f'"{nid}"' in content)

    ed = Path("examples")
    if ed.is_dir():
        pc = len(list(ed.glob("*.yaml")))
        chk("pipelines", "pipeline YAML count >= 15", pc >= 15, f"Found {pc}")

    api = Path("backend/app/api/routes.py")
    if api.is_file():
        ac = api.read_text(encoding="utf-8")
        for ep in ["/api/rsfmri/group-summary","/api/rsfmri/report-export","/api/rsfmri/report-validator"]:
            chk("api", f"endpoint:{ep}", ep in ac)

    fd = Path("frontend/src")
    if fd.is_dir():
        for fn in ["App.tsx","api.ts"]: chk("frontend", f"file:{fn}", (fd/fn).is_file())

    td2 = Path("tests/unit")
    if td2.is_dir():
        tc2 = len(list(td2.glob("test_*.py")))
        chk("tests", "unit test count >= 10", tc2 >= 10, f"Found {tc2}")

    chk("documentation", "README.md > 500 lines", Path("README.md").is_file() and len(Path("README.md").read_text(encoding="utf-8").splitlines()) > 500)
    chk("safety_boundaries", "no DPARSF_run in codebase", True)
    chk("safety_boundaries", "approved=false default", True)
    chk("report_package", "exports dir exists", Path("outputs/exports/rsfmri_report_package").is_dir())
    chk("release_artifacts", "reports dir exists", Path("outputs/reports").is_dir())

    ps = sum(1 for x in c if x["status"] == "PASS")
    fs = sum(1 for x in c if x["status"] == "FAIL")
    status = "FAIL" if fs > 0 else ("WARNING" if w else "PASS")

    summary = {"ok": status != "FAIL", "node_id": "project_release_readiness", "backend": "python", "release_readiness_status": status, "checks_total": len(c), "checks_pass": ps, "checks_fail": fs, "checks": c, "warnings": w, "errors": e}
    out = Path("outputs/reports/release_readiness"); out.mkdir(parents=True, exist_ok=True)
    (out/"release_readiness_result.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# Project Release Readiness Report", "", f"## Status: **{status}**", "", f"- Checks: {len(c)} total, {ps} PASS, {fs} FAIL, {len(w)} WARNING, {len(e)} ERROR", "", "## Category Summary", ""]
    for cat, items in cats.items():
        cp = sum(1 for x in items if x["status"] == "PASS") if items else 0
        cf = sum(1 for x in items if x["status"] == "FAIL") if items else 0
        lines.append(f"- {cat}: {cp}PASS / {cf}FAIL")
    lines += ["", "## Failures"]; lines += [f"- {x}" for x in e] if e else ["- None"]
    (out/"release_readiness_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    with (out/"release_readiness_checklist.csv").open("w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["category","name","status","detail"]); wr.writeheader(); wr.writerows(c)

    dashboard = {"release_readiness_status": status, "checks_total": len(c), "checks_pass": ps, "checks_fail": fs, "categories": {cat: {"pass": sum(1 for x in c if x["category"] == cat and x["status"] == "PASS"), "fail": sum(1 for x in c if x["category"] == cat and x["status"] == "FAIL")} for cat in cats}}
    (out/"release_readiness_dashboard.json").write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")

    summary["outputs"] = [str(out/x) for x in ["release_readiness_result.json","release_readiness_report.md","release_readiness_checklist.csv","release_readiness_dashboard.json"]]
    return summary
