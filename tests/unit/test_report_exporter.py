from __future__ import annotations
import json, zipfile; from pathlib import Path
from src.backend.app.tools.report_exporter import export_rsfmri_report_package, get_latest_rsfmri_report_export, list_rsfmri_report_exports

def test_report_exporter_creates_manifest_and_zip(tmp_path: Path):
    d = tmp_path/"derivatives"; rpt = tmp_path/"reports"; w = tmp_path/"work"; e = tmp_path/"exports"
    sub = "sub-001"
    gd = rpt/"rsfmri"/"group_summary"; gd.mkdir(parents=True)
    (gd/"dataset_summary.json").write_text(json.dumps({"ok":True,"subjects_total":1,"subjects_with_any_qc":1,"warnings_total":0,"errors_total":0,"stage_status_counts":{"motion":{"PASS":1,"WARNING":0,"FAIL":0,"MISSING":0}}}), encoding="utf-8")
    (gd/"dataset_summary_report.md").write_text("# Summary\n", encoding="utf-8")
    (gd/"subject_metrics_table.csv").write_text("subject_id,motion_status\nsub-001,PASS\n", encoding="utf-8")
    qd = d/"rsfmri_qc"/sub; qd.mkdir(parents=True)
    (qd/"motion_qc.json").write_text(json.dumps({"ok":True,"subject_id":sub,"motion_qc_status":"PASS"}), encoding="utf-8")
    md = d/"rsfmri_metrics"/sub; md.mkdir(parents=True)
    (md/"alff_falff_result.json").write_text(json.dumps({"ok":True,"subject_id":sub}), encoding="utf-8")
    cd = w/"gpu"/"contracts"; cd.mkdir(parents=True)
    (cd/"gpu_contract.json").write_text(json.dumps({"ok":True,"backend_id":"gpu_test","status":"CONTRACT_ONLY","execution_allowed":False}), encoding="utf-8")
    result = export_rsfmri_report_package(derivatives_dir=str(d), reports_dir=str(rpt), work_dir=str(w), exports_dir=str(e), export_id="test_export")
    assert result["ok"] is True
    pkg = e/"rsfmri_report_package"/"test_export"; zp = e/"rsfmri_report_package"/"test_export.zip"
    assert (pkg/"MANIFEST.json").exists(); assert (pkg/"README.md").exists()
    assert (pkg/"index.md").exists(); assert (pkg/"checksums"/"SHA256SUMS.txt").exists(); assert zp.exists()
    with zipfile.ZipFile(zp) as zf: assert "MANIFEST.json" in zf.namelist()
    latest = get_latest_rsfmri_report_export(exports_dir=str(e)); assert latest["ok"] is True; assert latest["export_id"] == "test_export"
    listing = list_rsfmri_report_exports(exports_dir=str(e)); assert listing["ok"] is True; assert listing["exports_total"] == 1
