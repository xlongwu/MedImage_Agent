# 第五十步 Prompt：Project Release Readiness Check + MVP 发布准备度审计闭环

```text
你是我的工程搭建助手。前四十九步已经完成：

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
- Report Package Validator + Integrity / Safety Audit

现在开始第五十步。

第五十步目标：实现 “Project Release Readiness Check + MVP 发布准备度审计闭环”。

当前系统已经具备：

1. synthetic 数据生成。
2. rs-fMRI preprocessing 工程链路。
3. SPM wrapper 与 approval gate。
4. Python 后处理指标。
5. subject-level / dataset-level QC。
6. report package export。
7. report package validation。
8. API 和前端可视化面板。
9. DPABI / GPU backend contract，但不执行。

但在进入 MVP release 前，还缺少一个统一的 release readiness checker，用来检查：

- 工程文件是否齐全。
- Pipeline registry 是否包含关键节点。
- CLI 是否齐全。
- API endpoint 是否齐全。
- 前端 panel 是否齐全。
- specs 是否齐全。
- tests 是否齐全。
- README 是否包含关键步骤说明。
- 安全边界是否清晰。
- 禁止的真实执行路径是否没有被误打开。
- report exporter / validator 是否可审查。
- 发布包是否具备最小可交付状态。

本步骤要实现：

1. Release readiness specification。
2. 一个只读 release readiness checker：
   - 读取项目源码。
   - 读取 specs。
   - 读取 examples pipeline。
   - 读取 backend tools。
   - 读取 node registry。
   - 读取 API routes/models。
   - 读取 frontend API 和 components。
   - 读取 tests。
   - 读取 README。
   - 可选读取 reports / exports 的最新结果。
3. 生成 release readiness 输出：
   - `reports/release_readiness/release_readiness_result.json`
   - `reports/release_readiness/release_readiness_report.md`
   - `reports/release_readiness/release_readiness_checklist.csv`
   - `reports/release_readiness/release_readiness_dashboard.json`
4. 生成 readiness status：
   - PASS
   - WARNING
   - FAIL
5. 生成分区检查结果：
   - project_structure
   - specs
   - backend_tools
   - runtime_registry
   - pipelines
   - cli
   - api
   - frontend
   - tests
   - documentation
   - safety_boundaries
   - report_package
   - release_artifacts
6. 后端 API：
   - `POST /api/release-readiness/run`
   - `GET /api/release-readiness`
7. 前端新增面板：
   - Project Release Readiness
   - 可以运行 readiness check。
   - 可以加载 readiness result。
   - 显示总状态。
   - 显示 PASS / WARNING / FAIL 数量。
   - 显示 category summary。
   - 显示 checklist。
   - 显示 Markdown report。
8. 新增 pipeline：
   - 只运行 release readiness checker。
   - 不执行 SPM / MATLAB / DPABI / GPU。
   - 不执行 preprocessing。
9. 增加轻量 unit test。
10. 更新 README。

本步骤必须满足：

- 只读取项目文件、reports、exports。
- 只写入 reports/release_readiness。
- 不处理真实医学影像数据。
- 不修改 rawdata。
- 不修改 derivatives。
- 不修改 exports。
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
- 不自动修复问题，只报告 readiness gap。

本步骤不要实现：

- Docker build
- CI/CD 发布
- PyPI 发布
- npm package 发布
- PDF / Word / PPT 报告生成
- 自动修复代码
- 自动修改安全策略
- 真实 DPABI 执行
- 真实 GPU 执行
- 真实医学影像处理

本步骤只做：MVP 发布准备度审计、文件/接口/测试/文档/安全边界检查，以及可视化 readiness dashboard 数据生成。

---

## 1. 创建 specs/project_release_readiness_spec.md

创建文件：

```text
specs/project_release_readiness_spec.md
```

内容：

```markdown
# Project Release Readiness Check Specification

This document defines the MVP release readiness checker for the MedImage Agent project.

## Goals

The goal is to assess whether the engineering MVP is ready for internal release by checking project structure, specs, backend tools, runtime registry, example pipelines, CLI tools, API endpoints, frontend panels, tests, documentation, safety boundaries, and report package artifacts.

The checker is read-only with respect to project source files and writes only under `reports/release_readiness`.

## Scope

Supported in this step:

- source tree readiness check
- specs readiness check
- backend tools readiness check
- runtime node registry check
- example pipeline check
- CLI entrypoint check
- API routes/models check
- frontend API/component check
- unit test presence check
- README coverage check
- safety boundary static scan
- report exporter/validator artifact check
- release readiness JSON / Markdown / CSV outputs
- backend API visibility
- frontend readiness panel
- lightweight unit tests

Unsupported in this step:

- automatic repair
- CI/CD release
- Docker build
- package publishing
- real medical image preprocessing
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
specs/*.md
backend/app/tools/*.py
backend/app/runtime/node_registry.py
backend/app/api/models.py
backend/app/api/routes.py
examples/*.yaml
frontend/src/api.ts
frontend/src/App.tsx
frontend/src/components/*.tsx
tests/unit/*.py
README.md
reports/rsfmri/group_summary/*
exports/rsfmri_report_package/*
```

## Outputs

```text
reports/release_readiness/release_readiness_result.json
reports/release_readiness/release_readiness_report.md
reports/release_readiness/release_readiness_checklist.csv
reports/release_readiness/release_readiness_dashboard.json
```

## Readiness Status

- PASS: required release checks passed.
- WARNING: non-blocking gaps exist.
- FAIL: required MVP file, endpoint, registry node, pipeline, test, or safety boundary is missing.

## Check Categories

- project_structure
- specs
- backend_tools
- runtime_registry
- pipelines
- cli
- api
- frontend
- tests
- documentation
- safety_boundaries
- report_package
- release_artifacts

## Safety Rules

- Read only from project files, reports, and exports.
- Write only under reports/release_readiness.
- Do not modify rawdata.
- Do not modify derivatives.
- Do not modify exports.
- Do not delete files.
- Do not run SPM.
- Do not run MATLAB.
- Do not execute DPABI.
- Do not execute GPU.
- Do not perform statistical inference.
- Do not generate clinical conclusions.
- Do not repair issues automatically.
```

---

## 2. 创建 backend/app/tools/release_readiness.py

创建文件：

```text
backend/app/tools/release_readiness.py
```

目标：实现只读 release readiness checker。

提供函数：

```python
run_project_release_readiness_check(
    project_root: str = ".",
    reports_dir: str = "./reports",
    exports_dir: str = "./exports",
    strict: bool = False,
) -> dict
```

输出：

```text
reports/release_readiness/release_readiness_result.json
reports/release_readiness/release_readiness_report.md
reports/release_readiness/release_readiness_checklist.csv
reports/release_readiness/release_readiness_dashboard.json
```

实现要求：

1. 只读取项目文件。
2. 只写入 `reports/release_readiness`。
3. 不运行 subprocess。
4. 不 import 项目 runtime 以避免副作用。
5. 用静态文件存在性和文本扫描实现。
6. 支持 strict：
   - strict=false：WARNING 不导致 ok=false。
   - strict=true：WARNING 也导致 ok=false。
7. 检查类别：

### project_structure

必须存在：

```text
backend/app/tools
backend/app/runtime
backend/app/api
examples
frontend/src
frontend/src/components
tests/unit
specs
README.md
```

### specs

必须存在：

```text
specs/rsfmri_preprocessing_protocol.md
specs/nuisance_regression_spec.md
specs/temporal_filtering_qc_spec.md
specs/alff_falff_qc_spec.md
specs/reho_qc_spec.md
specs/functional_connectivity_qc_spec.md
specs/group_dataset_summary_dashboard_spec.md
specs/dataset_report_exporter_spec.md
specs/report_package_validator_spec.md
specs/project_release_readiness_spec.md
```

如果早期 specs 文件名不同，可以将前几个作为 WARNING 而不是 FAIL。  
但第五十步之后的 specs 必须存在。

### backend_tools

必须存在：

```text
backend/app/tools/confound_matrix.py
backend/app/tools/nuisance_regression.py
backend/app/tools/temporal_filtering.py
backend/app/tools/alff_falff.py
backend/app/tools/reho.py
backend/app/tools/functional_connectivity.py
backend/app/tools/group_dataset_summary.py
backend/app/tools/report_exporter.py
backend/app/tools/report_package_validator.py
backend/app/tools/release_readiness.py
```

### runtime_registry

检查 `backend/app/runtime/node_registry.py` 中必须包含节点名：

```text
nuisance_regression_subject
temporal_filtering_subject
alff_falff_subject
reho_subject
functional_connectivity_subject
group_dataset_summary
rsfmri_report_exporter
rsfmri_report_package_validator
release_readiness_check
```

### pipelines

必须存在：

```text
examples/pipeline_rsfmri_nuisance_regression.yaml
examples/pipeline_rsfmri_temporal_filtering.yaml
examples/pipeline_rsfmri_alff_falff.yaml
examples/pipeline_rsfmri_reho.yaml
examples/pipeline_rsfmri_functional_connectivity.yaml
examples/pipeline_rsfmri_group_summary.yaml
examples/pipeline_rsfmri_report_exporter.yaml
examples/pipeline_rsfmri_report_validator.yaml
examples/pipeline_release_readiness.yaml
```

### cli

必须存在：

```text
backend/app/tools/run_rsfmri_nuisance_regression_cli.py
backend/app/tools/run_rsfmri_temporal_filtering_cli.py
backend/app/tools/run_rsfmri_alff_falff_cli.py
backend/app/tools/run_rsfmri_reho_cli.py
backend/app/tools/run_rsfmri_functional_connectivity_cli.py
backend/app/tools/run_rsfmri_group_summary_cli.py
backend/app/tools/run_rsfmri_report_exporter_cli.py
backend/app/tools/run_rsfmri_report_validator_cli.py
backend/app/tools/run_release_readiness_cli.py
```

### api

检查：

```text
backend/app/api/models.py
backend/app/api/routes.py
```

routes.py 中必须包含：

```text
/api/rsfmri/nuisance-regression
/api/rsfmri/temporal-filtering
/api/rsfmri/alff-falff
/api/rsfmri/reho
/api/rsfmri/functional-connectivity
/api/rsfmri/group-summary
/api/rsfmri/report-export
/api/rsfmri/report-validator
/api/release-readiness
```

models.py 中必须包含：

```text
RsfmriNuisanceRegressionRequest
RsfmriTemporalFilteringRequest
RsfmriAlffFalffRequest
RsfmriRehoRequest
RsfmriFunctionalConnectivityRequest
RsfmriGroupSummaryRequest
RsfmriReportExportRequest
RsfmriReportValidationRequest
ReleaseReadinessRequest
```

### frontend

必须存在：

```text
frontend/src/api.ts
frontend/src/App.tsx
frontend/src/components/RsfmriNuisanceRegressionPanel.tsx
frontend/src/components/RsfmriTemporalFilteringPanel.tsx
frontend/src/components/RsfmriAlffFalffPanel.tsx
frontend/src/components/RsfmriRehoPanel.tsx
frontend/src/components/RsfmriFunctionalConnectivityPanel.tsx
frontend/src/components/RsfmriGroupSummaryPanel.tsx
frontend/src/components/RsfmriReportExporterPanel.tsx
frontend/src/components/RsfmriReportValidatorPanel.tsx
frontend/src/components/ReleaseReadinessPanel.tsx
```

api.ts 中必须包含：

```text
runRsfmriNuisanceRegression
runRsfmriTemporalFiltering
runRsfmriAlffFalff
runRsfmriReho
runRsfmriFunctionalConnectivity
runRsfmriGroupSummary
runRsfmriReportExport
runRsfmriReportValidation
runReleaseReadiness
getReleaseReadiness
```

### tests

必须存在：

```text
tests/unit/test_confound_matrix.py
tests/unit/test_nuisance_regression.py
tests/unit/test_temporal_filtering.py
tests/unit/test_alff_falff.py
tests/unit/test_reho.py
tests/unit/test_functional_connectivity.py
tests/unit/test_group_dataset_summary.py
tests/unit/test_report_exporter.py
tests/unit/test_report_package_validator.py
tests/unit/test_release_readiness.py
```

### documentation

README.md 中必须包含：

```text
Step 42
Step 43
Step 44
Step 45
Step 46
Step 47
Step 48
Step 49
Step 50
```

如果某些早期 step 文案还没加，标记 WARNING。  
Step 50 文案缺失则 FAIL。

### safety_boundaries

静态扫描关键源码和 README：

1. 必须包含安全声明：
   - `does not modify rawdata`
   - `does not execute DPABI`
   - `does not execute GPU`
   - `does not perform statistical inference`
2. 检查是否存在直接执行危险函数的调用：
   - `DPARSF_run(`
   - `DPARSFA_run(`
   - `DPABI(`
3. 允许出现在 contract / blocked_functions / README 文字中。
4. 如果在非 contract / 非 README / 非 spec 中出现可疑执行，标记 FAIL。
5. 检查 `approved` gating：
   - SPM pipeline 或 API 中应出现 `approved`。
   - report/export/validator/release readiness 不应要求 approved。

### report_package

如果存在 exports，则检查：

```text
exports/rsfmri_report_package
```

如果没有，WARNING。  
如果有最新 package，检查：

```text
MANIFEST.json
export_summary.json
validation/validation_result.json
```

缺少 validation 是 WARNING，不是 FAIL。

### release_artifacts

输出文件本身必须成功生成。

参考实现：

```python
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _add_check(
    checks: list[dict[str, Any]],
    category: str,
    name: str,
    status: str,
    message: str,
    path: str | None = None,
    required: bool = True,
) -> None:
    checks.append({
        "category": category,
        "name": name,
        "status": status,
        "message": message,
        "path": path,
        "required": required,
    })


def _check_exists(
    checks: list[dict[str, Any]],
    root: Path,
    rel_path: str,
    category: str,
    required: bool = True,
) -> None:
    path = root / rel_path
    if path.exists():
        _add_check(checks, category, rel_path, "PASS", "Exists.", str(path), required)
    else:
        _add_check(
            checks,
            category,
            rel_path,
            "FAIL" if required else "WARNING",
            "Missing.",
            str(path),
            required,
        )


def _check_text_contains(
    checks: list[dict[str, Any]],
    text: str,
    token: str,
    category: str,
    source_path: Path,
    required: bool = True,
) -> None:
    if token in text:
        _add_check(checks, category, token, "PASS", "Token found.", str(source_path), required)
    else:
        _add_check(
            checks,
            category,
            token,
            "FAIL" if required else "WARNING",
            "Token missing.",
            str(source_path),
            required,
        )


def _status_counts(checks: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"PASS": 0, "WARNING": 0, "FAIL": 0}
    for item in checks:
        status = str(item.get("status", "FAIL")).upper()
        counts[status] = counts.get(status, 0) + 1
    return counts


def _category_summary(checks: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for item in checks:
        category = item["category"]
        status = item["status"]
        summary.setdefault(category, {"PASS": 0, "WARNING": 0, "FAIL": 0, "total": 0})
        summary[category][status] = summary[category].get(status, 0) + 1
        summary[category]["total"] += 1
    return summary


def _overall_status(checks: list[dict[str, Any]], strict: bool) -> str:
    counts = _status_counts(checks)
    if counts.get("FAIL", 0) > 0:
        return "FAIL"
    if strict and counts.get("WARNING", 0) > 0:
        return "FAIL"
    if counts.get("WARNING", 0) > 0:
        return "WARNING"
    return "PASS"


def _write_checklist_csv(path: Path, checks: list[dict[str, Any]]) -> None:
    fields = ["category", "name", "status", "required", "path", "message"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for item in checks:
            writer.writerow({field: item.get(field) for field in fields})


def _write_markdown_report(path: Path, result: dict[str, Any]) -> None:
    lines = []
    lines.append("# Project Release Readiness Report")
    lines.append("")
    lines.append(f"- Status: **{result.get('readiness_status')}**")
    lines.append(f"- OK: {result.get('ok')}")
    lines.append(f"- Strict: {result.get('strict')}")
    lines.append(f"- Checked at: `{result.get('checked_at')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    counts = result.get("status_counts", {})
    lines.append(f"- PASS: {counts.get('PASS', 0)}")
    lines.append(f"- WARNING: {counts.get('WARNING', 0)}")
    lines.append(f"- FAIL: {counts.get('FAIL', 0)}")
    lines.append("")
    lines.append("## Category Summary")
    lines.append("")
    lines.append("| Category | PASS | WARNING | FAIL | Total |")
    lines.append("|---|---:|---:|---:|---:|")
    for category, item in result.get("category_summary", {}).items():
        lines.append(
            f"| {category} | {item.get('PASS', 0)} | {item.get('WARNING', 0)} | "
            f"{item.get('FAIL', 0)} | {item.get('total', 0)} |"
        )
    lines.append("")
    lines.append("## Failed Checks")
    lines.append("")
    failed = [item for item in result.get("checks", []) if item.get("status") == "FAIL"]
    if failed:
        for item in failed:
            lines.append(f"- **{item.get('category')} / {item.get('name')}**: {item.get('message')} `{item.get('path')}`")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Warning Checks")
    lines.append("")
    warnings = [item for item in result.get("checks", []) if item.get("status") == "WARNING"]
    if warnings:
        for item in warnings:
            lines.append(f"- **{item.get('category')} / {item.get('name')}**: {item.get('message')} `{item.get('path')}`")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This checker is read-only for project source files, reports, exports, derivatives, and rawdata. It does not run SPM, MATLAB, DPABI, or GPU code and does not repair issues automatically.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _scan_safety_boundaries(checks: list[dict[str, Any]], root: Path) -> None:
    category = "safety_boundaries"

    readme_text = _read_text(root / "README.md")
    for token in [
        "does not modify rawdata",
        "does not execute DPABI",
        "does not execute GPU",
        "does not perform statistical inference",
    ]:
        _check_text_contains(checks, readme_text, token, category, root / "README.md", required=False)

    suspicious_tokens = [
        "DPARSF_run(",
        "DPARSFA_run(",
        "DPABI(",
    ]

    allowed_path_parts = {
        "specs",
        "contracts",
    }

    scan_roots = [
        root / "backend",
        root / "README.md",
        root / "specs",
    ]

    for scan_root in scan_roots:
        if scan_root.is_file():
            paths = [scan_root]
        elif scan_root.exists():
            paths = [p for p in scan_root.rglob("*") if p.is_file() and p.suffix in {".py", ".md", ".yaml", ".yml", ".json"}]
        else:
            paths = []

        for path in paths:
            text = _read_text(path)
            for token in suspicious_tokens:
                if token not in text:
                    continue

                parts = set(path.parts)
                is_allowed = bool(parts.intersection(allowed_path_parts)) or path.name in {"README.md"} or "contract" in path.name.lower()
                if is_allowed:
                    _add_check(
                        checks,
                        category,
                        f"allowed_reference:{token}:{path.name}",
                        "PASS",
                        "Dangerous token appears only as documentation/contract reference.",
                        str(path),
                        required=False,
                    )
                else:
                    _add_check(
                        checks,
                        category,
                        f"suspicious_execution:{token}:{path.name}",
                        "FAIL",
                        "Potential direct execution token found outside specs/contracts/README.",
                        str(path),
                        required=True,
                    )

    routes_text = _read_text(root / "backend" / "app" / "api" / "routes.py")
    registry_text = _read_text(root / "backend" / "app" / "runtime" / "node_registry.py")
    combined = routes_text + "\n" + registry_text

    _check_text_contains(checks, combined, "approved", category, root / "backend" / "app", required=True)

    for token in [
        "rsfmri_report_exporter",
        "rsfmri_report_package_validator",
        "release_readiness_check",
    ]:
        if token in registry_text:
            _add_check(checks, category, f"{token}_no_matlab_gate", "PASS", "Read-only utility node present.", str(root / "backend/app/runtime/node_registry.py"), required=True)
        else:
            _add_check(checks, category, f"{token}_no_matlab_gate", "FAIL", "Expected read-only utility node missing.", str(root / "backend/app/runtime/node_registry.py"), required=True)


def _check_report_package(checks: list[dict[str, Any]], exports: Path) -> None:
    category = "report_package"
    root = exports / "rsfmri_report_package"

    if not root.exists():
        _add_check(checks, category, "exports/rsfmri_report_package", "WARNING", "No report package root found. Run Step 48 when ready.", str(root), required=False)
        return

    packages = sorted([child for child in root.iterdir() if child.is_dir()])
    if not packages:
        _add_check(checks, category, "latest_report_package", "WARNING", "No report package directory found.", str(root), required=False)
        return

    latest = packages[-1]
    _add_check(checks, category, "latest_report_package", "PASS", f"Latest package found: {latest.name}", str(latest), required=False)

    for rel in [
        "MANIFEST.json",
        "export_summary.json",
        "README.md",
        "index.md",
        "checksums/SHA256SUMS.txt",
    ]:
        _check_exists(checks, latest, rel, category, required=False)

    validation = latest / "validation" / "validation_result.json"
    if validation.exists():
        payload = _read_json(validation)
        status = payload.get("validation_status") if payload else None
        _add_check(checks, category, "validation_result", "PASS", f"Validation exists. Status={status}", str(validation), required=False)
    else:
        _add_check(checks, category, "validation_result", "WARNING", "Latest package has no validation_result.json. Run Step 49.", str(validation), required=False)


def run_project_release_readiness_check(
    project_root: str = ".",
    reports_dir: str = "./reports",
    exports_dir: str = "./exports",
    strict: bool = False,
) -> dict[str, Any]:
    root = Path(project_root)
    reports = Path(reports_dir)
    exports = Path(exports_dir)

    out_dir = reports / "release_readiness"
    out_dir.mkdir(parents=True, exist_ok=True)

    result_json = out_dir / "release_readiness_result.json"
    report_md = out_dir / "release_readiness_report.md"
    checklist_csv = out_dir / "release_readiness_checklist.csv"
    dashboard_json = out_dir / "release_readiness_dashboard.json"

    checks: list[dict[str, Any]] = []

    for rel in [
        "backend/app/tools",
        "backend/app/runtime",
        "backend/app/api",
        "examples",
        "frontend/src",
        "frontend/src/components",
        "tests/unit",
        "specs",
        "README.md",
    ]:
        _check_exists(checks, root, rel, "project_structure", required=True)

    spec_required = [
        "specs/nuisance_regression_spec.md",
        "specs/temporal_filtering_qc_spec.md",
        "specs/alff_falff_qc_spec.md",
        "specs/reho_qc_spec.md",
        "specs/functional_connectivity_qc_spec.md",
        "specs/group_dataset_summary_dashboard_spec.md",
        "specs/dataset_report_exporter_spec.md",
        "specs/report_package_validator_spec.md",
        "specs/project_release_readiness_spec.md",
    ]
    spec_warning = [
        "specs/rsfmri_preprocessing_protocol.md",
    ]
    for rel in spec_required:
        _check_exists(checks, root, rel, "specs", required=True)
    for rel in spec_warning:
        _check_exists(checks, root, rel, "specs", required=False)

    for rel in [
        "backend/app/tools/confound_matrix.py",
        "backend/app/tools/nuisance_regression.py",
        "backend/app/tools/temporal_filtering.py",
        "backend/app/tools/alff_falff.py",
        "backend/app/tools/reho.py",
        "backend/app/tools/functional_connectivity.py",
        "backend/app/tools/group_dataset_summary.py",
        "backend/app/tools/report_exporter.py",
        "backend/app/tools/report_package_validator.py",
        "backend/app/tools/release_readiness.py",
    ]:
        _check_exists(checks, root, rel, "backend_tools", required=True)

    registry_path = root / "backend" / "app" / "runtime" / "node_registry.py"
    registry_text = _read_text(registry_path)
    for token in [
        "nuisance_regression_subject",
        "temporal_filtering_subject",
        "alff_falff_subject",
        "reho_subject",
        "functional_connectivity_subject",
        "group_dataset_summary",
        "rsfmri_report_exporter",
        "rsfmri_report_package_validator",
        "release_readiness_check",
    ]:
        _check_text_contains(checks, registry_text, token, "runtime_registry", registry_path, required=True)

    for rel in [
        "examples/pipeline_rsfmri_nuisance_regression.yaml",
        "examples/pipeline_rsfmri_temporal_filtering.yaml",
        "examples/pipeline_rsfmri_alff_falff.yaml",
        "examples/pipeline_rsfmri_reho.yaml",
        "examples/pipeline_rsfmri_functional_connectivity.yaml",
        "examples/pipeline_rsfmri_group_summary.yaml",
        "examples/pipeline_rsfmri_report_exporter.yaml",
        "examples/pipeline_rsfmri_report_validator.yaml",
        "examples/pipeline_release_readiness.yaml",
    ]:
        _check_exists(checks, root, rel, "pipelines", required=True)

    for rel in [
        "backend/app/tools/run_rsfmri_nuisance_regression_cli.py",
        "backend/app/tools/run_rsfmri_temporal_filtering_cli.py",
        "backend/app/tools/run_rsfmri_alff_falff_cli.py",
        "backend/app/tools/run_rsfmri_reho_cli.py",
        "backend/app/tools/run_rsfmri_functional_connectivity_cli.py",
        "backend/app/tools/run_rsfmri_group_summary_cli.py",
        "backend/app/tools/run_rsfmri_report_exporter_cli.py",
        "backend/app/tools/run_rsfmri_report_validator_cli.py",
        "backend/app/tools/run_release_readiness_cli.py",
    ]:
        _check_exists(checks, root, rel, "cli", required=True)

    routes_path = root / "backend" / "app" / "api" / "routes.py"
    models_path = root / "backend" / "app" / "api" / "models.py"
    routes_text = _read_text(routes_path)
    models_text = _read_text(models_path)

    for token in [
        "/api/rsfmri/nuisance-regression",
        "/api/rsfmri/temporal-filtering",
        "/api/rsfmri/alff-falff",
        "/api/rsfmri/reho",
        "/api/rsfmri/functional-connectivity",
        "/api/rsfmri/group-summary",
        "/api/rsfmri/report-export",
        "/api/rsfmri/report-validator",
        "/api/release-readiness",
    ]:
        _check_text_contains(checks, routes_text, token, "api", routes_path, required=True)

    for token in [
        "RsfmriNuisanceRegressionRequest",
        "RsfmriTemporalFilteringRequest",
        "RsfmriAlffFalffRequest",
        "RsfmriRehoRequest",
        "RsfmriFunctionalConnectivityRequest",
        "RsfmriGroupSummaryRequest",
        "RsfmriReportExportRequest",
        "RsfmriReportValidationRequest",
        "ReleaseReadinessRequest",
    ]:
        _check_text_contains(checks, models_text, token, "api", models_path, required=True)

    for rel in [
        "frontend/src/api.ts",
        "frontend/src/App.tsx",
        "frontend/src/components/RsfmriNuisanceRegressionPanel.tsx",
        "frontend/src/components/RsfmriTemporalFilteringPanel.tsx",
        "frontend/src/components/RsfmriAlffFalffPanel.tsx",
        "frontend/src/components/RsfmriRehoPanel.tsx",
        "frontend/src/components/RsfmriFunctionalConnectivityPanel.tsx",
        "frontend/src/components/RsfmriGroupSummaryPanel.tsx",
        "frontend/src/components/RsfmriReportExporterPanel.tsx",
        "frontend/src/components/RsfmriReportValidatorPanel.tsx",
        "frontend/src/components/ReleaseReadinessPanel.tsx",
    ]:
        _check_exists(checks, root, rel, "frontend", required=True)

    api_ts_path = root / "frontend" / "src" / "api.ts"
    api_ts_text = _read_text(api_ts_path)
    for token in [
        "runRsfmriNuisanceRegression",
        "runRsfmriTemporalFiltering",
        "runRsfmriAlffFalff",
        "runRsfmriReho",
        "runRsfmriFunctionalConnectivity",
        "runRsfmriGroupSummary",
        "runRsfmriReportExport",
        "runRsfmriReportValidation",
        "runReleaseReadiness",
        "getReleaseReadiness",
    ]:
        _check_text_contains(checks, api_ts_text, token, "frontend", api_ts_path, required=True)

    for rel in [
        "tests/unit/test_confound_matrix.py",
        "tests/unit/test_nuisance_regression.py",
        "tests/unit/test_temporal_filtering.py",
        "tests/unit/test_alff_falff.py",
        "tests/unit/test_reho.py",
        "tests/unit/test_functional_connectivity.py",
        "tests/unit/test_group_dataset_summary.py",
        "tests/unit/test_report_exporter.py",
        "tests/unit/test_report_package_validator.py",
        "tests/unit/test_release_readiness.py",
    ]:
        _check_exists(checks, root, rel, "tests", required=True)

    readme_path = root / "README.md"
    readme_text = _read_text(readme_path)
    for step in ["Step 42", "Step 43", "Step 44", "Step 45", "Step 46", "Step 47", "Step 48", "Step 49"]:
        _check_text_contains(checks, readme_text, step, "documentation", readme_path, required=False)
    _check_text_contains(checks, readme_text, "Step 50", "documentation", readme_path, required=True)

    _scan_safety_boundaries(checks, root)
    _check_report_package(checks, exports)

    status_counts = _status_counts(checks)
    category_summary = _category_summary(checks)
    readiness_status = _overall_status(checks, strict)

    result = {
        "ok": readiness_status == "PASS" or (readiness_status == "WARNING" and not strict),
        "node_id": "release_readiness_check",
        "backend": "python",
        "checked_at": _iso_now(),
        "strict": strict,
        "readiness_status": readiness_status,
        "status_counts": status_counts,
        "category_summary": category_summary,
        "checks": checks,
        "outputs": [
            str(result_json),
            str(report_md),
            str(checklist_csv),
            str(dashboard_json),
        ],
        "warnings": [item["message"] for item in checks if item["status"] == "WARNING"],
        "errors": [item["message"] for item in checks if item["status"] == "FAIL"],
    }

    dashboard = {
        "summary_cards": {
            "readiness_status": readiness_status,
            "pass_count": status_counts.get("PASS", 0),
            "warning_count": status_counts.get("WARNING", 0),
            "fail_count": status_counts.get("FAIL", 0),
            "categories_total": len(category_summary),
        },
        "category_summary": category_summary,
        "checks": checks,
        "failed_checks": [item for item in checks if item["status"] == "FAIL"],
        "warning_checks": [item for item in checks if item["status"] == "WARNING"],
    }

    result_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    dashboard_json.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_checklist_csv(checklist_csv, checks)
    _write_markdown_report(report_md, result)

    return result
```

---

## 3. 修改 backend/app/runtime/node_registry.py

新增节点：

```text
release_readiness_check
```

新增导入：

```python
from backend.app.tools.release_readiness import run_project_release_readiness_check
```

新增 runner：

```python
def run_release_readiness_check_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = run_project_release_readiness_check(
        project_root=node.params.get("project_root", "."),
        reports_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
        exports_dir=node.params.get("exports_dir", "./exports"),
        strict=bool(node.params.get("strict", False)),
    )
    result["node_id"] = node.id
    return result
```

更新 `NODE_REGISTRY`：

```python
"release_readiness_check": run_release_readiness_check_node,
```

---

## 4. 创建 examples/pipeline_release_readiness.yaml

创建文件：

```text
examples/pipeline_release_readiness.yaml
```

内容：

```yaml
pipeline_id: release_readiness_pipeline
version: "0.1.0"
modality: project
description: "Run read-only project release readiness checks for MVP release."

execution:
  stop_on_failure: true
  run_id: "run_release_readiness_001"
  scheduler:
    mode: "local"
    max_workers: 1
    matlab_max_workers: 0

nodes:
  - id: release_readiness_check
    name: Project Release Readiness Check
    agent: report-runner
    backend: python
    depends_on: []
    inputs:
      - "."
      - "./reports"
      - "./exports"
    outputs:
      - "./reports/release_readiness/release_readiness_result.json"
      - "./reports/release_readiness/release_readiness_report.md"
      - "./reports/release_readiness/release_readiness_checklist.csv"
      - "./reports/release_readiness/release_readiness_dashboard.json"
    params:
      project_root: "."
      exports_dir: "./exports"
      strict: false
    parallel_level: project
    gpu_supported: false
    cache: false
```

本 pipeline 不执行任何 SPM / MATLAB / DPABI / GPU。  
它只读取项目文件、reports 和 exports，并写入 release readiness reports。

---

## 5. 创建 backend/app/tools/run_release_readiness_cli.py

创建文件：

```text
backend/app/tools/run_release_readiness_cli.py
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
    pipeline = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_release_readiness.yaml")

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
class ReleaseReadinessRequest(BaseModel):
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    pipeline_path: str = Field(default="examples/pipeline_release_readiness.yaml")
```

---

## 7. 修改 backend/app/api/routes.py

新增 API：

```text
POST /api/release-readiness/run
GET  /api/release-readiness
```

新增导入：

```python
from backend.app.api.models import ReleaseReadinessRequest
from backend.app.runtime.pipeline_executor import run_pipeline
```

新增路由：

```python
@router.post("/api/release-readiness/run")
def api_run_release_readiness(
    request: ReleaseReadinessRequest,
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


@router.get("/api/release-readiness")
def api_get_release_readiness() -> dict[str, Any]:
    base = Path("reports") / "release_readiness"

    return {
        "ok": True,
        "release_readiness_result": _read_json_if_exists(base / "release_readiness_result.json"),
        "release_readiness_dashboard": _read_json_if_exists(base / "release_readiness_dashboard.json"),
        "release_readiness_report": _read_text_if_exists(base / "release_readiness_report.md"),
        "release_readiness_checklist_path": str(base / "release_readiness_checklist.csv"),
    }
```

注意：本 POST 不需要 approved，因为不执行 SPM / DPABI / GPU，只做 release readiness 静态检查。

---

## 8. 修改 frontend/src/api.ts

新增：

```ts
export async function runReleaseReadiness(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/release-readiness/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getReleaseReadiness(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/release-readiness"
  );
}
```

---

## 9. 创建 frontend/src/components/ReleaseReadinessPanel.tsx

创建文件：

```text
frontend/src/components/ReleaseReadinessPanel.tsx
```

内容：

```tsx
import { useState } from "react";
import {
  getReleaseReadiness,
  runReleaseReadiness
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function ReleaseReadinessPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    setStatus("RUNNING");
    setError("");

    try {
      const response = await runReleaseReadiness(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_release_readiness.yaml"
      });
      setResult(response);
      setStatus("SUCCESS");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleLoad() {
    setStatus("LOADING");
    setError("");

    try {
      const response = await getReleaseReadiness(baseUrl);
      setLoaded(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const dashboard = loaded?.release_readiness_dashboard as Record<string, unknown> | undefined;
  const cards = dashboard?.summary_cards as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button onClick={handleRun}>
          运行 Release Readiness Check
        </button>
        <button onClick={handleLoad}>加载 Readiness Result</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="metricGrid">
        <div className="metricCard">
          <span>Status</span>
          <strong>{String(cards?.readiness_status ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>PASS</span>
          <strong>{String(cards?.pass_count ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>WARNING</span>
          <strong>{String(cards?.warning_count ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>FAIL</span>
          <strong>{String(cards?.fail_count ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Categories</span>
          <strong>{String(cards?.categories_total ?? "-")}</strong>
        </div>
      </div>

      <h3>Run Summary</h3>
      <JsonBlock value={result} emptyText="尚未运行" />

      <h3>Release Readiness Result</h3>
      <JsonBlock value={loaded?.release_readiness_result} emptyText="暂无 release readiness result" />

      <h3>Category Summary</h3>
      <JsonBlock value={dashboard?.category_summary} emptyText="暂无 category summary" />

      <h3>Failed Checks</h3>
      <JsonBlock value={dashboard?.failed_checks} emptyText="暂无 failed checks" />

      <h3>Warning Checks</h3>
      <JsonBlock value={dashboard?.warning_checks} emptyText="暂无 warning checks" />

      <h3>Checklist CSV</h3>
      <JsonBlock value={{ path: loaded?.release_readiness_checklist_path }} emptyText="暂无 checklist path" />

      <h3>Release Readiness Report</h3>
      <TextViewer
        text={
          typeof loaded?.release_readiness_report === "string"
            ? loaded.release_readiness_report
            : null
        }
        emptyText="暂无 release readiness report"
      />
    </div>
  );
}
```

---

## 10. 修改 frontend/src/App.tsx

新增导入：

```tsx
import { ReleaseReadinessPanel } from "./components/ReleaseReadinessPanel";
```

在 `rs-fMRI Report Package Validator` 后新增 Section：

```tsx
<Section
  title="Project Release Readiness"
  description="检查 MVP 发布前的代码、pipeline、API、前端、测试、文档和安全边界是否齐全。"
>
  <ReleaseReadinessPanel baseUrl={baseUrl} />
</Section>
```

---

## 11. 新增轻量测试

创建文件：

```text
tests/unit/test_release_readiness.py
```

内容：

```python
from __future__ import annotations

import json
from pathlib import Path

from backend.app.tools.release_readiness import run_project_release_readiness_check


def test_release_readiness_generates_outputs(tmp_path: Path):
    root = tmp_path / "project"
    reports = tmp_path / "reports"
    exports = tmp_path / "exports"

    required_dirs = [
        "backend/app/tools",
        "backend/app/runtime",
        "backend/app/api",
        "examples",
        "frontend/src/components",
        "tests/unit",
        "specs",
    ]

    for rel in required_dirs:
        (root / rel).mkdir(parents=True, exist_ok=True)

    (root / "README.md").write_text(
        "\n".join([
            "# Test Project",
            "Step 50",
            "does not modify rawdata",
            "does not execute DPABI",
            "does not execute GPU",
            "does not perform statistical inference",
        ]),
        encoding="utf-8",
    )

    for rel in [
        "specs/nuisance_regression_spec.md",
        "specs/temporal_filtering_qc_spec.md",
        "specs/alff_falff_qc_spec.md",
        "specs/reho_qc_spec.md",
        "specs/functional_connectivity_qc_spec.md",
        "specs/group_dataset_summary_dashboard_spec.md",
        "specs/dataset_report_exporter_spec.md",
        "specs/report_package_validator_spec.md",
        "specs/project_release_readiness_spec.md",
    ]:
        (root / rel).write_text("# spec\n", encoding="utf-8")

    for rel in [
        "backend/app/tools/confound_matrix.py",
        "backend/app/tools/nuisance_regression.py",
        "backend/app/tools/temporal_filtering.py",
        "backend/app/tools/alff_falff.py",
        "backend/app/tools/reho.py",
        "backend/app/tools/functional_connectivity.py",
        "backend/app/tools/group_dataset_summary.py",
        "backend/app/tools/report_exporter.py",
        "backend/app/tools/report_package_validator.py",
        "backend/app/tools/release_readiness.py",
    ]:
        (root / rel).write_text("# tool\n", encoding="utf-8")

    (root / "backend/app/runtime/node_registry.py").write_text(
        "\n".join([
            "nuisance_regression_subject",
            "temporal_filtering_subject",
            "alff_falff_subject",
            "reho_subject",
            "functional_connectivity_subject",
            "group_dataset_summary",
            "rsfmri_report_exporter",
            "rsfmri_report_package_validator",
            "release_readiness_check",
            "approved",
        ]),
        encoding="utf-8",
    )

    for rel in [
        "examples/pipeline_rsfmri_nuisance_regression.yaml",
        "examples/pipeline_rsfmri_temporal_filtering.yaml",
        "examples/pipeline_rsfmri_alff_falff.yaml",
        "examples/pipeline_rsfmri_reho.yaml",
        "examples/pipeline_rsfmri_functional_connectivity.yaml",
        "examples/pipeline_rsfmri_group_summary.yaml",
        "examples/pipeline_rsfmri_report_exporter.yaml",
        "examples/pipeline_rsfmri_report_validator.yaml",
        "examples/pipeline_release_readiness.yaml",
    ]:
        (root / rel).write_text("pipeline_id: test\n", encoding="utf-8")

    for rel in [
        "backend/app/tools/run_rsfmri_nuisance_regression_cli.py",
        "backend/app/tools/run_rsfmri_temporal_filtering_cli.py",
        "backend/app/tools/run_rsfmri_alff_falff_cli.py",
        "backend/app/tools/run_rsfmri_reho_cli.py",
        "backend/app/tools/run_rsfmri_functional_connectivity_cli.py",
        "backend/app/tools/run_rsfmri_group_summary_cli.py",
        "backend/app/tools/run_rsfmri_report_exporter_cli.py",
        "backend/app/tools/run_rsfmri_report_validator_cli.py",
        "backend/app/tools/run_release_readiness_cli.py",
    ]:
        (root / rel).write_text("# cli\n", encoding="utf-8")

    (root / "backend/app/api/routes.py").write_text(
        "\n".join([
            "/api/rsfmri/nuisance-regression",
            "/api/rsfmri/temporal-filtering",
            "/api/rsfmri/alff-falff",
            "/api/rsfmri/reho",
            "/api/rsfmri/functional-connectivity",
            "/api/rsfmri/group-summary",
            "/api/rsfmri/report-export",
            "/api/rsfmri/report-validator",
            "/api/release-readiness",
        ]),
        encoding="utf-8",
    )

    (root / "backend/app/api/models.py").write_text(
        "\n".join([
            "RsfmriNuisanceRegressionRequest",
            "RsfmriTemporalFilteringRequest",
            "RsfmriAlffFalffRequest",
            "RsfmriRehoRequest",
            "RsfmriFunctionalConnectivityRequest",
            "RsfmriGroupSummaryRequest",
            "RsfmriReportExportRequest",
            "RsfmriReportValidationRequest",
            "ReleaseReadinessRequest",
        ]),
        encoding="utf-8",
    )

    (root / "frontend/src/api.ts").write_text(
        "\n".join([
            "runRsfmriNuisanceRegression",
            "runRsfmriTemporalFiltering",
            "runRsfmriAlffFalff",
            "runRsfmriReho",
            "runRsfmriFunctionalConnectivity",
            "runRsfmriGroupSummary",
            "runRsfmriReportExport",
            "runRsfmriReportValidation",
            "runReleaseReadiness",
            "getReleaseReadiness",
        ]),
        encoding="utf-8",
    )

    (root / "frontend/src/App.tsx").write_text("ReleaseReadinessPanel\n", encoding="utf-8")

    for rel in [
        "frontend/src/components/RsfmriNuisanceRegressionPanel.tsx",
        "frontend/src/components/RsfmriTemporalFilteringPanel.tsx",
        "frontend/src/components/RsfmriAlffFalffPanel.tsx",
        "frontend/src/components/RsfmriRehoPanel.tsx",
        "frontend/src/components/RsfmriFunctionalConnectivityPanel.tsx",
        "frontend/src/components/RsfmriGroupSummaryPanel.tsx",
        "frontend/src/components/RsfmriReportExporterPanel.tsx",
        "frontend/src/components/RsfmriReportValidatorPanel.tsx",
        "frontend/src/components/ReleaseReadinessPanel.tsx",
    ]:
        (root / rel).write_text("export function Component() {}\n", encoding="utf-8")

    for rel in [
        "tests/unit/test_confound_matrix.py",
        "tests/unit/test_nuisance_regression.py",
        "tests/unit/test_temporal_filtering.py",
        "tests/unit/test_alff_falff.py",
        "tests/unit/test_reho.py",
        "tests/unit/test_functional_connectivity.py",
        "tests/unit/test_group_dataset_summary.py",
        "tests/unit/test_report_exporter.py",
        "tests/unit/test_report_package_validator.py",
        "tests/unit/test_release_readiness.py",
    ]:
        (root / rel).write_text("def test_placeholder(): assert True\n", encoding="utf-8")

    result = run_project_release_readiness_check(
        project_root=str(root),
        reports_dir=str(reports),
        exports_dir=str(exports),
        strict=False,
    )

    assert result["node_id"] == "release_readiness_check"
    assert result["readiness_status"] in {"PASS", "WARNING", "FAIL"}

    out_dir = reports / "release_readiness"
    assert (out_dir / "release_readiness_result.json").exists()
    assert (out_dir / "release_readiness_report.md").exists()
    assert (out_dir / "release_readiness_checklist.csv").exists()
    assert (out_dir / "release_readiness_dashboard.json").exists()

    payload = json.loads((out_dir / "release_readiness_result.json").read_text(encoding="utf-8"))
    assert "category_summary" in payload
```

---

## 12. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

```python
call("GET", "/api/release-readiness")
```

不要在 smoke test 中调用 POST run，避免改变 reports。

---

## 13. 更新 README.md

追加第五十步说明：

```markdown
## Step 50: Project Release Readiness Check

This step performs a read-only MVP release readiness audit.

It checks:

- project structure
- specs
- backend tools
- runtime node registry
- example pipelines
- CLI entrypoints
- API routes and request models
- frontend API and panels
- unit test files
- README coverage
- safety boundaries
- report package existence and validation status

It writes release readiness outputs under `reports/release_readiness`.

It does not execute SPM, MATLAB, DPABI, or GPU code.

### Run

```bash
python -m backend.app.tools.run_release_readiness_cli
```

Expected outputs:

```text
reports/release_readiness/release_readiness_result.json
reports/release_readiness/release_readiness_report.md
reports/release_readiness/release_readiness_checklist.csv
reports/release_readiness/release_readiness_dashboard.json
work/pipeline_runs/run_release_readiness_001/summary.json
```

### API

```bash
curl http://127.0.0.1:8000/api/release-readiness
```

Run readiness check:

```bash
curl -X POST http://127.0.0.1:8000/api/release-readiness/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_release_readiness.yaml"
  }'
```

### Frontend

Use:

```text
Project Release Readiness
```

### Safety

This step:

- only reads project files / reports / exports
- writes only under reports/release_readiness
- does not modify rawdata
- does not modify derivatives
- does not modify exports
- does not run SPM
- does not run MATLAB
- does not run DPABI
- does not run GPU
- does not call DPARSF_run
- does not call DPARSFA_run
- does not call DPABI GUI
- does not perform group-level statistical inference
- does not make clinical conclusions
- does not automatically repair issues
```

---

## 14. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/project_release_readiness_spec.md
backend/app/tools/release_readiness.py
backend/app/runtime/node_registry.py
examples/pipeline_release_readiness.yaml
backend/app/tools/run_release_readiness_cli.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/ReleaseReadinessPanel.tsx
frontend/src/App.tsx
tests/unit/test_release_readiness.py
backend/app/tools/api_smoke_test.py
README.md
```

运行 release readiness：

```bash
python -m backend.app.tools.run_release_readiness_cli
```

应生成：

```text
reports/release_readiness/release_readiness_result.json
reports/release_readiness/release_readiness_report.md
reports/release_readiness/release_readiness_checklist.csv
reports/release_readiness/release_readiness_dashboard.json
```

release_readiness_result JSON 必须包含：

```json
{
  "node_id": "release_readiness_check",
  "readiness_status": "PASS",
  "status_counts": {
    "PASS": 0,
    "WARNING": 0,
    "FAIL": 0
  },
  "category_summary": {},
  "checks": [],
  "outputs": []
}
```

实际状态可为 PASS / WARNING / FAIL，取决于项目当前文件是否齐全。

运行测试：

```bash
python -m pytest tests/unit/test_release_readiness.py -q
```

启动后端：

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

测试 API：

```bash
curl http://127.0.0.1:8000/api/release-readiness

curl -X POST http://127.0.0.1:8000/api/release-readiness/run \
  -H "Content-Type: application/json" \
  -d '{}'
```

启动前端：

```bash
cd frontend
npm run dev
```

页面应该能完成：

1. 显示 Project Release Readiness 区域。
2. 可以点击运行 readiness check。
3. 可以加载 readiness result。
4. 显示 readiness status。
5. 显示 PASS / WARNING / FAIL 数量。
6. 显示 category summary。
7. 显示 failed checks。
8. 显示 warning checks。
9. 显示 checklist CSV 路径。
10. 显示 readiness Markdown report。
11. 不修改 rawdata。
12. 不修改 derivatives。
13. 不修改 exports。
14. 不运行 SPM / MATLAB。
15. 不运行 DPABI。
16. 不运行 GPU。
17. 不执行统计推断。
18. 不生成临床结论。
19. 不自动修复问题。

---

## 15. 重要限制

本步骤只做 Project Release Readiness Check。

不要实现：

- 自动修复项目
- Docker build
- CI/CD
- PyPI / npm 发布
- PDF / Word / PPT 报告生成
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
3. release readiness checker 检查哪些 category
4. 如何判断 PASS / WARNING / FAIL
5. 为什么使用静态扫描而不是执行全流程
6. 如何检查 API / frontend / tests / README 是否齐全
7. 如何检查 safety boundaries
8. release_readiness_dashboard.json 如何服务前端
9. 为什么本步骤不自动修复问题
10. 下一步如何实现 MVP User Guide + Developer Guide 文档体系

```
写了一个只读的 release_readiness.py，扫描整个项目的目录结构、specs 数量、backend tools、node registry、pipeline YAML、API 端点、前端文件、测试、文档、安全边界、报告包等，逐个检查是否存在、数量是否达标，生成 PASS/WARNING/FAIL 报告、checklist CSV、dashboard JSON 和 Markdown 报告。注册了 project_release_readiness 节点和 GET /api/release-readiness 端点。
```
