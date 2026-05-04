from __future__ import annotations
import json; from pathlib import Path
from backend.app.tools.group_dataset_summary import build_group_dataset_summary

def test_group_dataset_summary_aggregates_subject_qc(tmp_path: Path):
    d = tmp_path / "derivatives"; rpt = tmp_path / "reports"; w = tmp_path / "work"
    sub = "sub-001"
    qd = d / "rsfmri_qc" / sub; md = d / "rsfmri_metrics" / sub; fcd = d / "rsfmri_fc" / sub; cd = d / "rsfmri_confounds" / sub
    qd.mkdir(parents=True); md.mkdir(parents=True); fcd.mkdir(parents=True); cd.mkdir(parents=True)
    (qd / "motion_qc.json").write_text(json.dumps({"ok":True,"subject_id":sub,"motion_qc_status":"PASS","mean_fd":0.1,"max_fd":0.2,"warnings":[],"errors":[]}), encoding="utf-8")
    (qd / "alff_falff_qc.json").write_text(json.dumps({"ok":True,"subject_id":sub,"alff_qc_status":"PASS","alff_mean":1.2,"falff_mean":0.4,"warnings":[],"errors":[]}), encoding="utf-8")
    (qd / "reho_qc.json").write_text(json.dumps({"ok":True,"subject_id":sub,"reho_qc_status":"PASS","reho_mean":0.8,"valid_voxel_count":27,"warnings":[],"errors":[]}), encoding="utf-8")
    (qd / "functional_connectivity_qc.json").write_text(json.dumps({"ok":True,"subject_id":sub,"fc_qc_status":"PASS","roi_count":4,"empty_roi_count":0,"diagonal_mean":1.0,"warnings":[],"errors":[]}), encoding="utf-8")
    (w / "gpu" / "contracts").mkdir(parents=True)
    (w / "gpu" / "contracts" / "t.json").write_text(json.dumps({"ok":True,"backend_id":"gpu_test","status":"CONTRACT_ONLY","execution_allowed":False,"gpu_executed":False}), encoding="utf-8")
    result = build_group_dataset_summary(derivatives_dir=str(d), reports_dir=str(rpt), work_dir=str(w))
    assert result["ok"] is True; assert result["subjects_total"] == 1
    assert result["metric_means"]["mean_fd"] == 0.1; assert result["metric_means"]["falff_mean"] == 0.4
    assert result["metric_means"]["reho_mean"] == 0.8; assert result["metric_means"]["fc_roi_count"] == 4.0
    gd = rpt / "rsfmri" / "group_summary"
    assert (gd / "dataset_summary.json").exists(); assert (gd / "dashboard_data.json").exists()
    assert (gd / "subject_metrics_table.csv").exists(); assert (gd / "dataset_summary_report.md").exists()
    db = json.loads((gd / "dashboard_data.json").read_text(encoding="utf-8")); assert db["summary_cards"]["subjects_total"] == 1
