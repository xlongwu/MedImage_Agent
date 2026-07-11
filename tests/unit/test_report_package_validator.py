from __future__ import annotations
import json, hashlib, zipfile; from pathlib import Path
from src.backend.app.tools.report_package_validator import validate_rsfmri_report_package, get_latest_rsfmri_report_validation, list_rsfmri_report_validations
def _sh(p: Path) -> str:
    h = hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()
def _win_rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix().replace("/", "\\")
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

def test_validator_normalizes_manifest_windows_paths_against_zip_paths(tmp_path: Path):
    e = tmp_path/"exports"; root = e/"rsfmri_report_package"; pkg = root/"test_export"; pkg.mkdir(parents=True)
    safety = {"rawdata_included":False,"rawdata_modified":False,"derivatives_modified":False,"reports_modified":False,"work_modified":False,"spm_executed":False,"matlab_executed":False,"dpabi_executed":False,"gpu_executed":False,"files_deleted":False,"clinical_conclusions_generated":False,"statistical_inference_performed":False}
    paths = [
        pkg/"README.md",
        pkg/"index.md",
        pkg/"export_summary.json",
        pkg/"summary"/"group_summary"/"dataset_summary.json",
    ]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n" if path.suffix == ".json" else "# text\n", encoding="utf-8")

    files = [
        {
            "relative_path": _win_rel(path, pkg),
            "source_path": None,
            "size_bytes": path.stat().st_size,
            "sha256": _sh(path),
            "category": "test",
        }
        for path in paths
    ]
    mp = pkg/"MANIFEST.json"
    mp.write_text(json.dumps({"package_id":"test_export","created_at":"2026-01-01","source_roots":{},"safety":safety,"files":files,"excluded_files":[],"warnings":[],"errors":[]}), encoding="utf-8")
    csp = pkg/"checksums"/"SHA256SUMS.txt"; csp.parent.mkdir(parents=True)
    csp.write_text("\n".join(f"{_sh(path)}  {_win_rel(path, pkg)}" for path in paths + [mp]) + "\n", encoding="utf-8")
    zp = root/"test_export.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in list(paths) + [mp, csp]:
            zf.write(path, arcname=path.relative_to(pkg).as_posix())

    result = validate_rsfmri_report_package(exports_dir=str(e), export_id="test_export")

    assert result["ok"] is True
    assert result["stats"]["zip_missing_manifest_total"] == 0
    assert result["stats"]["missing_files_total"] == 0

def test_validator_latest_skips_incomplete_stale_exports(tmp_path: Path):
    e = tmp_path/"exports"; root = e/"rsfmri_report_package"; root.mkdir(parents=True)
    stale = root/"rsfmri_export_20990101_000000"; stale.mkdir()
    valid = root/"rsfmri_export_20260706_220533"; valid.mkdir()
    rm = valid/"README.md"; ix = valid/"index.md"; es = valid/"export_summary.json"
    rm.write_text("# README\n", encoding="utf-8"); ix.write_text("# Index\n", encoding="utf-8"); es.write_text(json.dumps({"ok":True}), encoding="utf-8")
    safety = {"rawdata_included":False,"rawdata_modified":False,"derivatives_modified":False,"reports_modified":False,"work_modified":False,"spm_executed":False,"matlab_executed":False,"dpabi_executed":False,"gpu_executed":False,"files_deleted":False,"clinical_conclusions_generated":False,"statistical_inference_performed":False}
    content_files = [rm, ix, es]
    files = [{"relative_path": f.relative_to(valid).as_posix(), "source_path": None, "size_bytes": f.stat().st_size, "sha256": _sh(f), "category": "test"} for f in content_files]
    mp = valid/"MANIFEST.json"
    mp.write_text(json.dumps({"package_id":valid.name,"created_at":"2026-01-01","source_roots":{},"safety":safety,"files":files,"excluded_files":[],"warnings":[],"errors":[]}), encoding="utf-8")
    csp = valid/"checksums"/"SHA256SUMS.txt"; csp.parent.mkdir(parents=True)
    csp.write_text("\n".join(f"{_sh(f)}  {f.relative_to(valid).as_posix()}" for f in content_files + [mp]) + "\n", encoding="utf-8")
    zp = root/f"{valid.name}.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in content_files + [mp, csp]:
            zf.write(f, arcname=f.relative_to(valid).as_posix())

    result = validate_rsfmri_report_package(exports_dir=str(e))

    assert result["ok"] is True
    assert result["export_id"] == valid.name
    assert any("Skipped 1 incomplete" in warning for warning in result["warnings"])
