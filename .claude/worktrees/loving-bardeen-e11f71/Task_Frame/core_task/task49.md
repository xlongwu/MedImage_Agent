# 第四十九步 Prompt：Report Package Validator + Integrity / Safety Audit 闭环

```text
你是我的工程搭建助手。前四十八步已经完成：

- MedImage Agent 工程骨架
- Pipeline runtime
- Agent runtime
- MATLAB / SPM / DPABI 环境检查
- synthetic BIDS 数据生成与扫描
- rs-fMRI preprocessing protocol
- rs-fMRI step registry
- SPM Slice Timing Correction + Metadata QC
- SPM Realignment + Motion QC
- Slice Timing → Realignment → Motion QC 链式核心 pipeline
- SPM Coregistration + Registration QC
- SPM Segmentation + Tissue QC
- SPM Normalization + Normalization QC
- SPM Smoothing + Smoothing QC
- Nuisance Regression 参数计划 + Confound Matrix + Python/DPABI 双后端设计
- Temporal Filtering + Filtering QC
- ALFF / fALFF 计算 + QC + GPU Candidate Backend 设计
- ReHo 计算 + ReHo QC + GPU/DPABI Backend Contract
- Functional Connectivity ROI/Seed 相关分析 + FC QC + GPU/DPABI Backend Contract
- Group-level Dataset Summary + Cross-subject Metrics Dashboard
- Dataset Report Exporter + 可交付报告包

现在开始第四十九步。

第四十九步目标：实现 “Report Package Validator + Integrity / Safety Audit 闭环”。

当前系统已经可以把已有 synthetic rs-fMRI 工程结果导出为：

```text
exports/rsfmri_report_package/{export_id}/
exports/rsfmri_report_package/{export_id}.zip
```

并包含：

- MANIFEST.json
- README.md
- index.md
- export_summary.json
- checksums/SHA256SUMS.txt
- summary/
- subjects/
- metrics/
- fc/
- contracts/
- pipeline_runs/
- tables/

但还缺少一个独立 validator，用来校验这个报告包是否完整、可审查、可归档、没有被篡改，并且符合安全声明。

本步骤要实现：

1. Report Package Validator specification。
2. 一个只读 validator：
   - 读取 export package directory。
   - 读取 export package zip。
   - 读取 MANIFEST.json。
   - 读取 SHA256SUMS.txt。
   - 重新计算所有导出文件的 SHA256。
   - 校验 manifest 记录和实际文件一致。
   - 校验 zip 完整性。
   - 校验 zip 内容和 package directory 内容一致。
   - 校验安全声明 flags。
   - 校验不包含 rawdata。
   - 校验不包含 NIfTI / MAT 等大二进制数据。
   - 校验 README / index / export_summary 是否存在。
   - 校验 source roots 不被复制进 package。
3. 生成 validation 输出：
   - `exports/rsfmri_report_package/{export_id}/validation/validation_result.json`
   - `exports/rsfmri_report_package/{export_id}/validation/validation_report.md`
4. 可选生成全局 validation index：
   - `exports/rsfmri_report_package/VALIDATION_INDEX.json`
5. 后端 API：
   - `POST /api/rsfmri/report-validator/run`
   - `GET /api/rsfmri/report-validator/latest`
   - `GET /api/rsfmri/report-validator/list`
6. 前端新增面板：
   - rs-fMRI Report Package Validator
   - 可以验证最新报告包
   - 可以加载最新 validation
   - 可以列出所有 validation
   - 显示 validation status
   - 显示 checksum mismatch 数量
   - 显示 missing file 数量
   - 显示 zip validation 状态
   - 显示 safety audit 状态
   - 显示 validation report
7. 新增 pipeline：
   - 只运行 validator，不执行 SPM / MATLAB / DPABI / GPU。
8. 增加轻量 unit test。
9. 更新 README。

本步骤必须满足：

- 只读取 exports 中已有 report package。
- 只写入 exports/rsfmri_report_package/{export_id}/validation。
- 不处理真实医学影像数据。
- 不修改 rawdata。
- 不修改 derivatives / reports / work。
- 不运行 SPM。
- 不运行 MATLAB。
- 不调用 DPABI。
- 不调用 DPARSF_run。
- 不调用 DPARSFA_run。
- 不调用 DPABI GUI。
- 不执行 GPU。
- 不删除文件。
- 不做医学结论。
- 不做 clinical interpretation。
- 不做 group-level statistics / inference。
- 不自动修复报告包，只报告问题。

本步骤不要实现：

- 自动修复 corrupted package
- 重新导出 package
- PDF 生成
- Word 文档生成
- PowerPoint 生成
- group-level statistical testing
- clinical interpretation
- real medical data handling
- Docker / release / CI 等外围功能

本步骤只做：对 Step 48 导出的报告包进行完整性校验、checksum 校验、zip 校验、安全声明审计，并输出 validation report。

---

## 1. 创建 specs/report_package_validator_spec.md

创建文件：

```text
specs/report_package_validator_spec.md
```

内容：

```markdown
# Report Package Validator Specification

This document defines the MVP validator for exported rs-fMRI report packages.

## Goals

The goal is to verify that a report package exported by the Dataset Report Exporter is complete, internally consistent, checksum-valid, zip-valid, and aligned with declared safety constraints.

The validator is read-only with respect to source project outputs and writes only validation artifacts under the selected export package.

## Scope

Supported in this step:

- validate one exported report package
- validate latest report package
- validate package directory
- validate zip archive
- validate MANIFEST.json
- validate SHA256 checksums
- validate required files
- validate safety flags
- validate excluded file rules
- generate validation JSON
- generate validation Markdown
- backend API visibility
- frontend validator panel
- lightweight unit tests

Unsupported in this step:

- automatic repair
- re-export
- real medical image preprocessing
- PDF generation
- Word generation
- PowerPoint generation
- clinical interpretation
- group-level statistical inference
- DPABI execution
- SPM execution
- MATLAB execution
- GPU execution
- rawdata modification
- file deletion

## Inputs

```text
exports/rsfmri_report_package/{export_id}/MANIFEST.json
exports/rsfmri_report_package/{export_id}/export_summary.json
exports/rsfmri_report_package/{export_id}/README.md
exports/rsfmri_report_package/{export_id}/index.md
exports/rsfmri_report_package/{export_id}/checksums/SHA256SUMS.txt
exports/rsfmri_report_package/{export_id}.zip
```

## Outputs

```text
exports/rsfmri_report_package/{export_id}/validation/validation_result.json
exports/rsfmri_report_package/{export_id}/validation/validation_report.md
exports/rsfmri_report_package/VALIDATION_INDEX.json
```

## Validation Checks

The validator checks:

- required files exist
- manifest is readable JSON
- export_summary is readable JSON
- checksum file exists
- all manifest file entries are inside the package
- no manifest path escapes the package directory
- all manifest files exist
- file sizes match manifest
- SHA256 checksums match manifest
- checksum file agrees with manifest
- zip file exists
- zip file opens successfully
- zip archive passes `testzip`
- zip entries do not use unsafe paths
- zip contains required files
- zip contains expected exported files
- package does not include rawdata
- package does not include `.nii`, `.nii.gz`, `.mat`
- safety flags are false for execution/modification claims
- README and index are present and non-empty

## Status

Validation status:

- PASS: all required checks passed
- WARNING: non-critical issue found
- FAIL: missing manifest, checksum mismatch, unsafe path, zip corruption, or safety violation

## Safety Rules

- Read only from exports.
- Write only validation outputs under exports.
- Do not modify source derivatives/reports/work.
- Do not modify rawdata.
- Do not delete files.
- Do not run SPM.
- Do not run MATLAB.
- Do not execute DPABI.
- Do not execute GPU.
- Do not perform statistical inference.
- Do not generate clinical conclusions.
- Do not repair packages automatically.
```

---

## 2. 创建 backend/app/tools/report_package_validator.py

创建文件：

```text
backend/app/tools/report_package_validator.py
```

目标：实现 report package validator。

提供函数：

```python
validate_rsfmri_report_package(
    exports_dir: str = "./exports",
    export_id: str | None = None,
    package_dir: str | None = None,
    zip_path: str | None = None,
    strict: bool = False,
) -> dict

get_latest_rsfmri_report_validation(
    exports_dir: str = "./exports",
) -> dict

list_rsfmri_report_validations(
    exports_dir: str = "./exports",
) -> dict
```

实现要求：

1. 如果 package_dir 未提供：
   - 使用 export_id 定位：
     `exports/rsfmri_report_package/{export_id}`
   - 如果 export_id 也未提供：
     使用最新 export package directory。
2. zip_path 默认：
   - `exports/rsfmri_report_package/{export_id}.zip`
3. 验证 required files：
   - MANIFEST.json
   - README.md
   - index.md
   - export_summary.json
   - checksums/SHA256SUMS.txt
4. 读取 MANIFEST.json：
   - 必须有 safety。
   - 必须有 files。
   - files 中每个 relative_path 必须安全。
5. 校验 checksum：
   - 对 manifest files 重新计算 sha256。
   - 对 size_bytes 比对。
   - 对 SHA256SUMS.txt 交叉比对。
6. 校验 zip：
   - zip 存在。
   - 可打开。
   - `ZipFile.testzip()` 返回 None。
   - zip 内 path 安全。
   - zip 内包含 MANIFEST.json / README.md / index.md / export_summary.json。
   - zip 内不包含 rawdata。
   - zip 内不包含 `.nii`, `.nii.gz`, `.mat`。
7. 安全审计：
   - rawdata_included 必须 false。
   - rawdata_modified 必须 false。
   - derivatives_modified 必须 false。
   - reports_modified 必须 false。
   - work_modified 必须 false。
   - spm_executed 必须 false。
   - matlab_executed 必须 false。
   - dpabi_executed 必须 false。
   - gpu_executed 必须 false。
   - files_deleted 必须 false。
   - clinical_conclusions_generated 必须 false。
   - statistical_inference_performed 必须 false。
8. 若 strict=true：
   - warning 也导致 overall ok=false。
9. 输出 validation_result.json 和 validation_report.md。
10. 更新 VALIDATION_INDEX.json。
11. 不修改 package 中其他文件。
12. 不删除文件。
13. 只使用 Python 标准库。

参考实现：

```python
from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any


REQUIRED_FILES = [
    "MANIFEST.json",
    "README.md",
    "index.md",
    "export_summary.json",
    "checksums/SHA256SUMS.txt",
]

FORBIDDEN_PARTS = {
    "rawdata",
}

FORBIDDEN_SUFFIXES = {
    ".nii",
    ".mat",
}

FORBIDDEN_SUFFIX_COMPOUNDS = {
    ".nii.gz",
}

SAFETY_FALSE_FLAGS = [
    "rawdata_included",
    "rawdata_modified",
    "derivatives_modified",
    "reports_modified",
    "work_modified",
    "spm_executed",
    "matlab_executed",
    "dpabi_executed",
    "gpu_executed",
    "files_deleted",
    "clinical_conclusions_generated",
    "statistical_inference_performed",
]


def _iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _is_safe_relative_path(value: str) -> bool:
    if not value or value.startswith("/"):
        return False

    path = Path(value)
    if any(part in {"..", ""} for part in path.parts):
        return False

    return True


def _has_forbidden_path(value: str) -> bool:
    lower = value.lower()
    parts = set(Path(lower).parts)

    if parts.intersection(FORBIDDEN_PARTS):
        return True

    if any(lower.endswith(suffix) for suffix in FORBIDDEN_SUFFIX_COMPOUNDS):
        return True

    if Path(lower).suffix in FORBIDDEN_SUFFIXES:
        return True

    return False


def _load_checksum_file(path: Path) -> dict[str, str]:
    checksums: dict[str, str] = {}

    if not path.exists():
        return checksums

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue

        parts = line.split(None, 1)
        if len(parts) != 2:
            continue

        digest, rel = parts
        checksums[rel.strip()] = digest.strip()

    return checksums


def _locate_package(
    exports_dir: str,
    export_id: str | None,
    package_dir: str | None,
    zip_path: str | None,
) -> tuple[Path | None, Path | None, str | None, list[str], list[str]]:
    warnings: list[str] = []
    errors: list[str] = []

    root = Path(exports_dir) / "rsfmri_report_package"

    if package_dir:
        pkg = Path(package_dir)
        resolved_export_id = pkg.name
    elif export_id:
        pkg = root / export_id
        resolved_export_id = export_id
    else:
        if not root.exists():
            return None, None, None, warnings, ["No report package root found."]

        packages = sorted([child for child in root.iterdir() if child.is_dir()])
        if not packages:
            return None, None, None, warnings, ["No report package directories found."]

        pkg = packages[-1]
        resolved_export_id = pkg.name
        warnings.append(f"No export_id provided. Using latest package: {resolved_export_id}")

    zpath = Path(zip_path) if zip_path else pkg.parent / f"{resolved_export_id}.zip"
    return pkg, zpath, resolved_export_id, warnings, errors


def _validate_required_files(package_dir: Path) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    checks = []
    warnings: list[str] = []
    errors: list[str] = []

    for rel in REQUIRED_FILES:
        path = package_dir / rel
        exists = path.exists()
        non_empty = path.is_file() and path.stat().st_size > 0 if exists else False

        status = "PASS" if exists and non_empty else "FAIL"
        if not exists:
            errors.append(f"Required file missing: {rel}")
        elif not non_empty:
            errors.append(f"Required file is empty: {rel}")

        checks.append({
            "name": f"required_file:{rel}",
            "status": status,
            "path": str(path),
            "exists": exists,
            "non_empty": non_empty,
        })

    return checks, warnings, errors


def _validate_manifest_files(package_dir: Path, manifest: dict[str, Any] | None) -> tuple[list[dict[str, Any]], list[str], list[str], dict[str, Any]]:
    checks = []
    warnings: list[str] = []
    errors: list[str] = []
    stats = {
        "manifest_files_total": 0,
        "missing_files_total": 0,
        "checksum_mismatch_total": 0,
        "size_mismatch_total": 0,
        "unsafe_path_total": 0,
        "forbidden_file_total": 0,
    }

    if not manifest:
        errors.append("MANIFEST.json could not be read.")
        checks.append({
            "name": "manifest_readable",
            "status": "FAIL",
        })
        return checks, warnings, errors, stats

    files = manifest.get("files")
    if not isinstance(files, list):
        errors.append("MANIFEST.json missing list field: files.")
        checks.append({
            "name": "manifest_files_list",
            "status": "FAIL",
        })
        return checks, warnings, errors, stats

    checksum_map = _load_checksum_file(package_dir / "checksums" / "SHA256SUMS.txt")
    stats["manifest_files_total"] = len(files)

    for item in files:
        rel = item.get("relative_path")
        expected_sha = item.get("sha256")
        expected_size = item.get("size_bytes")

        if not isinstance(rel, str) or not _is_safe_relative_path(rel):
            stats["unsafe_path_total"] += 1
            errors.append(f"Unsafe manifest relative_path: {rel}")
            checks.append({
                "name": "manifest_file_path",
                "relative_path": rel,
                "status": "FAIL",
                "reason": "unsafe_path",
            })
            continue

        if _has_forbidden_path(rel):
            stats["forbidden_file_total"] += 1
            errors.append(f"Forbidden file included in manifest/package: {rel}")

        path = package_dir / rel

        if not path.exists():
            stats["missing_files_total"] += 1
            errors.append(f"Manifest file missing from package: {rel}")
            checks.append({
                "name": "manifest_file_exists",
                "relative_path": rel,
                "status": "FAIL",
            })
            continue

        actual_size = int(path.stat().st_size)
        actual_sha = _sha256(path)

        size_ok = expected_size is None or int(expected_size) == actual_size
        sha_ok = expected_sha == actual_sha

        checksum_file_sha = checksum_map.get(rel)
        checksum_file_ok = checksum_file_sha is None or checksum_file_sha == actual_sha

        if not size_ok:
            stats["size_mismatch_total"] += 1
            errors.append(f"Size mismatch for {rel}: manifest={expected_size}, actual={actual_size}")

        if not sha_ok:
            stats["checksum_mismatch_total"] += 1
            errors.append(f"SHA256 mismatch for {rel}")

        if checksum_file_sha is not None and not checksum_file_ok:
            stats["checksum_mismatch_total"] += 1
            errors.append(f"SHA256SUMS mismatch for {rel}")

        checks.append({
            "name": "manifest_file_integrity",
            "relative_path": rel,
            "status": "PASS" if size_ok and sha_ok and checksum_file_ok and not _has_forbidden_path(rel) else "FAIL",
            "size_ok": size_ok,
            "sha256_ok": sha_ok,
            "checksum_file_ok": checksum_file_ok,
            "actual_size_bytes": actual_size,
            "actual_sha256": actual_sha,
        })

    return checks, warnings, errors, stats


def _validate_zip(zip_path: Path, manifest: dict[str, Any] | None) -> tuple[list[dict[str, Any]], list[str], list[str], dict[str, Any]]:
    checks = []
    warnings: list[str] = []
    errors: list[str] = []
    stats = {
        "zip_exists": False,
        "zip_test_ok": False,
        "zip_entries_total": 0,
        "zip_unsafe_path_total": 0,
        "zip_forbidden_file_total": 0,
        "zip_missing_required_total": 0,
        "zip_missing_manifest_files_total": 0,
    }

    if not zip_path.exists():
        errors.append(f"ZIP file missing: {zip_path}")
        checks.append({
            "name": "zip_exists",
            "status": "FAIL",
            "zip_path": str(zip_path),
        })
        return checks, warnings, errors, stats

    stats["zip_exists"] = True

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            bad_file = zf.testzip()
            stats["zip_test_ok"] = bad_file is None

            if bad_file is not None:
                errors.append(f"ZIP test failed at file: {bad_file}")

            names = zf.namelist()
            stats["zip_entries_total"] = len(names)

            name_set = set(names)

            for name in names:
                if not _is_safe_relative_path(name):
                    stats["zip_unsafe_path_total"] += 1
                    errors.append(f"Unsafe path in ZIP: {name}")

                if _has_forbidden_path(name):
                    stats["zip_forbidden_file_total"] += 1
                    errors.append(f"Forbidden file included in ZIP: {name}")

            for required in REQUIRED_FILES:
                if required not in name_set:
                    stats["zip_missing_required_total"] += 1
                    errors.append(f"Required file missing from ZIP: {required}")

            if manifest and isinstance(manifest.get("files"), list):
                for item in manifest["files"]:
                    rel = item.get("relative_path")
                    if isinstance(rel, str) and rel not in name_set:
                        # validation files can be created after export and are not necessarily in the original zip.
                        if not rel.startswith("validation/"):
                            stats["zip_missing_manifest_files_total"] += 1
                            errors.append(f"Manifest file missing from ZIP: {rel}")

            checks.append({
                "name": "zip_integrity",
                "status": "PASS" if not errors and stats["zip_test_ok"] else ("PASS" if stats["zip_test_ok"] and stats["zip_unsafe_path_total"] == 0 and stats["zip_forbidden_file_total"] == 0 else "FAIL"),
                "zip_path": str(zip_path),
                "zip_entries_total": stats["zip_entries_total"],
                "zip_test_ok": stats["zip_test_ok"],
            })

    except Exception as exc:
        errors.append(f"ZIP could not be opened: {exc}")
        checks.append({
            "name": "zip_open",
            "status": "FAIL",
            "zip_path": str(zip_path),
            "error": str(exc),
        })

    return checks, warnings, errors, stats


def _validate_safety(manifest: dict[str, Any] | None) -> tuple[list[dict[str, Any]], list[str], list[str], dict[str, Any]]:
    checks = []
    warnings: list[str] = []
    errors: list[str] = []
    stats = {
        "safety_flags_checked": 0,
        "safety_violations_total": 0,
    }

    if not manifest:
        errors.append("Cannot validate safety because manifest is missing.")
        return checks, warnings, errors, stats

    safety = manifest.get("safety")
    if not isinstance(safety, dict):
        errors.append("MANIFEST.json missing safety object.")
        checks.append({
            "name": "safety_object",
            "status": "FAIL",
        })
        return checks, warnings, errors, stats

    for flag in SAFETY_FALSE_FLAGS:
        stats["safety_flags_checked"] += 1
        value = safety.get(flag)

        ok = value is False
        if not ok:
            stats["safety_violations_total"] += 1
            errors.append(f"Safety flag violation: {flag}={value}")

        checks.append({
            "name": f"safety_flag:{flag}",
            "status": "PASS" if ok else "FAIL",
            "value": value,
            "expected": False,
        })

    return checks, warnings, errors, stats


def _write_validation_report(path: Path, result: dict[str, Any]) -> None:
    lines = []
    lines.append(f"# rs-fMRI Report Package Validation")
    lines.append("")
    lines.append(f"- Export ID: `{result.get('export_id')}`")
    lines.append(f"- Status: **{result.get('validation_status')}**")
    lines.append(f"- OK: {result.get('ok')}")
    lines.append(f"- Package directory: `{result.get('package_dir')}`")
    lines.append(f"- ZIP: `{result.get('zip_path')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    stats = result.get("stats", {})
    lines.append(f"- Required files missing: {stats.get('required_files_missing_total')}")
    lines.append(f"- Manifest files total: {stats.get('manifest_files_total')}")
    lines.append(f"- Missing files: {stats.get('missing_files_total')}")
    lines.append(f"- Checksum mismatches: {stats.get('checksum_mismatch_total')}")
    lines.append(f"- Size mismatches: {stats.get('size_mismatch_total')}")
    lines.append(f"- Unsafe paths: {stats.get('unsafe_path_total')}")
    lines.append(f"- Forbidden files: {stats.get('forbidden_file_total')}")
    lines.append(f"- ZIP entries: {stats.get('zip_entries_total')}")
    lines.append(f"- ZIP test OK: {stats.get('zip_test_ok')}")
    lines.append(f"- Safety violations: {stats.get('safety_violations_total')}")
    lines.append("")
    lines.append("## Warnings")
    lines.append("")
    for warning in result.get("warnings", []):
        lines.append(f"- {warning}")
    if not result.get("warnings"):
        lines.append("- None")
    lines.append("")
    lines.append("## Errors")
    lines.append("")
    for error in result.get("errors", []):
        lines.append(f"- {error}")
    if not result.get("errors"):
        lines.append("- None")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This validator is read-only for source outputs and does not repair, regenerate, or clinically interpret the package.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _update_validation_index(exports_dir: str, result: dict[str, Any]) -> None:
    root = Path(exports_dir) / "rsfmri_report_package"
    root.mkdir(parents=True, exist_ok=True)
    index_path = root / "VALIDATION_INDEX.json"

    current = _read_json(index_path) or {
        "ok": True,
        "validations": [],
    }

    validations = current.get("validations", [])
    if not isinstance(validations, list):
        validations = []

    entry = {
        "export_id": result.get("export_id"),
        "validated_at": result.get("validated_at"),
        "validation_status": result.get("validation_status"),
        "ok": result.get("ok"),
        "package_dir": result.get("package_dir"),
        "zip_path": result.get("zip_path"),
        "validation_result": result.get("validation_result_json"),
        "validation_report": result.get("validation_report_md"),
    }

    validations = [item for item in validations if item.get("export_id") != entry["export_id"]]
    validations.append(entry)

    current = {
        "ok": True,
        "updated_at": _iso_now(),
        "validations_total": len(validations),
        "validations": validations,
    }

    _write_json(index_path, current)


def validate_rsfmri_report_package(
    exports_dir: str = "./exports",
    export_id: str | None = None,
    package_dir: str | None = None,
    zip_path: str | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    located_package, located_zip, resolved_export_id, locate_warnings, locate_errors = _locate_package(
        exports_dir=exports_dir,
        export_id=export_id,
        package_dir=package_dir,
        zip_path=zip_path,
    )

    warnings: list[str] = list(locate_warnings)
    errors: list[str] = list(locate_errors)
    checks: list[dict[str, Any]] = []

    if located_package is None or resolved_export_id is None:
        return {
            "ok": False,
            "node_id": "rsfmri_report_package_validator",
            "backend": "python",
            "validation_status": "FAIL",
            "exports_dir": exports_dir,
            "warnings": warnings,
            "errors": errors,
        }

    validation_dir = located_package / "validation"
    validation_dir.mkdir(parents=True, exist_ok=True)

    validation_result_json = validation_dir / "validation_result.json"
    validation_report_md = validation_dir / "validation_report.md"

    if not located_package.exists():
        errors.append(f"Package directory missing: {located_package}")

    required_checks, required_warnings, required_errors = _validate_required_files(located_package)
    checks.extend(required_checks)
    warnings.extend(required_warnings)
    errors.extend(required_errors)

    required_missing_total = sum(1 for item in required_checks if item.get("status") != "PASS")

    manifest_path = located_package / "MANIFEST.json"
    manifest = _read_json(manifest_path)

    manifest_checks, manifest_warnings, manifest_errors, manifest_stats = _validate_manifest_files(located_package, manifest)
    checks.extend(manifest_checks)
    warnings.extend(manifest_warnings)
    errors.extend(manifest_errors)

    zip_checks, zip_warnings, zip_errors, zip_stats = _validate_zip(located_zip, manifest)
    checks.extend(zip_checks)
    warnings.extend(zip_warnings)
    errors.extend(zip_errors)

    safety_checks, safety_warnings, safety_errors, safety_stats = _validate_safety(manifest)
    checks.extend(safety_checks)
    warnings.extend(safety_warnings)
    errors.extend(safety_errors)

    stats = {
        "required_files_missing_total": required_missing_total,
        **manifest_stats,
        **zip_stats,
        **safety_stats,
        "checks_total": len(checks),
        "warnings_total": len(warnings),
        "errors_total": len(errors),
    }

    if errors:
        status = "FAIL"
    elif warnings:
        status = "WARNING"
    else:
        status = "PASS"

    ok = status == "PASS" or (status == "WARNING" and not strict)

    result = {
        "ok": ok,
        "node_id": "rsfmri_report_package_validator",
        "backend": "python",
        "export_id": resolved_export_id,
        "validated_at": _iso_now(),
        "validation_status": status,
        "strict": strict,
        "package_dir": str(located_package),
        "zip_path": str(located_zip),
        "validation_result_json": str(validation_result_json),
        "validation_report_md": str(validation_report_md),
        "stats": stats,
        "checks": checks,
        "warnings": warnings,
        "errors": errors,
        "outputs": [
            str(validation_result_json),
            str(validation_report_md),
            str(Path(exports_dir) / "rsfmri_report_package" / "VALIDATION_INDEX.json"),
        ],
    }

    _write_json(validation_result_json, result)
    _write_validation_report(validation_report_md, result)
    _update_validation_index(exports_dir, result)

    return result


def _package_root(exports_dir: str) -> Path:
    return Path(exports_dir) / "rsfmri_report_package"


def list_rsfmri_report_validations(
    exports_dir: str = "./exports",
) -> dict[str, Any]:
    root = _package_root(exports_dir)
    index_path = root / "VALIDATION_INDEX.json"
    index = _read_json(index_path)

    validations = []
    if index and isinstance(index.get("validations"), list):
        validations = index["validations"]
    elif root.exists():
        for package in sorted(root.iterdir()):
            if not package.is_dir():
                continue
            validation_path = package / "validation" / "validation_result.json"
            payload = _read_json(validation_path)
            if payload:
                validations.append({
                    "export_id": package.name,
                    "validated_at": payload.get("validated_at"),
                    "validation_status": payload.get("validation_status"),
                    "ok": payload.get("ok"),
                    "package_dir": str(package),
                    "zip_path": payload.get("zip_path"),
                    "validation_result": str(validation_path),
                    "validation_report": str(package / "validation" / "validation_report.md"),
                })

    return {
        "ok": True,
        "validations_total": len(validations),
        "validations": validations,
    }


def get_latest_rsfmri_report_validation(
    exports_dir: str = "./exports",
) -> dict[str, Any]:
    listing = list_rsfmri_report_validations(exports_dir=exports_dir)
    validations = listing.get("validations", [])

    if not validations:
        return {
            "ok": False,
            "warnings": [],
            "errors": ["No rs-fMRI report package validations found."],
        }

    latest = validations[-1]
    validation_result_path = latest.get("validation_result")
    validation_report_path = latest.get("validation_report")

    result = _read_json(Path(validation_result_path)) if validation_result_path else None
    report = Path(validation_report_path).read_text(encoding="utf-8") if validation_report_path and Path(validation_report_path).exists() else None

    return {
        "ok": bool(result),
        "latest": latest,
        "validation_result": result,
        "validation_report": report,
    }
```

---

## 3. 修改 backend/app/runtime/node_registry.py

新增节点：

```text
rsfmri_report_package_validator
```

新增导入：

```python
from backend.app.tools.report_package_validator import validate_rsfmri_report_package
```

新增 runner：

```python
def run_rsfmri_report_package_validator_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = validate_rsfmri_report_package(
        exports_dir=node.params.get("exports_dir", "./exports"),
        export_id=node.params.get("export_id"),
        package_dir=node.params.get("package_dir"),
        zip_path=node.params.get("zip_path"),
        strict=bool(node.params.get("strict", False)),
    )
    result["node_id"] = node.id
    return result
```

更新 `NODE_REGISTRY`：

```python
"rsfmri_report_package_validator": run_rsfmri_report_package_validator_node,
```

---

## 4. 创建 examples/pipeline_rsfmri_report_validator.yaml

创建文件：

```text
examples/pipeline_rsfmri_report_validator.yaml
```

内容：

```yaml
pipeline_id: rsfmri_report_validator_pipeline
version: "0.1.0"
modality: rs-fMRI
description: "Validate an exported synthetic rs-fMRI report package for integrity, checksums, ZIP consistency, and safety declarations."

execution:
  stop_on_failure: true
  run_id: "run_rsfmri_report_validator_001"
  scheduler:
    mode: "local"
    max_workers: 1
    matlab_max_workers: 0

nodes:
  - id: rsfmri_report_package_validator
    name: rs-fMRI Report Package Validator
    agent: report-runner
    backend: python
    depends_on: []
    inputs:
      - "./exports/rsfmri_report_package"
    outputs:
      - "./exports/rsfmri_report_package/VALIDATION_INDEX.json"
    params:
      exports_dir: "./exports"
      export_id: null
      package_dir: null
      zip_path: null
      strict: false
    parallel_level: project
    gpu_supported: false
    cache: false
```

本 pipeline 不执行任何 SPM / MATLAB / DPABI / GPU。  
它只读取 exports 中的 report package，并写 validation 结果。

---

## 5. 创建 backend/app/tools/run_rsfmri_report_validator_cli.py

创建文件：

```text
backend/app/tools/run_rsfmri_report_validator_cli.py
```

内容：

```python
from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.pipeline_executor import run_pipeline


def main() -> int:
    args = sys.argv[1:]

    project_config = Path(args[0]) if len(args) > 0 else Path("examples/project_config_dataset.yaml")
    pipeline = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_rsfmri_report_validator.yaml")

    summary = run_pipeline(project_config, pipeline)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    status = summary.get("status")
    if status == "SUCCESS":
        return 0
    if status == "INVALID":
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

---

## 6. 修改 backend/app/api/models.py

新增 request model：

```python
class RsfmriReportValidationRequest(BaseModel):
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    pipeline_path: str = Field(default="examples/pipeline_rsfmri_report_validator.yaml")
```

---

## 7. 修改 backend/app/api/routes.py

新增 API：

```text
POST /api/rsfmri/report-validator/run
GET  /api/rsfmri/report-validator/latest
GET  /api/rsfmri/report-validator/list
```

新增导入：

```python
from backend.app.api.models import RsfmriReportValidationRequest
from backend.app.runtime.pipeline_executor import run_pipeline
from backend.app.tools.report_package_validator import (
    get_latest_rsfmri_report_validation,
    list_rsfmri_report_validations,
)
```

新增路由：

```python
@router.post("/api/rsfmri/report-validator/run")
def api_run_rsfmri_report_validator(
    request: RsfmriReportValidationRequest,
) -> dict[str, Any]:
    try:
        summary = run_pipeline(
            request.project_config_path,
            request.pipeline_path,
        )

        if summary.get("status") not in {"SUCCESS", "PARTIAL"}:
            raise HTTPException(status_code=400, detail=summary)

        return summary

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/rsfmri/report-validator/latest")
def api_get_latest_rsfmri_report_validation() -> dict[str, Any]:
    return get_latest_rsfmri_report_validation(exports_dir="./exports")


@router.get("/api/rsfmri/report-validator/list")
def api_list_rsfmri_report_validations() -> dict[str, Any]:
    return list_rsfmri_report_validations(exports_dir="./exports")
```

注意：本 POST 不需要 approved，因为不执行 SPM / DPABI / GPU，只做 report package validation。

---

## 8. 修改 frontend/src/api.ts

新增：

```ts
export async function runRsfmriReportValidation(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/report-validator/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getLatestRsfmriReportValidation(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/report-validator/latest"
  );
}

export async function listRsfmriReportValidations(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/report-validator/list"
  );
}
```

---

## 9. 创建 frontend/src/components/RsfmriReportValidatorPanel.tsx

创建文件：

```text
frontend/src/components/RsfmriReportValidatorPanel.tsx
```

内容：

```tsx
import { useState } from "react";
import {
  getLatestRsfmriReportValidation,
  listRsfmriReportValidations,
  runRsfmriReportValidation
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function RsfmriReportValidatorPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [latest, setLatest] = useState<Record<string, unknown> | null>(null);
  const [validationsList, setValidationsList] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    setStatus("RUNNING");
    setError("");

    try {
      const response = await runRsfmriReportValidation(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_report_validator.yaml"
      });
      setResult(response);
      setStatus("SUCCESS");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleLoadLatest() {
    setStatus("LOADING");
    setError("");

    try {
      const response = await getLatestRsfmriReportValidation(baseUrl);
      setLatest(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleList() {
    setStatus("LOADING");
    setError("");

    try {
      const response = await listRsfmriReportValidations(baseUrl);
      setValidationsList(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const validationResult = latest?.validation_result as Record<string, unknown> | undefined;
  const stats = validationResult?.stats as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button onClick={handleRun}>
          验证最新 rs-fMRI Report Package
        </button>
        <button onClick={handleLoadLatest}>加载最新验证结果</button>
        <button onClick={handleList}>列出历史验证结果</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="metricGrid">
        <div className="metricCard">
          <span>Validation Status</span>
          <strong>{String(validationResult?.validation_status ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Checksum Mismatch</span>
          <strong>{String(stats?.checksum_mismatch_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Missing Files</span>
          <strong>{String(stats?.missing_files_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>ZIP Test OK</span>
          <strong>{String(stats?.zip_test_ok ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Safety Violations</span>
          <strong>{String(stats?.safety_violations_total ?? "-")}</strong>
        </div>
      </div>

      <h3>Run Summary</h3>
      <JsonBlock value={result} emptyText="尚未运行" />

      <h3>Latest Validation Result</h3>
      <JsonBlock value={latest?.validation_result} emptyText="暂无最新 validation result" />

      <h3>Validation Checks</h3>
      <JsonBlock value={validationResult?.checks} emptyText="暂无 validation checks" />

      <h3>Validation Report</h3>
      <TextViewer
        text={
          typeof latest?.validation_report === "string"
            ? latest.validation_report
            : null
        }
        emptyText="暂无 validation report"
      />

      <h3>Validation List</h3>
      <JsonBlock value={validationsList} emptyText="暂无 validation list" />
    </div>
  );
}
```

---

## 10. 修改 frontend/src/App.tsx

新增导入：

```tsx
import { RsfmriReportValidatorPanel } from "./components/RsfmriReportValidatorPanel";
```

在 `rs-fMRI Report Exporter` 后新增 Section：

```tsx
<Section
  title="rs-fMRI Report Package Validator"
  description="校验报告包完整性、checksums、ZIP 内容和安全声明。"
>
  <RsfmriReportValidatorPanel baseUrl={baseUrl} />
</Section>
```

---

## 11. 新增轻量测试

创建文件：

```text
tests/unit/test_report_package_validator.py
```

内容：

```python
from __future__ import annotations

import json
import zipfile
from pathlib import Path

from backend.app.tools.report_package_validator import (
    get_latest_rsfmri_report_validation,
    list_rsfmri_report_validations,
    validate_rsfmri_report_package,
)


def _sha256(path: Path) -> str:
    import hashlib

    hasher = hashlib.sha256()
    with path.open("rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()


def test_report_package_validator_passes_valid_package(tmp_path: Path):
    exports = tmp_path / "exports"
    root = exports / "rsfmri_report_package"
    package = root / "test_export"
    package.mkdir(parents=True)

    readme = package / "README.md"
    index = package / "index.md"
    export_summary = package / "export_summary.json"
    checksums = package / "checksums" / "SHA256SUMS.txt"
    checksums.parent.mkdir(parents=True)

    readme.write_text("# README\n", encoding="utf-8")
    index.write_text("# Index\n", encoding="utf-8")
    export_summary.write_text(json.dumps({"ok": True}), encoding="utf-8")

    manifest = {
        "package_id": "test_export",
        "export_id": "test_export",
        "created_at": "2026-01-01T00:00:00",
        "source_roots": {},
        "safety": {
            "rawdata_included": False,
            "rawdata_modified": False,
            "derivatives_modified": False,
            "reports_modified": False,
            "work_modified": False,
            "spm_executed": False,
            "matlab_executed": False,
            "dpabi_executed": False,
            "gpu_executed": False,
            "files_deleted": False,
            "clinical_conclusions_generated": False,
            "statistical_inference_performed": False,
        },
        "files": [],
        "excluded_files": [],
        "warnings": [],
        "errors": [],
    }

    # Create manifest after basic files, then calculate checksums.
    manifest_path = package / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    files = []
    for path in [readme, index, export_summary, manifest_path]:
        files.append({
            "relative_path": str(path.relative_to(package)),
            "source_path": None,
            "size_bytes": path.stat().st_size,
            "sha256": _sha256(path),
            "category": "test",
        })

    checksum_lines = [f"{item['sha256']}  {item['relative_path']}" for item in files]
    checksums.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    files.append({
        "relative_path": "checksums/SHA256SUMS.txt",
        "source_path": None,
        "size_bytes": checksums.stat().st_size,
        "sha256": _sha256(checksums),
        "category": "checksum",
    })

    manifest["files"] = files
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Refresh manifest checksum in its own entry after rewrite.
    for item in manifest["files"]:
        if item["relative_path"] == "MANIFEST.json":
            item["size_bytes"] = manifest_path.stat().st_size
            item["sha256"] = _sha256(manifest_path)

    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Refresh checksum file to match final files except checksum file itself can be absent from checksum map.
    checksum_lines = []
    for item in manifest["files"]:
        if item["relative_path"] != "checksums/SHA256SUMS.txt":
            checksum_lines.append(f"{item['sha256']}  {item['relative_path']}")
    checksums.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    for item in manifest["files"]:
        if item["relative_path"] == "checksums/SHA256SUMS.txt":
            item["size_bytes"] = checksums.stat().st_size
            item["sha256"] = _sha256(checksums)

    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    zip_path = root / "test_export.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in package.rglob("*"):
            if path.is_file():
                zf.write(path, arcname=str(path.relative_to(package)))

    result = validate_rsfmri_report_package(
        exports_dir=str(exports),
        export_id="test_export",
    )

    assert result["ok"] is True
    assert result["validation_status"] in {"PASS", "WARNING"}
    assert (package / "validation" / "validation_result.json").exists()
    assert (package / "validation" / "validation_report.md").exists()
    assert (root / "VALIDATION_INDEX.json").exists()

    latest = get_latest_rsfmri_report_validation(exports_dir=str(exports))
    assert latest["ok"] is True

    listing = list_rsfmri_report_validations(exports_dir=str(exports))
    assert listing["ok"] is True
    assert listing["validations_total"] == 1
```

---

## 12. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

```python
call("GET", "/api/rsfmri/report-validator/latest")
call("GET", "/api/rsfmri/report-validator/list")
```

不要在 smoke test 中调用 POST run，避免改变 exports validation。

---

## 13. 更新 README.md

追加第四十九步说明：

```markdown
## Step 49: Report Package Validator

This step validates exported synthetic rs-fMRI report packages.

It supports:

- report package directory validation
- zip archive validation
- MANIFEST.json validation
- SHA256 checksum validation
- required file validation
- safety flag audit
- forbidden rawdata / NIfTI / MAT inclusion checks
- validation JSON report
- validation Markdown report
- backend API visibility
- frontend validator panel

It does not repair packages and does not execute SPM, MATLAB, DPABI, or GPU code.

### Run

```bash
python -m backend.app.tools.run_rsfmri_report_validator_cli
```

Expected outputs:

```text
exports/rsfmri_report_package/{export_id}/validation/validation_result.json
exports/rsfmri_report_package/{export_id}/validation/validation_report.md
exports/rsfmri_report_package/VALIDATION_INDEX.json
work/pipeline_runs/run_rsfmri_report_validator_001/summary.json
```

### API

```bash
curl http://127.0.0.1:8000/api/rsfmri/report-validator/latest
curl http://127.0.0.1:8000/api/rsfmri/report-validator/list
```

Run validation:

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/report-validator/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_rsfmri_report_validator.yaml"
  }'
```

### Frontend

Use:

```text
rs-fMRI Report Package Validator
```

### Safety

This step:

- only reads exports
- writes only validation artifacts under exports
- does not include or modify rawdata
- does not modify derivatives / reports / work
- does not repair packages
- does not run SPM
- does not run MATLAB
- does not run DPABI
- does not run GPU
- does not call DPARSF_run
- does not call DPARSFA_run
- does not call DPABI GUI
- does not perform group-level statistical inference
- does not make clinical conclusions
```

---

## 14. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/report_package_validator_spec.md
backend/app/tools/report_package_validator.py
backend/app/runtime/node_registry.py
examples/pipeline_rsfmri_report_validator.yaml
backend/app/tools/run_rsfmri_report_validator_cli.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/RsfmriReportValidatorPanel.tsx
frontend/src/App.tsx
tests/unit/test_report_package_validator.py
backend/app/tools/api_smoke_test.py
README.md
```

先确保已有 Step 48 export package：

```bash
python -m backend.app.tools.run_rsfmri_report_exporter_cli
```

然后运行 validator：

```bash
python -m backend.app.tools.run_rsfmri_report_validator_cli
```

应生成：

```text
exports/rsfmri_report_package/{export_id}/validation/validation_result.json
exports/rsfmri_report_package/{export_id}/validation/validation_report.md
exports/rsfmri_report_package/VALIDATION_INDEX.json
```

validation_result JSON 必须包含：

```json
{
  "node_id": "rsfmri_report_package_validator",
  "export_id": "rsfmri_export_...",
  "validation_status": "PASS",
  "stats": {
    "required_files_missing_total": 0,
    "checksum_mismatch_total": 0,
    "missing_files_total": 0,
    "zip_test_ok": true,
    "safety_violations_total": 0
  },
  "checks": [],
  "warnings": [],
  "errors": []
}
```

实际状态可为 PASS / WARNING / FAIL，取决于 report package 是否包含 manifest 中所有文件、zip 是否完整、checksum 是否一致。

运行测试：

```bash
python -m pytest tests/unit/test_report_package_validator.py -q
```

启动后端：

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

测试 API：

```bash
curl http://127.0.0.1:8000/api/rsfmri/report-validator/latest
curl http://127.0.0.1:8000/api/rsfmri/report-validator/list

curl -X POST http://127.0.0.1:8000/api/rsfmri/report-validator/run \
  -H "Content-Type: application/json" \
  -d '{}'
```

启动前端：

```bash
cd frontend
npm run dev
```

页面应该能完成：

1. 显示 rs-fMRI Report Package Validator 区域。
2. 可以点击验证最新 report package。
3. 可以加载最新 validation result。
4. 可以列出历史 validation。
5. 显示 validation status。
6. 显示 checksum mismatch 数量。
7. 显示 missing files 数量。
8. 显示 ZIP test OK。
9. 显示 safety violations 数量。
10. 显示 validation result JSON。
11. 显示 validation checks JSON。
12. 显示 validation Markdown report。
13. 不修改 rawdata。
14. 不修改 derivatives / reports / work。
15. 不修复 package。
16. 不运行 SPM / MATLAB。
17. 不运行 DPABI。
18. 不运行 GPU。
19. 不执行统计推断。
20. 不生成临床结论。

---

## 15. 重要限制

本步骤只做 Report Package Validator。

不要实现：

- 自动修复 package
- 重新导出 package
- PDF 生成
- Word 文档生成
- PowerPoint 生成
- group-level statistical testing
- GLM
- t-tests
- multiple-comparison correction
- clinical interpretation
- subject exclusion automation
- graph theory metrics
- dynamic FC
- 真实医学影像处理
- DPABI 全流程执行
- DPARSF_run 自动执行
- DPARSFA_run 自动执行
- DPABI GUI 自动化
- SPM / MATLAB 执行
- GPU 执行
- rawdata 修改
- 文件删除

完成后请总结：

1. 新增了哪些文件
2. 修改了哪些文件
3. validator 如何定位最新 export package
4. required files 如何检查
5. MANIFEST.json 如何校验
6. SHA256SUMS 如何交叉校验
7. ZIP archive 如何校验
8. safety flags 如何审计
9. forbidden rawdata / NIfTI / MAT 如何检查
10. validation_result.json 和 validation_report.md 分别包含什么
11. 为什么本步骤不自动修复 report package
12. 下一步如何实现 Project Release Readiness Check：检查代码、测试、文档、API、前端和安全边界是否准备好进入 MVP release

```
给报告包加了一个独立校验器。

`report_package_validator.py` 读 Step 48 导出的报告包，逐项检查：必需要文件（MANIFEST.json / README.md / index.md / export_summary.json / SHA256SUMS.txt）是否存在且非空、manifest 里每个文件的 sha256 和文件大小是否与实际一致、SHA256SUMS.txt 是否与 manifest 交叉吻合、ZIP 是否能正常打开且 `testzip()` 通过、包内有没有不该出现的东西（rawdata 路径、.nii/.mat 等二进制文件），以及 12 个 safety flag 是否全部为 `false`（确认导出过程没有执行 SPM/MATLAB/DPABI/GPU、没有修改原始数据、没有做统计推断）。

校验结果写成 validation_result.json 和 validation_report.md，放在对应 report package 的 `validation/` 子目录下，同时更新全局的 VALIDATION_INDEX.json。只读不修，有问题只报告不自动修复。
```
