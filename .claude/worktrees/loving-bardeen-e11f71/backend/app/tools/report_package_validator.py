from __future__ import annotations
import hashlib, json, zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

REQUIRED_FILES = ["MANIFEST.json","README.md","index.md","export_summary.json","checksums/SHA256SUMS.txt"]
FORBIDDEN_PARTS = {"rawdata"}
FORBIDDEN_SUFFIXES = {".nii",".mat"}
FORBIDDEN_COMPOUND = {".nii.gz"}
SAFETY_FALSE = ["rawdata_included","rawdata_modified","derivatives_modified","reports_modified","work_modified","spm_executed","matlab_executed","dpabi_executed","gpu_executed","files_deleted","clinical_conclusions_generated","statistical_inference_performed"]

def _iso_now() -> str: return datetime.now().isoformat(timespec="seconds")
def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists(): return None
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return None
def _write_json(path: Path, p: dict[str, Any]) -> None: path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1048576), b""): h.update(c)
    return h.hexdigest()
def _safe_path(v: str) -> bool: return bool(v) and not v.startswith("/") and all(p not in {"..",""} for p in Path(v).parts)
def _forbidden(v: str) -> bool:
    l = v.lower()
    if set(Path(l).parts) & FORBIDDEN_PARTS: return True
    if any(l.endswith(s) for s in FORBIDDEN_COMPOUND): return True
    if Path(l).suffix in FORBIDDEN_SUFFIXES: return True
    return False

def _load_checksums(path: Path) -> dict[str,str]:
    m: dict[str,str] = {}
    if not path.exists(): return m
    for line in path.read_text(encoding="utf-8",errors="replace").splitlines():
        line = line.strip()
        if not line: continue
        parts = line.split(None,1)
        if len(parts) == 2: m[parts[1].strip()] = parts[0].strip()
    return m

def _locate(exports_dir: str, export_id: str | None, package_dir: str | None, zip_path: str | None) -> tuple[Path|None,Path|None,str|None,list[str],list[str]]:
    w: list[str] = []; e: list[str] = []; root = Path(exports_dir)/"rsfmri_report_package"
    if package_dir: pkg = Path(package_dir); rid = pkg.name
    elif export_id: pkg = root/export_id; rid = export_id
    else:
        if not root.exists(): return None,None,None,w,["No report package root found."]
        pkgs = sorted([c for c in root.iterdir() if c.is_dir()])
        if not pkgs: return None,None,None,w,["No packages found."]
        pkg = pkgs[-1]; rid = pkg.name; w.append(f"Using latest: {rid}")
    zp = Path(zip_path) if zip_path else pkg.parent/f"{rid}.zip"
    return pkg, zp, rid, w, e

def validate_rsfmri_report_package(exports_dir: str = "./exports", export_id: str | None = None, package_dir: str | None = None, zip_path: str | None = None, strict: bool = False) -> dict[str, Any]:
    pkg, zp, rid, w, e = _locate(exports_dir, export_id, package_dir, zip_path)
    if not pkg or not rid: return {"ok": False, "node_id": "rsfmri_report_package_validator", "backend": "python", "validation_status": "FAIL", "exports_dir": exports_dir, "warnings": w, "errors": e}
    vd = pkg/"validation"; vd.mkdir(parents=True, exist_ok=True)
    vrj = vd/"validation_result.json"; vrm = vd/"validation_report.md"
    checks: list[dict[str,Any]] = []

    if not pkg.exists(): e.append(f"Package missing: {pkg}")

    # Required files
    rm = 0
    for rel in REQUIRED_FILES:
        path = pkg/rel; ex = path.exists(); ne = ex and path.is_file() and path.stat().st_size > 0
        st = "PASS" if ex and ne else "FAIL"
        if not ex: e.append(f"Missing: {rel}")
        elif not ne: e.append(f"Empty: {rel}")
        if st != "PASS": rm += 1
        checks.append({"name": f"required:{rel}", "status": st, "path": str(path), "exists": ex, "non_empty": ne})

    # Manifest
    manifest = _read_json(pkg/"MANIFEST.json")
    ms = {"manifest_files_total":0,"missing_files_total":0,"checksum_mismatch_total":0,"size_mismatch_total":0,"unsafe_path_total":0,"forbidden_file_total":0}
    if not manifest: e.append("MANIFEST.json unreadable.")
    else:
        files = manifest.get("files")
        if not isinstance(files, list): e.append("manifest.files not a list.")
        else:
            cm = _load_checksums(pkg/"checksums"/"SHA256SUMS.txt"); ms["manifest_files_total"] = len(files)
            for item in files:
                rel = item.get("relative_path"); esha = item.get("sha256"); esize = item.get("size_bytes")
                if not isinstance(rel,str) or not _safe_path(rel): ms["unsafe_path_total"] += 1; e.append(f"Unsafe path: {rel}"); continue
                if _forbidden(rel): ms["forbidden_file_total"] += 1; e.append(f"Forbidden file: {rel}")
                fp = pkg/rel
                if not fp.exists(): ms["missing_files_total"] += 1; e.append(f"Missing from package: {rel}"); continue
                asize = int(fp.stat().st_size); asha = _sha256(fp)
                so = esize is None or int(esize) == asize; sho = esha == asha
                cso = cm.get(rel); cfo = cso is None or cso == asha
                if not so: ms["size_mismatch_total"] += 1; e.append(f"Size mismatch: {rel}")
                if not sho or (cso is not None and not cfo): ms["checksum_mismatch_total"] += 1; e.append(f"Checksum mismatch: {rel}")
                checks.append({"name": "file_integrity", "relative_path": rel, "status": "PASS" if so and sho and cfo and not _forbidden(rel) else "FAIL", "size_ok": so, "sha256_ok": sho, "checksum_file_ok": cfo, "actual_size": asize, "actual_sha256": asha})

    # ZIP
    zs = {"zip_exists": False, "zip_test_ok": False, "zip_entries_total": 0, "zip_unsafe_path_total": 0, "zip_forbidden_file_total": 0, "zip_missing_required_total": 0, "zip_missing_manifest_total": 0}
    if not zp.exists(): e.append(f"ZIP missing: {zp}")
    else:
        zs["zip_exists"] = True
        try:
            with zipfile.ZipFile(zp,"r") as zf:
                bad = zf.testzip(); zs["zip_test_ok"] = bad is None
                if bad: e.append(f"ZIP test failed: {bad}")
                names = zf.namelist(); zs["zip_entries_total"] = len(names); nameset = set(names)
                for n in names:
                    if not _safe_path(n): zs["zip_unsafe_path_total"] += 1; e.append(f"Unsafe ZIP path: {n}")
                    if _forbidden(n): zs["zip_forbidden_file_total"] += 1; e.append(f"Forbidden in ZIP: {n}")
                for r in REQUIRED_FILES:
                    if r not in nameset: zs["zip_missing_required_total"] += 1; e.append(f"Missing from ZIP: {r}")
                if manifest and isinstance(manifest.get("files"), list):
                    for item in manifest["files"]:
                        rel = item.get("relative_path")
                        if isinstance(rel,str) and rel not in nameset and not rel.startswith("validation/"): zs["zip_missing_manifest_total"] += 1; e.append(f"Manifest file missing from ZIP: {rel}")
        except Exception as exc: e.append(f"ZIP error: {exc}")
    checks.append({"name": "zip_integrity", "status": "PASS" if zs["zip_test_ok"] and zs["zip_unsafe_path_total"] == 0 and zs["zip_forbidden_file_total"] == 0 else "FAIL"})

    # Safety
    ss = {"safety_flags_checked": 0, "safety_violations_total": 0}
    if not manifest: e.append("Cannot audit safety.")
    else:
        safety = manifest.get("safety")
        if not isinstance(safety, dict): e.append("manifest.safety not a dict.")
        else:
            for flag in SAFETY_FALSE:
                ss["safety_flags_checked"] += 1; v = safety.get(flag); ok = v is False
                if not ok: ss["safety_violations_total"] += 1; e.append(f"Safety violation: {flag}={v}")
                checks.append({"name": f"safety:{flag}", "status": "PASS" if ok else "FAIL", "value": v, "expected": False})

    stats = {"required_files_missing_total": rm, **ms, **zs, **ss, "checks_total": len(checks), "warnings_total": len(w), "errors_total": len(e)}
    status = "FAIL" if e else ("WARNING" if w else "PASS")
    ok = status == "PASS" or (status == "WARNING" and not strict)

    result = {"ok": ok, "node_id": "rsfmri_report_package_validator", "backend": "python", "export_id": rid, "validated_at": _iso_now(), "validation_status": status, "strict": strict, "package_dir": str(pkg), "zip_path": str(zp), "validation_result_json": str(vrj), "validation_report_md": str(vrm), "stats": stats, "checks": checks, "warnings": w, "errors": e, "outputs": [str(vrj), str(vrm), str(Path(exports_dir)/"rsfmri_report_package"/"VALIDATION_INDEX.json")]}

    _write_json(vrj, result)

    # Report
    lines = [f"# rs-fMRI Report Package Validation", "", f"- Export: `{rid}`", f"- Status: **{status}**", f"- OK: {ok}", f"- Package: `{pkg}`", f"- ZIP: `{zp}`", "", "## Summary", ""]
    for k in ["required_files_missing_total","manifest_files_total","missing_files_total","checksum_mismatch_total","zip_entries_total","zip_test_ok","safety_violations_total"]: lines.append(f"- {k}: {stats.get(k)}")
    lines += ["", "## Warnings"]
    if w: lines += [f"- {x}" for x in w]
    else: lines.append("- None")
    lines += ["", "## Errors"]
    if e: lines += [f"- {x}" for x in e]
    else: lines.append("- None")
    lines += ["", "## Safety", "", "Read-only validator. Does not repair, regenerate, or clinically interpret the package."]
    vrm.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Index
    root = Path(exports_dir)/"rsfmri_report_package"
    idx = root/"VALIDATION_INDEX.json"
    cur = _read_json(idx) or {"ok":True,"validations":[]}
    vals = cur.get("validations",[])
    if not isinstance(vals, list): vals = []
    entry = {"export_id": rid, "validated_at": result["validated_at"], "validation_status": status, "ok": ok, "package_dir": str(pkg), "zip_path": str(zp), "validation_result": str(vrj), "validation_report": str(vrm)}
    vals = [x for x in vals if x.get("export_id") != rid]; vals.append(entry)
    _write_json(idx, {"ok":True,"updated_at":_iso_now(),"validations_total":len(vals),"validations":vals})
    return result

def list_rsfmri_report_validations(exports_dir: str = "./exports") -> dict[str, Any]:
    root = Path(exports_dir)/"rsfmri_report_package"
    idx = root/"VALIDATION_INDEX.json"
    cur = _read_json(idx); vals = []
    if cur and isinstance(cur.get("validations"), list): vals = cur["validations"]
    elif root.exists():
        for pkg in sorted(root.iterdir()):
            if not pkg.is_dir(): continue
            vp = pkg/"validation"/"validation_result.json"; pl = _read_json(vp)
            if pl: vals.append({"export_id": pkg.name, "validated_at": pl.get("validated_at"), "validation_status": pl.get("validation_status"), "ok": pl.get("ok"), "package_dir": str(pkg), "zip_path": pl.get("zip_path"), "validation_result": str(vp), "validation_report": str(pkg/"validation"/"validation_report.md")})
    return {"ok": True, "validations_total": len(vals), "validations": vals}

def get_latest_rsfmri_report_validation(exports_dir: str = "./exports") -> dict[str, Any]:
    listing = list_rsfmri_report_validations(exports_dir=exports_dir); vv = listing.get("validations",[])
    if not vv: return {"ok": False, "warnings": [], "errors": ["No validations found."]}
    latest = vv[-1]; rp = latest.get("validation_result"); rr = latest.get("validation_report")
    res = _read_json(Path(rp)) if rp else None
    rep = Path(rr).read_text(encoding="utf-8") if rr and Path(rr).exists() else None
    return {"ok": bool(res), "latest": latest, "validation_result": res, "validation_report": rep}
