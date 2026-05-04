from __future__ import annotations
import json, hashlib, zipfile; from pathlib import Path
from backend.app.tools.report_package_validator import validate_rsfmri_report_package, get_latest_rsfmri_report_validation, list_rsfmri_report_validations
def _sh(p: Path) -> str:
    h = hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()
def test_validator_passes_valid_package(tmp_path: Path):
    e = tmp_path/"exports"; root = e/"rsfmri_report_package"; pkg = root/"test_export"; pkg.mkdir(parents=True)
    rm = pkg/"README.md"; ix = pkg/"index.md"; es = pkg/"export_summary.json"
    rm.write_text("# README\n", encoding="utf-8"); ix.write_text("# Index\n", encoding="utf-8"); es.write_text(json.dumps({"ok":True}), encoding="utf-8")
    mp = pkg/"MANIFEST.json"
    manifest = {"package_id":"test_export","created_at":"2026-01-01","source_roots":{},"safety":{"rawdata_included":False,"rawdata_modified":False,"derivatives_modified":False,"reports_modified":False,"work_modified":False,"spm_executed":False,"matlab_executed":False,"dpabi_executed":False,"gpu_executed":False,"files_deleted":False,"clinical_conclusions_generated":False,"statistical_inference_performed":False},"files":[],"excluded_files":[],"warnings":[],"errors":[]}
    mp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    files = []
    for f in [rm, ix, es, mp]: files.append({"relative_path": str(f.relative_to(pkg)), "source_path": None, "size_bytes": f.stat().st_size, "sha256": _sh(f), "category": "test"})
    csd = pkg/"checksums"; csd.mkdir(parents=True); csp = csd/"SHA256SUMS.txt"
    csp.write_text("\n".join(f"{x['sha256']}  {x['relative_path']}" for x in files) + "\n", encoding="utf-8")
    files.append({"relative_path": "checksums/SHA256SUMS.txt", "source_path": None, "size_bytes": csp.stat().st_size, "sha256": _sh(csp), "category": "checksum"})
    manifest["files"] = files; mp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    zp = root/"test_export.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in pkg.rglob("*"):
            if f.is_file(): zf.write(f, arcname=str(f.relative_to(pkg)))
    result = validate_rsfmri_report_package(exports_dir=str(e), export_id="test_export")
    assert result["ok"] is True; assert result["validation_status"] in {"PASS","WARNING"}
    assert (pkg/"validation"/"validation_result.json").exists()
    assert get_latest_rsfmri_report_validation(exports_dir=str(e))["ok"] is True
    assert list_rsfmri_report_validations(exports_dir=str(e))["validations_total"] == 1
