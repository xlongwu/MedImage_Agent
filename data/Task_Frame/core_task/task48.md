# 第四十八步 Prompt：Dataset Report Exporter + 可交付报告包闭环

```text
你是我的工程搭建助手。前四十七步已经完成：

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

现在开始第四十八步。

第四十八步目标：实现 “Dataset Report Exporter + 可交付报告包闭环”。

当前系统已经可以生成大量分散的工程产物：

- subject-level QC JSON / Markdown
- dataset-level QC summary JSON / Markdown
- metrics maps / FC matrices
- backend contracts
- pipeline run summaries
- group-level dashboard JSON / CSV / Markdown

但还缺少一个可交付报告包导出器，把这些文件按稳定结构打包成一个可审查、可归档、可交付的 report package。

本步骤要实现：

1. Dataset Report Exporter specification。
2. 一个只读 report exporter：
   - 读取 `reports/rsfmri/group_summary`
   - 读取 `reports/rsfmri/*.json` / `*.md`
   - 读取 subject-level QC JSON / Markdown
   - 读取 metrics result JSON
   - 读取 FC result JSON / matrix TSV
   - 读取 DPABI/GPU contracts
   - 读取 pipeline run summary
3. 生成统一 export directory：

```text
exports/rsfmri_report_package/{export_id}/
```

4. 输出 report package 目录结构：
   - `MANIFEST.json`
   - `README.md`
   - `index.md`
   - `summary/`
   - `subjects/`
   - `metrics/`
   - `fc/`
   - `contracts/`
   - `pipeline_runs/`
   - `tables/`
   - `checksums/`
5. 复制或汇总关键文件：
   - group dataset summary
   - dashboard data
   - subject metrics table
   - pipeline completeness
   - contracts overview
   - subject-level QC
   - metrics result JSON
   - FC matrix metadata
   - reports Markdown
6. 生成 manifest：
   - package_id
   - created_at
   - source roots
   - file list
   - file sizes
   - sha256 checksums
   - safety flags
7. 生成 export summary JSON：
   - exported_subjects
   - exported_files_total
   - missing_expected_files
   - warnings
   - errors
8. 生成 Markdown index：
   - report package overview
   - subject list
   - core dataset status
   - included files
   - safety notes
   - limitations
9. 生成 zip：
   - `exports/rsfmri_report_package/{export_id}.zip`
10. 后端 API：
   - `POST /api/rsfmri/report-export/run`
   - `GET /api/rsfmri/report-export/latest`
   - `GET /api/rsfmri/report-export/list`
11. 前端新增面板：
   - rs-fMRI Report Exporter
   - 可以生成报告包
   - 可以加载最新报告包
   - 显示 export summary
   - 显示 manifest
   - 显示 zip 路径
   - 显示 README / index
12. 新增 pipeline：
   - 只运行 exporter，不执行 SPM / MATLAB / DPABI / GPU。
13. 增加轻量 unit test。
14. 更新 README。

本步骤必须满足：

- 只读取 derivatives / reports / work 中已有 synthetic outputs。
- 只写入 exports。
- 不处理真实医学影像数据。
- 不修改 rawdata。
- 不修改 derivatives / reports / work 中已有文件。
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
- 不自动排除 subject。

本步骤不要实现：

- PDF 生成
- Word 文档生成
- PowerPoint 生成
- group-level statistical testing
- GLM / t-test
- multiple comparison correction
- graph theory metrics
- dynamic FC
- clinical interpretation
- real medical data handling
- Docker / release / CI 等外围功能

本步骤只做：把已有 Markdown / JSON / CSV / TSV 工程结果整理、复制、校验、打包成一个可交付 ZIP 报告包。

---

## 1. 创建 specs/dataset_report_exporter_spec.md

创建文件：

```text
specs/dataset_report_exporter_spec.md
```

内容：

```markdown
# Dataset Report Exporter Specification

This document defines the MVP dataset report exporter for rs-fMRI engineering validation.

## Goals

The goal is to package existing synthetic rs-fMRI QC outputs, metrics summaries, contracts, and pipeline run summaries into a reproducible, auditable, zip-based report package.

The exporter is read-only with respect to source outputs and writes only under `exports`.

## Scope

Supported in this step:

- read-only scan of derivatives / reports / work
- group summary export
- subject-level QC export
- metrics result JSON export
- FC result export
- backend contract export
- pipeline run summary export
- manifest with sha256 checksums
- Markdown package index
- ZIP report package
- backend API visibility
- frontend exporter panel
- lightweight unit tests

Unsupported in this step:

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
- source file deletion

## Inputs

```text
reports/rsfmri/group_summary/*
reports/rsfmri/*.json
reports/rsfmri/*.md
derivatives/rsfmri_qc/{subject_id}/*.json
derivatives/rsfmri_qc/{subject_id}/*.md
derivatives/rsfmri_metrics/{subject_id}/*.json
derivatives/rsfmri_fc/{subject_id}/*.json
derivatives/rsfmri_fc/{subject_id}/*.tsv
derivatives/rsfmri_confounds/{subject_id}/*.json
derivatives/rsfmri_confounds/{subject_id}/*.tsv
work/dpabi/contracts/*.json
work/gpu/contracts/*.json
work/pipeline_runs/*/summary.json
```

## Outputs

```text
exports/rsfmri_report_package/{export_id}/MANIFEST.json
exports/rsfmri_report_package/{export_id}/README.md
exports/rsfmri_report_package/{export_id}/index.md
exports/rsfmri_report_package/{export_id}/export_summary.json
exports/rsfmri_report_package/{export_id}/summary/*
exports/rsfmri_report_package/{export_id}/subjects/*
exports/rsfmri_report_package/{export_id}/metrics/*
exports/rsfmri_report_package/{export_id}/fc/*
exports/rsfmri_report_package/{export_id}/contracts/*
exports/rsfmri_report_package/{export_id}/pipeline_runs/*
exports/rsfmri_report_package/{export_id}/tables/*
exports/rsfmri_report_package/{export_id}/checksums/SHA256SUMS.txt
exports/rsfmri_report_package/{export_id}.zip
```

## Manifest Requirements

The manifest includes:

- package_id
- export_id
- created_at
- source_roots
- files
- relative_path
- source_path
- size_bytes
- sha256
- category
- safety
- warnings
- errors

## Safety Rules

- Read only from derivatives / reports / work.
- Write only under exports.
- Do not modify rawdata.
- Do not modify source outputs.
- Do not delete files.
- Do not run SPM.
- Do not run MATLAB.
- Do not execute DPABI.
- Do not execute GPU.
- Do not perform statistical inference.
- Do not generate clinical conclusions.
```

---

## 2. 创建 backend/app/tools/report_exporter.py

创建文件：

```text
backend/app/tools/report_exporter.py
```

目标：实现 report package exporter。

提供函数：

```python
export_rsfmri_report_package(
    derivatives_dir: str = "./derivatives",
    reports_dir: str = "./reports",
    work_dir: str = "./work",
    exports_dir: str = "./exports",
    export_id: str | None = None,
    include_subject_qc: bool = True,
    include_metrics: bool = True,
    include_fc: bool = True,
    include_contracts: bool = True,
    include_pipeline_runs: bool = True,
) -> dict

get_latest_rsfmri_report_export(
    exports_dir: str = "./exports",
) -> dict

list_rsfmri_report_exports(
    exports_dir: str = "./exports",
) -> dict
```

实现要求：

1. 不修改 derivatives / reports / work。
2. 只写 exports。
3. export_id 默认：
   - `rsfmri_export_YYYYmmdd_HHMMSS`
4. 扫描并复制以下内容：
   - group summary → `summary/group_summary/`
   - reports/rsfmri top-level summaries → `summary/stage_reports/`
   - subject QC → `subjects/{subject_id}/qc/`
   - metrics JSON → `metrics/{subject_id}/`
   - FC JSON/TSV → `fc/{subject_id}/`
   - confounds JSON/TSV → `subjects/{subject_id}/confounds/`
   - contracts → `contracts/dpabi/` and `contracts/gpu/`
   - pipeline run summaries → `pipeline_runs/`
   - CSV/TSV tables → `tables/`
5. 生成 checksums。
6. 生成 MANIFEST.json。
7. 生成 README.md。
8. 生成 index.md。
9. 生成 export_summary.json。
10. 生成 zip。
11. 如果源文件缺失，不失败；记录 warnings。
12. 如果没有任何可导出文件，也生成 package，但 `ok=false` 并记录 warning。
13. 不把 NIfTI 大文件复制进 report package；只复制 JSON / Markdown / CSV / TSV / TXT。
14. 若发现 `.nii`，只记录在 manifest 的 `excluded_files`，不复制。
15. 只使用 Python 标准库。

参考实现：

```python
from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any


TEXT_EXTENSIONS = {".json", ".md", ".csv", ".tsv", ".txt", ".log", ".yaml", ".yml"}
EXCLUDED_EXTENSIONS = {".nii", ".gz", ".mat"}


def _now_id() -> str:
    return datetime.now().strftime("rsfmri_export_%Y%m%d_%H%M%S")


def _iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _copy_file(source: Path, destination: Path) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return {
        "relative_path": None,
        "source_path": str(source),
        "size_bytes": int(destination.stat().st_size),
        "sha256": _sha256(destination),
    }


def _safe_collect_files(base: Path, patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    if not base.exists():
        return files

    for pattern in patterns:
        files.extend(sorted(base.glob(pattern)))

    out = []
    seen = set()
    for path in files:
        if path.is_file() and path not in seen:
            out.append(path)
            seen.add(path)

    return out


def _discover_subjects(derivatives: Path) -> list[str]:
    subjects = set()
    for base_name in ["rsfmri_qc", "rsfmri_metrics", "rsfmri_fc", "rsfmri_confounds"]:
        base = derivatives / base_name
        if not base.exists():
            continue
        for child in base.iterdir():
            if child.is_dir() and child.name.startswith("sub-"):
                subjects.add(child.name)
    return sorted(subjects)


def _stage_status_summary(group_summary: dict[str, Any] | None) -> str:
    if not group_summary:
        return "Group summary not available."

    lines = []
    counts = group_summary.get("stage_status_counts", {})
    if not isinstance(counts, dict):
        return "Stage status counts not available."

    lines.append("| Stage | PASS | WARNING | FAIL | MISSING | UNKNOWN |")
    lines.append("|---|---:|---:|---:|---:|---:|")

    for stage, item in counts.items():
        item = item or {}
        lines.append(
            f"| {stage} | {item.get('PASS', 0)} | {item.get('WARNING', 0)} | "
            f"{item.get('FAIL', 0)} | {item.get('MISSING', 0)} | {item.get('UNKNOWN', 0)} |"
        )

    return "\n".join(lines)


def _write_readme(path: Path, export_id: str, summary: dict[str, Any]) -> None:
    lines = []
    lines.append(f"# rs-fMRI Report Package: {export_id}")
    lines.append("")
    lines.append("This package contains engineering validation outputs for the synthetic rs-fMRI pipeline.")
    lines.append("")
    lines.append("## Contents")
    lines.append("")
    lines.append("- `MANIFEST.json`: file manifest with checksums")
    lines.append("- `index.md`: human-readable package index")
    lines.append("- `export_summary.json`: exporter summary")
    lines.append("- `summary/`: group and stage-level reports")
    lines.append("- `subjects/`: subject-level QC and confounds summaries")
    lines.append("- `metrics/`: subject metrics result JSON files")
    lines.append("- `fc/`: functional connectivity result files and matrices")
    lines.append("- `contracts/`: DPABI and GPU backend contracts")
    lines.append("- `pipeline_runs/`: pipeline run summaries")
    lines.append("- `tables/`: CSV/TSV tables")
    lines.append("- `checksums/SHA256SUMS.txt`: checksums for exported files")
    lines.append("")
    lines.append("## Safety")
    lines.append("")
    lines.append("This package is generated from synthetic derivative outputs only. It does not include rawdata and does not make clinical conclusions.")
    lines.append("")
    lines.append("## Export Summary")
    lines.append("")
    lines.append(f"- Exported subjects: {summary.get('exported_subjects')}")
    lines.append(f"- Exported files total: {summary.get('exported_files_total')}")
    lines.append(f"- Excluded files total: {summary.get('excluded_files_total')}")
    lines.append(f"- Warning count: {len(summary.get('warnings', []))}")
    lines.append(f"- Error count: {len(summary.get('errors', []))}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_index(path: Path, export_id: str, group_summary: dict[str, Any] | None, export_summary: dict[str, Any]) -> None:
    lines = []
    lines.append(f"# rs-fMRI Dataset Report Index")
    lines.append("")
    lines.append(f"- Export ID: `{export_id}`")
    lines.append(f"- Created at: `{export_summary.get('created_at')}`")
    lines.append(f"- Subjects: {export_summary.get('exported_subjects')}")
    lines.append(f"- Files: {export_summary.get('exported_files_total')}")
    lines.append("")
    lines.append("## Dataset Overview")
    lines.append("")
    if group_summary:
        lines.append(f"- Subjects total: {group_summary.get('subjects_total')}")
        lines.append(f"- Subjects with QC: {group_summary.get('subjects_with_any_qc')}")
        lines.append(f"- Warnings total: {group_summary.get('warnings_total')}")
        lines.append(f"- Errors total: {group_summary.get('errors_total')}")
    else:
        lines.append("Group summary was not available at export time.")

    lines.append("")
    lines.append("## Stage Status Counts")
    lines.append("")
    lines.append(_stage_status_summary(group_summary))
    lines.append("")
    lines.append("## Included High-level Files")
    lines.append("")
    lines.append("- `summary/group_summary/dataset_summary.json`")
    lines.append("- `summary/group_summary/dashboard_data.json`")
    lines.append("- `summary/group_summary/dataset_summary_report.md`")
    lines.append("- `tables/subject_metrics_table.csv`")
    lines.append("- `contracts/`")
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append("- This package is for engineering validation.")
    lines.append("- It is not a clinical report.")
    lines.append("- It does not include rawdata.")
    lines.append("- It does not perform group-level statistical inference.")
    lines.append("- It does not execute SPM, MATLAB, DPABI, or GPU code.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _zip_directory(source_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=str(path.relative_to(source_dir)))


def _register_copied(
    copied_files: list[dict[str, Any]],
    package_dir: Path,
    source: Path,
    destination: Path,
    category: str,
) -> None:
    info = _copy_file(source, destination)
    info["relative_path"] = str(destination.relative_to(package_dir))
    info["category"] = category
    copied_files.append(info)


def export_rsfmri_report_package(
    derivatives_dir: str = "./derivatives",
    reports_dir: str = "./reports",
    work_dir: str = "./work",
    exports_dir: str = "./exports",
    export_id: str | None = None,
    include_subject_qc: bool = True,
    include_metrics: bool = True,
    include_fc: bool = True,
    include_contracts: bool = True,
    include_pipeline_runs: bool = True,
) -> dict[str, Any]:
    derivatives = Path(derivatives_dir)
    reports = Path(reports_dir)
    work = Path(work_dir)
    exports = Path(exports_dir)

    export_id = export_id or _now_id()
    package_root = exports / "rsfmri_report_package"
    package_dir = package_root / export_id
    zip_path = package_root / f"{export_id}.zip"

    package_dir.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    errors: list[str] = []
    copied_files: list[dict[str, Any]] = []
    excluded_files: list[dict[str, Any]] = []

    subjects = _discover_subjects(derivatives)

    # 1. Group summary and stage reports.
    group_base = reports / "rsfmri" / "group_summary"
    group_files = _safe_collect_files(group_base, ["*.json", "*.md", "*.csv"])
    if not group_files:
        warnings.append("No group summary files found. Run Step 47 first.")

    for src in group_files:
        dest = package_dir / "summary" / "group_summary" / src.name
        _register_copied(copied_files, package_dir, src, dest, "group_summary")

        if src.name == "subject_metrics_table.csv":
            table_dest = package_dir / "tables" / "subject_metrics_table.csv"
            _register_copied(copied_files, package_dir, src, table_dest, "table")

    stage_report_files = _safe_collect_files(reports / "rsfmri", ["*.json", "*.md"])
    for src in stage_report_files:
        if "group_summary" in src.parts:
            continue
        dest = package_dir / "summary" / "stage_reports" / src.name
        _register_copied(copied_files, package_dir, src, dest, "stage_report")

    # 2. Subject QC and confounds.
    if include_subject_qc:
        for subject_id in subjects:
            qc_dir = derivatives / "rsfmri_qc" / subject_id
            for src in _safe_collect_files(qc_dir, ["*.json", "*.md"]):
                dest = package_dir / "subjects" / subject_id / "qc" / src.name
                _register_copied(copied_files, package_dir, src, dest, "subject_qc")

            confounds_dir = derivatives / "rsfmri_confounds" / subject_id
            for src in _safe_collect_files(confounds_dir, ["*.json", "*.tsv", "*.csv", "*.md"]):
                dest = package_dir / "subjects" / subject_id / "confounds" / src.name
                _register_copied(copied_files, package_dir, src, dest, "confounds")

    # 3. Metrics.
    if include_metrics:
        for subject_id in subjects:
            metrics_dir = derivatives / "rsfmri_metrics" / subject_id
            for src in _safe_collect_files(metrics_dir, ["*.json", "*.md", "*.tsv", "*.csv"]):
                dest = package_dir / "metrics" / subject_id / src.name
                _register_copied(copied_files, package_dir, src, dest, "metrics")

            for src in sorted(metrics_dir.glob("*")) if metrics_dir.exists() else []:
                if src.is_file() and src.suffix in EXCLUDED_EXTENSIONS:
                    excluded_files.append({
                        "source_path": str(src),
                        "reason": "Large or binary metric image excluded from report package.",
                    })

    # 4. Functional connectivity.
    if include_fc:
        for subject_id in subjects:
            fc_dir = derivatives / "rsfmri_fc" / subject_id
            for src in _safe_collect_files(fc_dir, ["*.json", "*.tsv", "*.csv", "*.md"]):
                dest = package_dir / "fc" / subject_id / src.name
                _register_copied(copied_files, package_dir, src, dest, "functional_connectivity")

            for src in sorted(fc_dir.glob("*")) if fc_dir.exists() else []:
                if src.is_file() and src.suffix in EXCLUDED_EXTENSIONS:
                    excluded_files.append({
                        "source_path": str(src),
                        "reason": "Large or binary FC image excluded from report package.",
                    })

    # 5. Contracts.
    if include_contracts:
        dpabi_contracts = _safe_collect_files(work / "dpabi" / "contracts", ["*.json"])
        gpu_contracts = _safe_collect_files(work / "gpu" / "contracts", ["*.json"])

        if not dpabi_contracts and not gpu_contracts:
            warnings.append("No DPABI/GPU contracts found.")

        for src in dpabi_contracts:
            dest = package_dir / "contracts" / "dpabi" / src.name
            _register_copied(copied_files, package_dir, src, dest, "dpabi_contract")

        for src in gpu_contracts:
            dest = package_dir / "contracts" / "gpu" / src.name
            _register_copied(copied_files, package_dir, src, dest, "gpu_contract")

    # 6. Pipeline runs.
    if include_pipeline_runs:
        run_summaries = sorted((work / "pipeline_runs").glob("*/summary.json")) if (work / "pipeline_runs").exists() else []
        if not run_summaries:
            warnings.append("No pipeline run summaries found.")

        for src in run_summaries[-50:]:
            run_id = src.parent.name
            dest = package_dir / "pipeline_runs" / f"{run_id}_summary.json"
            _register_copied(copied_files, package_dir, src, dest, "pipeline_run")

    # 7. Checksums.
    checksum_dir = package_dir / "checksums"
    checksum_dir.mkdir(parents=True, exist_ok=True)
    checksum_path = checksum_dir / "SHA256SUMS.txt"

    checksum_lines = []
    for item in copied_files:
        checksum_lines.append(f"{item['sha256']}  {item['relative_path']}")
    checksum_path.write_text("\n".join(checksum_lines) + ("\n" if checksum_lines else ""), encoding="utf-8")

    copied_files.append({
        "relative_path": str(checksum_path.relative_to(package_dir)),
        "source_path": None,
        "size_bytes": int(checksum_path.stat().st_size),
        "sha256": _sha256(checksum_path),
        "category": "checksum",
    })

    group_summary = _read_json(package_dir / "summary" / "group_summary" / "dataset_summary.json")

    export_summary = {
        "ok": len(copied_files) > 1,
        "node_id": "rsfmri_report_exporter",
        "backend": "python",
        "export_id": export_id,
        "package_dir": str(package_dir),
        "zip_path": str(zip_path),
        "created_at": _iso_now(),
        "exported_subjects": subjects,
        "exported_subjects_total": len(subjects),
        "exported_files_total": len(copied_files),
        "excluded_files_total": len(excluded_files),
        "warnings": warnings,
        "errors": errors,
    }

    if len(copied_files) <= 1:
        export_summary["ok"] = False
        warnings.append("No source files were exported.")

    # 8. README / index / manifest.
    readme_path = package_dir / "README.md"
    index_path = package_dir / "index.md"
    export_summary_path = package_dir / "export_summary.json"
    manifest_path = package_dir / "MANIFEST.json"

    _write_readme(readme_path, export_id, export_summary)
    _write_index(index_path, export_id, group_summary, export_summary)

    for generated_path, category in [
        (readme_path, "package_readme"),
        (index_path, "package_index"),
    ]:
        copied_files.append({
            "relative_path": str(generated_path.relative_to(package_dir)),
            "source_path": None,
            "size_bytes": int(generated_path.stat().st_size),
            "sha256": _sha256(generated_path),
            "category": category,
        })

    export_summary["exported_files_total"] = len(copied_files) + 2  # includes summary and manifest after write.
    export_summary_path.write_text(json.dumps(export_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    copied_files.append({
        "relative_path": str(export_summary_path.relative_to(package_dir)),
        "source_path": None,
        "size_bytes": int(export_summary_path.stat().st_size),
        "sha256": _sha256(export_summary_path),
        "category": "export_summary",
    })

    manifest = {
        "package_id": export_id,
        "export_id": export_id,
        "created_at": export_summary["created_at"],
        "source_roots": {
            "derivatives": str(derivatives),
            "reports": str(reports),
            "work": str(work),
        },
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
        "files": copied_files,
        "excluded_files": excluded_files,
        "warnings": warnings,
        "errors": errors,
    }

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    copied_files.append({
        "relative_path": str(manifest_path.relative_to(package_dir)),
        "source_path": None,
        "size_bytes": int(manifest_path.stat().st_size),
        "sha256": _sha256(manifest_path),
        "category": "manifest",
    })

    # Refresh manifest with itself included.
    manifest["files"] = copied_files
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # Refresh checksum with generated files included.
    checksum_lines = [f"{item['sha256']}  {item['relative_path']}" for item in copied_files if item["relative_path"] != "checksums/SHA256SUMS.txt"]
    checksum_path.write_text("\n".join(checksum_lines) + ("\n" if checksum_lines else ""), encoding="utf-8")

    _zip_directory(package_dir, zip_path)

    export_summary["zip_size_bytes"] = int(zip_path.stat().st_size) if zip_path.exists() else None
    export_summary["outputs"] = [
        str(package_dir),
        str(zip_path),
        str(manifest_path),
        str(readme_path),
        str(index_path),
        str(export_summary_path),
        str(checksum_path),
    ]

    export_summary_path.write_text(json.dumps(export_summary, ensure_ascii=False, indent=2), encoding="utf-8")

    return export_summary


def _read_export_summary(package_dir: Path) -> dict[str, Any]:
    summary = _read_json(package_dir / "export_summary.json") or {}
    manifest = _read_json(package_dir / "MANIFEST.json")
    index_md = package_dir / "index.md"
    readme_md = package_dir / "README.md"

    return {
        "ok": bool(summary),
        "export_id": package_dir.name,
        "package_dir": str(package_dir),
        "zip_path": str(package_dir.parent / f"{package_dir.name}.zip"),
        "export_summary": summary,
        "manifest": manifest,
        "index_md": index_md.read_text(encoding="utf-8") if index_md.exists() else None,
        "readme_md": readme_md.read_text(encoding="utf-8") if readme_md.exists() else None,
    }


def list_rsfmri_report_exports(
    exports_dir: str = "./exports",
) -> dict[str, Any]:
    package_root = Path(exports_dir) / "rsfmri_report_package"
    packages = []

    if package_root.exists():
        for child in sorted(package_root.iterdir()):
            if child.is_dir():
                summary = _read_json(child / "export_summary.json") or {}
                packages.append({
                    "export_id": child.name,
                    "package_dir": str(child),
                    "zip_path": str(package_root / f"{child.name}.zip"),
                    "created_at": summary.get("created_at"),
                    "ok": summary.get("ok"),
                    "exported_files_total": summary.get("exported_files_total"),
                    "exported_subjects_total": summary.get("exported_subjects_total"),
                })

    return {
        "ok": True,
        "exports_total": len(packages),
        "exports": packages,
    }


def get_latest_rsfmri_report_export(
    exports_dir: str = "./exports",
) -> dict[str, Any]:
    package_root = Path(exports_dir) / "rsfmri_report_package"
    if not package_root.exists():
        return {
            "ok": False,
            "errors": ["No rs-fMRI report exports found."],
            "warnings": [],
        }

    packages = sorted([child for child in package_root.iterdir() if child.is_dir()])
    if not packages:
        return {
            "ok": False,
            "errors": ["No rs-fMRI report exports found."],
            "warnings": [],
        }

    return _read_export_summary(packages[-1])
```

---

## 3. 修改 backend/app/runtime/node_registry.py

新增节点：

```text
rsfmri_report_exporter
```

新增导入：

```python
from backend.app.tools.report_exporter import export_rsfmri_report_package
```

新增 runner：

```python
def run_rsfmri_report_exporter_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = export_rsfmri_report_package(
        derivatives_dir=context.derivatives_dir,
        reports_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
        work_dir=context.work_dir,
        exports_dir=node.params.get("exports_dir", "./exports"),
        export_id=node.params.get("export_id"),
        include_subject_qc=bool(node.params.get("include_subject_qc", True)),
        include_metrics=bool(node.params.get("include_metrics", True)),
        include_fc=bool(node.params.get("include_fc", True)),
        include_contracts=bool(node.params.get("include_contracts", True)),
        include_pipeline_runs=bool(node.params.get("include_pipeline_runs", True)),
    )
    result["node_id"] = node.id
    return result
```

更新 `NODE_REGISTRY`：

```python
"rsfmri_report_exporter": run_rsfmri_report_exporter_node,
```

---

## 4. 创建 examples/pipeline_rsfmri_report_exporter.yaml

创建文件：

```text
examples/pipeline_rsfmri_report_exporter.yaml
```

内容：

```yaml
pipeline_id: rsfmri_report_exporter_pipeline
version: "0.1.0"
modality: rs-fMRI
description: "Export existing synthetic rs-fMRI reports, QC, metrics, contracts, and summaries into a zip report package."

execution:
  stop_on_failure: true
  run_id: "run_rsfmri_report_exporter_001"
  scheduler:
    mode: "local"
    max_workers: 1
    matlab_max_workers: 0

nodes:
  - id: rsfmri_report_exporter
    name: rs-fMRI Report Exporter
    agent: report-runner
    backend: python
    depends_on: []
    inputs:
      - "./derivatives"
      - "./reports"
      - "./work"
    outputs:
      - "./exports/rsfmri_report_package"
    params:
      exports_dir: "./exports"
      export_id: null
      include_subject_qc: true
      include_metrics: true
      include_fc: true
      include_contracts: true
      include_pipeline_runs: true
    parallel_level: project
    gpu_supported: false
    cache: false
```

本 pipeline 不执行任何 SPM / MATLAB / DPABI / GPU。  
它只做 read-only export aggregation，并写入 exports。

---

## 5. 创建 backend/app/tools/run_rsfmri_report_exporter_cli.py

创建文件：

```text
backend/app/tools/run_rsfmri_report_exporter_cli.py
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
    pipeline = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_rsfmri_report_exporter.yaml")

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
class RsfmriReportExportRequest(BaseModel):
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    pipeline_path: str = Field(default="examples/pipeline_rsfmri_report_exporter.yaml")
```

---

## 7. 修改 backend/app/api/routes.py

新增 API：

```text
POST /api/rsfmri/report-export/run
GET  /api/rsfmri/report-export/latest
GET  /api/rsfmri/report-export/list
```

新增导入：

```python
from backend.app.api.models import RsfmriReportExportRequest
from backend.app.runtime.pipeline_executor import run_pipeline
from backend.app.tools.report_exporter import (
    get_latest_rsfmri_report_export,
    list_rsfmri_report_exports,
)
```

新增路由：

```python
@router.post("/api/rsfmri/report-export/run")
def api_run_rsfmri_report_export(
    request: RsfmriReportExportRequest,
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


@router.get("/api/rsfmri/report-export/latest")
def api_get_latest_rsfmri_report_export() -> dict[str, Any]:
    return get_latest_rsfmri_report_export(exports_dir="./exports")


@router.get("/api/rsfmri/report-export/list")
def api_list_rsfmri_report_exports() -> dict[str, Any]:
    return list_rsfmri_report_exports(exports_dir="./exports")
```

注意：本 POST 不需要 approved，因为不执行 SPM / DPABI / GPU，只做只读导出和 exports 写入。

---

## 8. 修改 frontend/src/api.ts

新增：

```ts
export async function runRsfmriReportExport(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/report-export/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getLatestRsfmriReportExport(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/report-export/latest"
  );
}

export async function listRsfmriReportExports(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/report-export/list"
  );
}
```

---

## 9. 创建 frontend/src/components/RsfmriReportExporterPanel.tsx

创建文件：

```text
frontend/src/components/RsfmriReportExporterPanel.tsx
```

内容：

```tsx
import { useState } from "react";
import {
  getLatestRsfmriReportExport,
  listRsfmriReportExports,
  runRsfmriReportExport
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function RsfmriReportExporterPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [latest, setLatest] = useState<Record<string, unknown> | null>(null);
  const [exportsList, setExportsList] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    setStatus("RUNNING");
    setError("");

    try {
      const response = await runRsfmriReportExport(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_report_exporter.yaml"
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
      const response = await getLatestRsfmriReportExport(baseUrl);
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
      const response = await listRsfmriReportExports(baseUrl);
      setExportsList(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const exportSummary = latest?.export_summary as Record<string, unknown> | undefined;
  const manifest = latest?.manifest as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button onClick={handleRun}>
          生成 rs-fMRI Report Package
        </button>
        <button onClick={handleLoadLatest}>加载最新报告包</button>
        <button onClick={handleList}>列出历史报告包</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="metricGrid">
        <div className="metricCard">
          <span>Export ID</span>
          <strong>{String(latest?.export_id ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Subjects</span>
          <strong>{String(exportSummary?.exported_subjects_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Files</span>
          <strong>{String(exportSummary?.exported_files_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>ZIP Size</span>
          <strong>{String(exportSummary?.zip_size_bytes ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Manifest Files</span>
          <strong>
            {Array.isArray(manifest?.files) ? String(manifest.files.length) : "-"}
          </strong>
        </div>
      </div>

      <h3>Run Summary</h3>
      <JsonBlock value={result} emptyText="尚未运行" />

      <h3>Latest Export Summary</h3>
      <JsonBlock value={latest?.export_summary} emptyText="暂无最新 export summary" />

      <h3>Latest Manifest</h3>
      <JsonBlock value={latest?.manifest} emptyText="暂无 manifest" />

      <h3>ZIP Path</h3>
      <JsonBlock value={{ zip_path: latest?.zip_path, package_dir: latest?.package_dir }} emptyText="暂无 zip path" />

      <h3>README</h3>
      <TextViewer
        text={
          typeof latest?.readme_md === "string"
            ? latest.readme_md
            : null
        }
        emptyText="暂无 README"
      />

      <h3>Index</h3>
      <TextViewer
        text={
          typeof latest?.index_md === "string"
            ? latest.index_md
            : null
        }
        emptyText="暂无 index"
      />

      <h3>Export List</h3>
      <JsonBlock value={exportsList} emptyText="暂无 export list" />
    </div>
  );
}
```

---

## 10. 修改 frontend/src/App.tsx

新增导入：

```tsx
import { RsfmriReportExporterPanel } from "./components/RsfmriReportExporterPanel";
```

在 `rs-fMRI Group Dataset Dashboard` 后新增 Section：

```tsx
<Section
  title="rs-fMRI Report Exporter"
  description="把已有 JSON / Markdown / CSV / TSV 工程结果整理成带 manifest 和 checksums 的 ZIP 报告包。"
>
  <RsfmriReportExporterPanel baseUrl={baseUrl} />
</Section>
```

---

## 11. 新增轻量测试

创建文件：

```text
tests/unit/test_report_exporter.py
```

内容：

```python
from __future__ import annotations

import json
import zipfile
from pathlib import Path

from backend.app.tools.report_exporter import (
    export_rsfmri_report_package,
    get_latest_rsfmri_report_export,
    list_rsfmri_report_exports,
)


def test_report_exporter_creates_manifest_and_zip(tmp_path: Path):
    derivatives = tmp_path / "derivatives"
    reports = tmp_path / "reports"
    work = tmp_path / "work"
    exports = tmp_path / "exports"

    sub = "sub-001"

    group_dir = reports / "rsfmri" / "group_summary"
    group_dir.mkdir(parents=True)

    (group_dir / "dataset_summary.json").write_text(
        json.dumps({
            "ok": True,
            "subjects_total": 1,
            "subjects_with_any_qc": 1,
            "warnings_total": 0,
            "errors_total": 0,
            "stage_status_counts": {
                "motion": {"PASS": 1, "WARNING": 0, "FAIL": 0, "MISSING": 0, "UNKNOWN": 0}
            },
        }),
        encoding="utf-8",
    )

    (group_dir / "dataset_summary_report.md").write_text(
        "# Dataset Summary\n",
        encoding="utf-8",
    )

    (group_dir / "subject_metrics_table.csv").write_text(
        "subject_id,motion_status\nsub-001,PASS\n",
        encoding="utf-8",
    )

    qc_dir = derivatives / "rsfmri_qc" / sub
    qc_dir.mkdir(parents=True)
    (qc_dir / "motion_qc.json").write_text(
        json.dumps({
            "ok": True,
            "subject_id": sub,
            "motion_qc_status": "PASS",
        }),
        encoding="utf-8",
    )

    metrics_dir = derivatives / "rsfmri_metrics" / sub
    metrics_dir.mkdir(parents=True)
    (metrics_dir / "alff_falff_result.json").write_text(
        json.dumps({
            "ok": True,
            "subject_id": sub,
        }),
        encoding="utf-8",
    )

    contract_dir = work / "gpu" / "contracts"
    contract_dir.mkdir(parents=True)
    (contract_dir / "gpu_contract.json").write_text(
        json.dumps({
            "ok": True,
            "backend_id": "gpu_candidate_test",
            "status": "CONTRACT_ONLY",
            "execution_allowed": False,
        }),
        encoding="utf-8",
    )

    result = export_rsfmri_report_package(
        derivatives_dir=str(derivatives),
        reports_dir=str(reports),
        work_dir=str(work),
        exports_dir=str(exports),
        export_id="test_export",
    )

    assert result["ok"] is True

    package_dir = exports / "rsfmri_report_package" / "test_export"
    zip_path = exports / "rsfmri_report_package" / "test_export.zip"

    assert (package_dir / "MANIFEST.json").exists()
    assert (package_dir / "README.md").exists()
    assert (package_dir / "index.md").exists()
    assert (package_dir / "export_summary.json").exists()
    assert (package_dir / "checksums" / "SHA256SUMS.txt").exists()
    assert zip_path.exists()

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        assert "MANIFEST.json" in names
        assert "README.md" in names

    latest = get_latest_rsfmri_report_export(exports_dir=str(exports))
    assert latest["ok"] is True
    assert latest["export_id"] == "test_export"

    listing = list_rsfmri_report_exports(exports_dir=str(exports))
    assert listing["ok"] is True
    assert listing["exports_total"] == 1
```

---

## 12. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

```python
call("GET", "/api/rsfmri/report-export/latest")
call("GET", "/api/rsfmri/report-export/list")
```

不要在 smoke test 中调用 POST run，避免改变 exports。

---

## 13. 更新 README.md

追加第四十八步说明：

```markdown
## Step 48: Dataset Report Exporter

This step packages existing synthetic rs-fMRI reports, QC outputs, metrics summaries, backend contracts, and pipeline run summaries into a zip report package.

It supports:

- read-only scan of derivatives / reports / work
- export package directory
- manifest with SHA256 checksums
- README and index Markdown
- export summary JSON
- ZIP package
- backend API visibility
- frontend report exporter panel

It does not execute SPM, MATLAB, DPABI, or GPU code.

### Run

```bash
python -m backend.app.tools.run_rsfmri_report_exporter_cli
```

Expected outputs:

```text
exports/rsfmri_report_package/{export_id}/MANIFEST.json
exports/rsfmri_report_package/{export_id}/README.md
exports/rsfmri_report_package/{export_id}/index.md
exports/rsfmri_report_package/{export_id}/export_summary.json
exports/rsfmri_report_package/{export_id}/checksums/SHA256SUMS.txt
exports/rsfmri_report_package/{export_id}.zip
work/pipeline_runs/run_rsfmri_report_exporter_001/summary.json
```

### API

```bash
curl http://127.0.0.1:8000/api/rsfmri/report-export/latest
curl http://127.0.0.1:8000/api/rsfmri/report-export/list
```

Run export:

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/report-export/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_rsfmri_report_exporter.yaml"
  }'
```

### Frontend

Use:

```text
rs-fMRI Report Exporter
```

### Safety

This step:

- only reads derivatives / reports / work
- writes only under exports
- does not include rawdata
- does not modify derivatives / reports / work
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
specs/dataset_report_exporter_spec.md
backend/app/tools/report_exporter.py
backend/app/runtime/node_registry.py
examples/pipeline_rsfmri_report_exporter.yaml
backend/app/tools/run_rsfmri_report_exporter_cli.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/RsfmriReportExporterPanel.tsx
frontend/src/App.tsx
tests/unit/test_report_exporter.py
backend/app/tools/api_smoke_test.py
README.md
```

运行 report exporter：

```bash
python -m backend.app.tools.run_rsfmri_report_exporter_cli
```

应生成：

```text
exports/rsfmri_report_package/{export_id}/MANIFEST.json
exports/rsfmri_report_package/{export_id}/README.md
exports/rsfmri_report_package/{export_id}/index.md
exports/rsfmri_report_package/{export_id}/export_summary.json
exports/rsfmri_report_package/{export_id}/checksums/SHA256SUMS.txt
exports/rsfmri_report_package/{export_id}.zip
```

MANIFEST.json 必须包含：

```json
{
  "package_id": "rsfmri_export_...",
  "export_id": "rsfmri_export_...",
  "created_at": "...",
  "source_roots": {},
  "safety": {
    "rawdata_included": false,
    "spm_executed": false,
    "matlab_executed": false,
    "dpabi_executed": false,
    "gpu_executed": false
  },
  "files": [],
  "excluded_files": []
}
```

运行测试：

```bash
python -m pytest tests/unit/test_report_exporter.py -q
```

启动后端：

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

测试 API：

```bash
curl http://127.0.0.1:8000/api/rsfmri/report-export/latest
curl http://127.0.0.1:8000/api/rsfmri/report-export/list

curl -X POST http://127.0.0.1:8000/api/rsfmri/report-export/run \
  -H "Content-Type: application/json" \
  -d '{}'
```

启动前端：

```bash
cd frontend
npm run dev
```

页面应该能完成：

1. 显示 rs-fMRI Report Exporter 区域。
2. 可以点击生成 report package。
3. 可以加载最新 report package。
4. 可以列出历史 report package。
5. 显示 export id。
6. 显示 exported subjects。
7. 显示 exported files。
8. 显示 zip size。
9. 显示 manifest file count。
10. 显示 export summary JSON。
11. 显示 manifest JSON。
12. 显示 zip path。
13. 显示 README。
14. 显示 index。
15. 不修改 rawdata。
16. 不运行 SPM / MATLAB。
17. 不运行 DPABI。
18. 不运行 GPU。
19. 不执行统计推断。
20. 不生成临床结论。

---

## 15. 重要限制

本步骤只做 Dataset Report Exporter。

不要实现：

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
3. exporter 如何扫描 derivatives / reports / work
4. 哪些文件会复制进 report package
5. 哪些大文件或二进制文件会被排除
6. MANIFEST.json 如何记录 checksum 和 safety flags
7. README.md 和 index.md 分别用于什么
8. ZIP package 如何生成
9. 前端如何加载 latest/list
10. 为什么本步骤不是 PDF/Word 报告生成
11. 下一步如何实现 Report Package Validator：校验导出包完整性、checksums 和安全声明

```
这一步做了一个可交付的报告打包器。

`report_exporter.py` 只读扫描 derivatives/reports/work 下所有已有的工程产物——group summary、dataset-level report、每个 subject 的 QC JSON/Markdown、metrics result、FC 矩阵 TSV、confounds、DPABI/GPU contracts、pipeline run summaries——把它们按固定目录结构复制到 `exports/rsfmri_report_package/{export_id}/` 下，生成一份 MANIFEST.json（每个文件的 sha256 校验和 + safety flags）、README.md、index.md、export_summary.json、SHA256SUMS.txt，最后打成一个 ZIP。`.nii`/`.gz`/`.mat` 等大二进制文件不复制，只记录在 excluded_files 里。不调 SPM/MATLAB/DPABI/GPU，不需要审批。

这是整个 48 步项目的最后一步，从 rs-fMRI 预处理协议定义到可交付 ZIP 报告包，流程完整闭环。
```
