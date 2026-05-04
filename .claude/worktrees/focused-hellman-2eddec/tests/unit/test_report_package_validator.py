from __future__ import annotations
import json, hashlib, zipfile; from pathlib import Path
from backend.app.tools.report_package_validator import validate_rsfmri_report_package, get_latest_rsfmri_report_validation, list_rsfmri_report_validations
def _sh(p: Path) -> str:
    h = hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()
def test_validator_passes_valid_package(tmp_path: Path):
    e = tmp_path/"exports"; root = e/"rsfmri_report_package"; pkg = root/"test_export"; pkg.mkdir(parents=True)
    rm = pkg/"README.md"; ix = pkg/"index.md"; es = pkg/"export_summary.json"
    rm.write_text("# README\n", encoding="utf-8"); ix.write_text("# Index\n", encoding="utf-8"); es.write_text(json.dumps({"ok":True}), encoding="utf-8")
    safety = {"rawdata_included":False,"rawdata_modified":False,"derivatives_modified":False,"reports_modified":False,"work_modified":False,"spm_executed":False,"matlab_executed":False,"dpabi_executed":False,"gpu_executed":False,"files_deleted":False,"clinical_conclusions_generated":False,"statistical_inference_performed":False}
    # Build content files; MANIFEST.json writes once at the end
    content_files = [rm, ix, es]
    # Write MANIFEST.json with complete content (written once, so hash is stable)
    files = [{"relative_path": str(f.relative_to(pkg)), "source_path": None, "size_bytes": f.stat().st_size, "sha256": _sh(f), "category": "test"} for f in content_files]
    mp = pkg/"MANIFEST.json"
    manifest = {"package_id":"test_export","created_at":"2026-01-01","source_roots":{},"safety":safety,"files":files,"excluded_files":[],"warnings":[],"errors":[]}
    mp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    # Now write SHA256SUMS.txt as the LAST content file, including MANIFEST.json's hash
    all_content = content_files + [mp]
    csd = pkg/"checksums"; csd.mkdir(parents=True); csp = csd/"SHA256SUMS.txt"
    checksums_lines = [f"{_sh(f)}  {str(f.relative_to(pkg))}" for f in all_content]
    # SHA256SUMS.txt does NOT include itself (no self-reference)
    csp.write_text("\n".join(checksums_lines) + "\n", encoding="utf-8")
    # ZIP the package
    zp = root/"test_export.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in pkg.rglob("*"):
            if f.is_file(): zf.write(f, arcname=str(f.relative_to(pkg)))
    result = validate_rsfmri_report_package(exports_dir=str(e), export_id="test_export")
    assert result["ok"] is True; assert result["validation_status"] in {"PASS","WARNING"}
    assert (pkg/"validation"/"validation_result.json").exists()
    assert get_latest_rsfmri_report_validation(exports_dir=str(e))["ok"] is True
    assert list_rsfmri_report_validations(exports_dir=str(e))["validations_total"] == 1
