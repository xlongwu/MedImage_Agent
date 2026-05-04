# 第四十七步 Prompt：Group-level Dataset Summary + Cross-subject Metrics Dashboard 闭环

```text
你是我的工程搭建助手。前四十六步已经完成：

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

现在开始第四十七步。

第四十七步目标：实现 “Group-level Dataset Summary + Cross-subject Metrics Dashboard 闭环”。

当前系统已经可以完成从 synthetic raw BOLD 到 rs-fMRI 多类指标和 QC 的完整工程链路：

synthetic raw BOLD
→ SPM slice timing correction
→ SPM realignment
→ motion QC
→ SPM coregistration
→ registration QC
→ SPM segmentation
→ tissue QC
→ SPM normalization
→ normalization QC
→ SPM smoothing
→ smoothing QC
→ confound matrix
→ Python nuisance regression
→ nuisance regression QC
→ Python temporal filtering
→ filtering QC
→ Python ALFF/fALFF
→ ALFF/fALFF QC
→ Python ReHo
→ ReHo QC
→ Python Functional Connectivity
→ FC QC

但目前各步骤的 subject-level / dataset-level QC 分散在不同 JSON 和 Markdown 中。  
本步骤要把所有核心 QC、metrics、contracts 和 pipeline run summary 汇总到一个 cross-subject dataset dashboard 中，方便评估整个数据集质量和流程完整性。

本步骤要实现：

1. Group-level dataset summary specification。
2. 一个统一的 cross-subject summary builder：
   - 自动扫描 derivatives / reports / work 下已有 outputs。
   - 汇总每个 subject 的各阶段状态。
   - 汇总每个 subject 的关键 QC metrics。
   - 汇总 dataset-level PASS / WARNING / FAIL 计数。
   - 汇总 missing output / missing QC。
   - 汇总 backend contracts 是否生成。
3. 生成 subject-level wide table：
   - 每行一个 subject。
   - 每列一个 processing stage 的 QC 状态和关键 metrics。
4. 生成 dataset-level JSON：
   - `reports/rsfmri/group_summary/dataset_summary.json`
5. 生成 dataset-level CSV：
   - `reports/rsfmri/group_summary/subject_metrics_table.csv`
6. 生成 dataset-level Markdown report：
   - `reports/rsfmri/group_summary/dataset_summary_report.md`
7. 生成 dashboard-ready JSON：
   - `reports/rsfmri/group_summary/dashboard_data.json`
8. 生成 pipeline completeness graph JSON：
   - subject × stage 完整性矩阵
   - stage order
   - missing outputs
9. 生成 quality overview：
   - status counts
   - warning/error counts
   - mean motion FD
   - tissue volume summaries
   - normalization finite fraction
   - smoothing variance ratio
   - nuisance regression variance ratio
   - filtering retained frequency fraction
   - ALFF / fALFF means
   - ReHo means
   - FC ROI count / empty ROI count
10. 生成 contracts overview：
   - DPABI nuisance/filtering/ALFF/ReHo/FC contracts
   - GPU ALFF/ReHo/FC contracts
   - 均只读检查，不执行 contract。
11. 新增 backend API：
   - `POST /api/rsfmri/group-summary/run`
   - `GET /api/rsfmri/group-summary`
12. 新增 frontend 面板：
   - rs-fMRI Group Dataset Dashboard
   - 显示 summary cards
   - 显示 subject table
   - 显示 stage completeness matrix JSON
   - 显示 warnings/errors
   - 显示 contracts overview
   - 显示 Markdown report
13. 新增 pipeline：
   - 只运行 group summary aggregation，不执行 SPM / DPABI / GPU。
14. 增加轻量 unit test。
15. 更新 README。

本步骤必须满足：

- 只读取 synthetic derivatives / reports / work。
- 不处理真实医学影像数据。
- 不修改 rawdata。
- 不运行 SPM。
- 不运行 MATLAB。
- 不调用 DPABI。
- 不调用 DPARSF_run。
- 不调用 DPARSFA_run。
- 不调用 DPABI GUI。
- 不执行 GPU。
- 不删除文件。
- 不做医学结论。
- 不做真正 group-level statistics / inference。
- 不做病例诊断。
- 不根据 QC 自动排除 subject，只标记建议和状态。

本步骤不要实现：

- group-level statistical testing
- GLM / two-sample t-test / paired t-test
- correction for multiple comparisons
- graph theory metrics
- dynamic FC
- clinical interpretation
- real medical data handling
- Docker / release / CI 等外围功能

本步骤只做：跨 subject 的工程级数据集汇总、完整性检查、QC dashboard 数据生成和前端展示。

---

## 1. 创建 specs/group_dataset_summary_dashboard_spec.md

创建文件：

```text
specs/group_dataset_summary_dashboard_spec.md
```

内容：

```markdown
# Group-level Dataset Summary and Dashboard Specification

This document defines the MVP group-level dataset summary and cross-subject dashboard for rs-fMRI engineering validation.

## Goals

The goal is to aggregate subject-level and dataset-level QC outputs into one dashboard-ready summary.

This step helps users inspect:

- processing completeness
- subject-level QC status
- dataset-level warning/error counts
- cross-subject metric summaries
- missing outputs
- generated backend contracts

## Scope

Supported in this step:

- synthetic derivatives only
- read-only aggregation
- subject metrics table
- dataset summary JSON
- dashboard-ready JSON
- Markdown report
- backend API visibility
- frontend dashboard panel
- lightweight unit tests

Unsupported in this step:

- real medical image preprocessing
- clinical interpretation
- group-level statistical inference
- GLM
- t-tests
- multiple-comparison correction
- automatic subject exclusion
- DPABI execution
- SPM execution
- MATLAB execution
- GPU execution
- rawdata modification
- file deletion

## Inputs

```text
derivatives/rsfmri_qc/{subject_id}/*.json
derivatives/rsfmri_metrics/{subject_id}/*.json
derivatives/rsfmri_fc/{subject_id}/fc_result.json
derivatives/rsfmri_confounds/{subject_id}/confound_qc.json
reports/rsfmri/*_summary.json
work/dpabi/contracts/*.json
work/gpu/contracts/*.json
work/pipeline_runs/*/summary.json
```

## Outputs

```text
reports/rsfmri/group_summary/dataset_summary.json
reports/rsfmri/group_summary/dashboard_data.json
reports/rsfmri/group_summary/subject_metrics_table.csv
reports/rsfmri/group_summary/pipeline_completeness.json
reports/rsfmri/group_summary/contracts_overview.json
reports/rsfmri/group_summary/dataset_summary_report.md
```

## Stage Order

The default stage order is:

1. slice_timing
2. realignment_motion
3. coregistration
4. segmentation
5. normalization
6. smoothing
7. nuisance_regression
8. temporal_filtering
9. alff_falff
10. reho
11. functional_connectivity

## Summary Metrics

The dataset summary includes:

- subjects_total
- subjects_with_any_qc
- stage_status_counts
- subjects_by_stage_status
- missing_stage_qc
- warning_count
- error_count
- mean_fd
- mean_gm_volume_mm3
- mean_wm_volume_mm3
- mean_csf_volume_mm3
- mean_normalization_finite_fraction
- mean_smoothing_variance_ratio
- mean_regression_variance_ratio
- mean_filtering_retained_frequency_fraction
- mean_alff_mean
- mean_falff_mean
- mean_reho_mean
- mean_fc_roi_count
- mean_fc_empty_roi_count

## Safety Rules

- This step is read-only for derivatives/reports/work inputs.
- This step writes only under reports/rsfmri/group_summary.
- Do not modify rawdata.
- Do not delete files.
- Do not run SPM.
- Do not run MATLAB.
- Do not execute DPABI.
- Do not execute GPU.
- Do not perform statistical inference.
- Do not generate clinical conclusions.
```

---

## 2. 创建 backend/app/tools/group_dataset_summary.py

创建文件：

```text
backend/app/tools/group_dataset_summary.py
```

目标：扫描 derivatives / reports / work，生成统一 group summary。

提供函数：

```python
build_group_dataset_summary(
    derivatives_dir: str = "./derivatives",
    reports_dir: str = "./reports",
    work_dir: str = "./work",
) -> dict
```

输出：

```text
reports/rsfmri/group_summary/dataset_summary.json
reports/rsfmri/group_summary/dashboard_data.json
reports/rsfmri/group_summary/subject_metrics_table.csv
reports/rsfmri/group_summary/pipeline_completeness.json
reports/rsfmri/group_summary/contracts_overview.json
reports/rsfmri/group_summary/dataset_summary_report.md
```

实现要求：

1. 自动发现 subjects：
   - `derivatives/rsfmri_qc/*`
   - `derivatives/rsfmri_preproc/*`
   - `derivatives/rsfmri_metrics/*`
   - `derivatives/rsfmri_fc/*`
   - `derivatives/rsfmri_confounds/*`
2. 支持缺失文件，不报错中断。
3. 每个 subject 读取：
   - `motion_qc.json`
   - `registration_qc.json`
   - `tissue_qc.json`
   - `normalization_qc.json`
   - `smoothing_qc.json`
   - `confound_qc.json`
   - `nuisance_regression_qc.json`
   - `temporal_filtering_qc.json`
   - `alff_falff_qc.json`
   - `reho_qc.json`
   - `functional_connectivity_qc.json`
4. 对每个 stage 提取 status：
   - motion: `motion_qc_status` 或 `motion_status`
   - registration: `registration_qc_status`
   - segmentation/tissue: `segmentation_qc_status`
   - normalization: `normalization_qc_status`
   - smoothing: `smoothing_qc_status`
   - confounds: `confound_qc_status` 若没有则根据 ok 推断
   - nuisance: `regression_qc_status`
   - filtering: `filtering_qc_status`
   - alff/falff: `alff_qc_status`
   - reho: `reho_qc_status`
   - fc: `fc_qc_status`
5. 缺失 stage 状态标记为 `MISSING`。
6. 汇总 warning/error：
   - subject-level warning/error 数量
   - dataset-level warning/error 数量
7. 提取 metrics，字段尽量稳定：
   - mean_fd / max_fd / volumes_removed / framewise_displacement_mean
   - gm_volume_mm3 / wm_volume_mm3 / csf_volume_mm3
   - finite_fraction
   - variance_ratio
   - retained_frequency_fraction
   - alff_mean / falff_mean
   - reho_mean / valid_voxel_count
   - roi_count / empty_roi_count / diagonal_mean
8. contracts overview：
   - `work/dpabi/contracts/*.json`
   - `work/gpu/contracts/*.json`
   - 只读取，不执行。
9. pipeline runs overview：
   - `work/pipeline_runs/*/summary.json`
   - 只读取最近若干个 summary。
10. 输出 CSV wide table。
11. 输出 dashboard_data.json，结构适合前端直接展示。
12. 输出 Markdown report。
13. 不读取 rawdata。
14. 不删除文件。

参考实现：

```python
from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import mean
from typing import Any


STAGE_ORDER = [
    "slice_timing",
    "motion",
    "registration",
    "segmentation",
    "normalization",
    "smoothing",
    "confounds",
    "nuisance_regression",
    "temporal_filtering",
    "alff_falff",
    "reho",
    "functional_connectivity",
]

STAGE_FILES = {
    "slice_timing": ("slice_timing_qc.json", ["slice_timing_status", "slice_timing_qc_status"]),
    "motion": ("motion_qc.json", ["motion_qc_status", "motion_status"]),
    "registration": ("registration_qc.json", ["registration_qc_status"]),
    "segmentation": ("tissue_qc.json", ["segmentation_qc_status"]),
    "normalization": ("normalization_qc.json", ["normalization_qc_status"]),
    "smoothing": ("smoothing_qc.json", ["smoothing_qc_status"]),
    "nuisance_regression": ("nuisance_regression_qc.json", ["regression_qc_status"]),
    "temporal_filtering": ("temporal_filtering_qc.json", ["filtering_qc_status"]),
    "alff_falff": ("alff_falff_qc.json", ["alff_qc_status"]),
    "reho": ("reho_qc.json", ["reho_qc_status"]),
    "functional_connectivity": ("functional_connectivity_qc.json", ["fc_qc_status"]),
}


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _mean(values: list[Any]) -> float | None:
    nums = [_safe_float(v) for v in values]
    nums = [v for v in nums if v is not None]
    return float(mean(nums)) if nums else None


def _discover_subjects(derivatives: Path) -> list[str]:
    subjects = set()

    for base_name in [
        "rsfmri_qc",
        "rsfmri_preproc",
        "rsfmri_metrics",
        "rsfmri_fc",
        "rsfmri_confounds",
    ]:
        base = derivatives / base_name
        if not base.exists():
            continue

        for child in base.iterdir():
            if child.is_dir() and child.name.startswith("sub-"):
                subjects.add(child.name)

    return sorted(subjects)


def _status_from_payload(payload: dict[str, Any] | None, keys: list[str]) -> str:
    if not payload:
        return "MISSING"

    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value.upper()

    if payload.get("ok") is True:
        return "PASS"
    if payload.get("ok") is False:
        return "FAIL"

    return "UNKNOWN"


def _warnings_count(payload: dict[str, Any] | None) -> int:
    if not payload:
        return 0
    warnings = payload.get("warnings", [])
    return len(warnings) if isinstance(warnings, list) else 0


def _errors_count(payload: dict[str, Any] | None) -> int:
    if not payload:
        return 0
    errors = payload.get("errors", [])
    return len(errors) if isinstance(errors, list) else 0


def _read_subject_qc(derivatives: Path, subject_id: str) -> dict[str, Any]:
    qc_dir = derivatives / "rsfmri_qc" / subject_id
    confounds_dir = derivatives / "rsfmri_confounds" / subject_id

    payloads: dict[str, Any] = {}

    for stage, (filename, _keys) in STAGE_FILES.items():
        path = qc_dir / filename
        payloads[stage] = {
            "path": str(path),
            "payload": _read_json(path),
        }

    confound_qc = confounds_dir / "confound_qc.json"
    payloads["confounds"] = {
        "path": str(confound_qc),
        "payload": _read_json(confound_qc),
    }

    return payloads


def _extract_subject_row(subject_id: str, payloads: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "subject_id": subject_id,
    }

    status_by_stage: dict[str, str] = {}
    warnings_total = 0
    errors_total = 0

    for stage in STAGE_ORDER:
        if stage == "confounds":
            payload = payloads.get(stage, {}).get("payload")
            status = _status_from_payload(payload, ["confound_qc_status"])
        else:
            _filename, keys = STAGE_FILES.get(stage, ("", []))
            payload = payloads.get(stage, {}).get("payload")
            status = _status_from_payload(payload, keys)

        status_by_stage[stage] = status
        row[f"{stage}_status"] = status
        warnings_total += _warnings_count(payload)
        errors_total += _errors_count(payload)

    row["warnings_total"] = warnings_total
    row["errors_total"] = errors_total

    motion = payloads.get("motion", {}).get("payload") or {}
    segmentation = payloads.get("segmentation", {}).get("payload") or {}
    normalization = payloads.get("normalization", {}).get("payload") or {}
    smoothing = payloads.get("smoothing", {}).get("payload") or {}
    confounds = payloads.get("confounds", {}).get("payload") or {}
    nuisance = payloads.get("nuisance_regression", {}).get("payload") or {}
    filtering = payloads.get("temporal_filtering", {}).get("payload") or {}
    alff = payloads.get("alff_falff", {}).get("payload") or {}
    reho = payloads.get("reho", {}).get("payload") or {}
    fc = payloads.get("functional_connectivity", {}).get("payload") or {}

    # Motion metrics: tolerate multiple field names across previous steps.
    row["mean_fd"] = (
        _safe_float(motion.get("mean_fd"))
        or _safe_float(motion.get("framewise_displacement_mean"))
        or _safe_float(motion.get("fd_mean"))
    )
    row["max_fd"] = (
        _safe_float(motion.get("max_fd"))
        or _safe_float(motion.get("framewise_displacement_max"))
        or _safe_float(motion.get("fd_max"))
    )

    row["gm_volume_mm3"] = _safe_float(segmentation.get("gm_volume_mm3"))
    row["wm_volume_mm3"] = _safe_float(segmentation.get("wm_volume_mm3"))
    row["csf_volume_mm3"] = _safe_float(segmentation.get("csf_volume_mm3"))

    row["normalization_finite_fraction"] = _safe_float(normalization.get("finite_fraction"))
    row["smoothing_variance_ratio"] = _safe_float(smoothing.get("variance_reduction_ratio"))
    row["confound_rows"] = _safe_float((confounds.get("qc") or {}).get("rows"))
    row["confound_columns"] = _safe_float((confounds.get("qc") or {}).get("columns"))
    row["confound_rank"] = _safe_float((confounds.get("qc") or {}).get("rank"))
    row["regression_variance_ratio"] = _safe_float(nuisance.get("variance_ratio"))
    row["filtering_retained_frequency_fraction"] = _safe_float(filtering.get("retained_frequency_fraction"))
    row["filtering_variance_ratio"] = _safe_float(filtering.get("variance_ratio"))
    row["alff_mean"] = _safe_float(alff.get("alff_mean"))
    row["falff_mean"] = _safe_float(alff.get("falff_mean"))
    row["reho_mean"] = _safe_float(reho.get("reho_mean"))
    row["reho_valid_voxel_count"] = _safe_float(reho.get("valid_voxel_count"))
    row["fc_roi_count"] = _safe_float(fc.get("roi_count"))
    row["fc_empty_roi_count"] = _safe_float(fc.get("empty_roi_count"))
    row["fc_diagonal_mean"] = _safe_float(fc.get("diagonal_mean"))

    row["status_by_stage"] = status_by_stage
    return row


def _status_counts(subject_rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}

    for stage in STAGE_ORDER:
        counts = {
            "PASS": 0,
            "WARNING": 0,
            "FAIL": 0,
            "MISSING": 0,
            "UNKNOWN": 0,
        }

        for row in subject_rows:
            status = str(row.get(f"{stage}_status", "UNKNOWN")).upper()
            counts[status] = counts.get(status, 0) + 1

        out[stage] = counts

    return out


def _pipeline_completeness(subject_rows: list[dict[str, Any]]) -> dict[str, Any]:
    matrix = []

    for row in subject_rows:
        stages = []
        for stage in STAGE_ORDER:
            status = str(row.get(f"{stage}_status", "MISSING")).upper()
            stages.append({
                "stage": stage,
                "status": status,
                "complete": status in {"PASS", "WARNING"},
            })

        matrix.append({
            "subject_id": row["subject_id"],
            "stages": stages,
        })

    return {
        "stage_order": STAGE_ORDER,
        "subjects": matrix,
    }


def _collect_contracts(work: Path) -> dict[str, Any]:
    contract_paths = []
    for base in [work / "dpabi" / "contracts", work / "gpu" / "contracts"]:
        if not base.exists():
            continue
        contract_paths.extend(sorted(base.glob("*.json")))

    contracts = []
    for path in contract_paths:
        payload = _read_json(path)
        contracts.append({
            "path": str(path),
            "exists": path.exists(),
            "backend_id": payload.get("backend_id") if payload else None,
            "status": payload.get("status") if payload else None,
            "execution_allowed": payload.get("execution_allowed") if payload else None,
            "gpu_executed": payload.get("gpu_executed") if payload else None,
            "dpabi_executed": (payload.get("safety") or {}).get("dpabi_executed") if payload else None,
            "payload_ok": payload.get("ok") if payload else False,
        })

    return {
        "contracts_total": len(contracts),
        "contracts": contracts,
    }


def _collect_pipeline_runs(work: Path, max_runs: int = 20) -> list[dict[str, Any]]:
    run_paths = sorted((work / "pipeline_runs").glob("*/summary.json"))
    run_paths = run_paths[-max_runs:]

    runs = []
    for path in run_paths:
        payload = _read_json(path)
        if not payload:
            continue

        runs.append({
            "path": str(path),
            "status": payload.get("status"),
            "pipeline_id": payload.get("pipeline_id"),
            "run_id": payload.get("run_id"),
            "started_at": payload.get("started_at"),
            "finished_at": payload.get("finished_at"),
        })

    return runs


def _write_subject_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    base_fields = [
        "subject_id",
        *[f"{stage}_status" for stage in STAGE_ORDER],
        "warnings_total",
        "errors_total",
        "mean_fd",
        "max_fd",
        "gm_volume_mm3",
        "wm_volume_mm3",
        "csf_volume_mm3",
        "normalization_finite_fraction",
        "smoothing_variance_ratio",
        "confound_rows",
        "confound_columns",
        "confound_rank",
        "regression_variance_ratio",
        "filtering_retained_frequency_fraction",
        "filtering_variance_ratio",
        "alff_mean",
        "falff_mean",
        "reho_mean",
        "reho_valid_voxel_count",
        "fc_roi_count",
        "fc_empty_roi_count",
        "fc_diagonal_mean",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=base_fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in base_fields})


def _write_markdown_report(path: Path, summary: dict[str, Any], subject_rows: list[dict[str, Any]]) -> None:
    lines = []
    lines.append("# rs-fMRI Group-level Dataset Summary")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append(f"- Subjects total: {summary.get('subjects_total')}")
    lines.append(f"- Subjects with any QC: {summary.get('subjects_with_any_qc')}")
    lines.append(f"- Total warnings: {summary.get('warnings_total')}")
    lines.append(f"- Total errors: {summary.get('errors_total')}")
    lines.append("")
    lines.append("## Key Cross-subject Metrics")
    lines.append("")
    for key, value in summary.get("metric_means", {}).items():
        lines.append(f"- {key}: {value}")

    lines.append("")
    lines.append("## Stage Status Counts")
    lines.append("")
    lines.append("| Stage | PASS | WARNING | FAIL | MISSING | UNKNOWN |")
    lines.append("|---|---:|---:|---:|---:|---:|")

    for stage, counts in summary.get("stage_status_counts", {}).items():
        lines.append(
            f"| {stage} | {counts.get('PASS', 0)} | {counts.get('WARNING', 0)} | "
            f"{counts.get('FAIL', 0)} | {counts.get('MISSING', 0)} | {counts.get('UNKNOWN', 0)} |"
        )

    lines.append("")
    lines.append("## Subject Table")
    lines.append("")
    lines.append("| Subject | Final FC | ALFF/fALFF | ReHo | Warnings | Errors |")
    lines.append("|---|---|---|---|---:|---:|")

    for row in subject_rows:
        lines.append(
            f"| {row.get('subject_id')} | {row.get('functional_connectivity_status')} | "
            f"{row.get('alff_falff_status')} | {row.get('reho_status')} | "
            f"{row.get('warnings_total')} | {row.get('errors_total')} |"
        )

    lines.append("")
    lines.append("## Contracts")
    lines.append("")
    lines.append(f"- Contracts total: {summary.get('contracts_overview', {}).get('contracts_total')}")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This report aggregates derivative QC outputs only. It does not modify rawdata, execute SPM, execute DPABI, execute GPU code, or perform clinical/statistical inference.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_group_dataset_summary(
    derivatives_dir: str = "./derivatives",
    reports_dir: str = "./reports",
    work_dir: str = "./work",
) -> dict[str, Any]:
    derivatives = Path(derivatives_dir)
    reports = Path(reports_dir)
    work = Path(work_dir)

    out_dir = reports / "rsfmri" / "group_summary"
    out_dir.mkdir(parents=True, exist_ok=True)

    dataset_summary_json = out_dir / "dataset_summary.json"
    dashboard_data_json = out_dir / "dashboard_data.json"
    subject_metrics_csv = out_dir / "subject_metrics_table.csv"
    pipeline_completeness_json = out_dir / "pipeline_completeness.json"
    contracts_overview_json = out_dir / "contracts_overview.json"
    report_md = out_dir / "dataset_summary_report.md"

    subjects = _discover_subjects(derivatives)

    subject_rows = []
    subject_payloads = {}

    for subject_id in subjects:
        payloads = _read_subject_qc(derivatives, subject_id)
        subject_payloads[subject_id] = payloads
        subject_rows.append(_extract_subject_row(subject_id, payloads))

    stage_counts = _status_counts(subject_rows)
    completeness = _pipeline_completeness(subject_rows)
    contracts = _collect_contracts(work)
    pipeline_runs = _collect_pipeline_runs(work)

    metric_means = {
        "mean_fd": _mean([row.get("mean_fd") for row in subject_rows]),
        "max_fd": _mean([row.get("max_fd") for row in subject_rows]),
        "gm_volume_mm3": _mean([row.get("gm_volume_mm3") for row in subject_rows]),
        "wm_volume_mm3": _mean([row.get("wm_volume_mm3") for row in subject_rows]),
        "csf_volume_mm3": _mean([row.get("csf_volume_mm3") for row in subject_rows]),
        "normalization_finite_fraction": _mean([row.get("normalization_finite_fraction") for row in subject_rows]),
        "smoothing_variance_ratio": _mean([row.get("smoothing_variance_ratio") for row in subject_rows]),
        "regression_variance_ratio": _mean([row.get("regression_variance_ratio") for row in subject_rows]),
        "filtering_retained_frequency_fraction": _mean([row.get("filtering_retained_frequency_fraction") for row in subject_rows]),
        "filtering_variance_ratio": _mean([row.get("filtering_variance_ratio") for row in subject_rows]),
        "alff_mean": _mean([row.get("alff_mean") for row in subject_rows]),
        "falff_mean": _mean([row.get("falff_mean") for row in subject_rows]),
        "reho_mean": _mean([row.get("reho_mean") for row in subject_rows]),
        "reho_valid_voxel_count": _mean([row.get("reho_valid_voxel_count") for row in subject_rows]),
        "fc_roi_count": _mean([row.get("fc_roi_count") for row in subject_rows]),
        "fc_empty_roi_count": _mean([row.get("fc_empty_roi_count") for row in subject_rows]),
        "fc_diagonal_mean": _mean([row.get("fc_diagonal_mean") for row in subject_rows]),
    }

    warnings_total = int(sum(int(row.get("warnings_total", 0) or 0) for row in subject_rows))
    errors_total = int(sum(int(row.get("errors_total", 0) or 0) for row in subject_rows))

    subjects_with_any_qc = 0
    for row in subject_rows:
        if any(str(row.get(f"{stage}_status")) != "MISSING" for stage in STAGE_ORDER):
            subjects_with_any_qc += 1

    summary = {
        "ok": True,
        "node_id": "group_dataset_summary",
        "backend": "python",
        "subjects_total": len(subjects),
        "subjects_with_any_qc": subjects_with_any_qc,
        "stage_order": STAGE_ORDER,
        "stage_status_counts": stage_counts,
        "warnings_total": warnings_total,
        "errors_total": errors_total,
        "metric_means": metric_means,
        "contracts_overview": contracts,
        "pipeline_runs": pipeline_runs,
        "outputs": [
            str(dataset_summary_json),
            str(dashboard_data_json),
            str(subject_metrics_csv),
            str(pipeline_completeness_json),
            str(contracts_overview_json),
            str(report_md),
        ],
        "warnings": [],
        "errors": [],
    }

    dashboard = {
        "summary_cards": {
            "subjects_total": len(subjects),
            "subjects_with_any_qc": subjects_with_any_qc,
            "warnings_total": warnings_total,
            "errors_total": errors_total,
            "contracts_total": contracts.get("contracts_total"),
        },
        "stage_order": STAGE_ORDER,
        "stage_status_counts": stage_counts,
        "metric_means": metric_means,
        "subject_rows": subject_rows,
        "pipeline_completeness": completeness,
        "contracts_overview": contracts,
        "pipeline_runs": pipeline_runs,
    }

    dataset_summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    dashboard_data_json.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")
    pipeline_completeness_json.write_text(json.dumps(completeness, ensure_ascii=False, indent=2), encoding="utf-8")
    contracts_overview_json.write_text(json.dumps(contracts, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_subject_csv(subject_metrics_csv, subject_rows)
    _write_markdown_report(report_md, summary, subject_rows)

    return summary
```

---

## 3. 修改 backend/app/runtime/node_registry.py

新增节点：

```text
group_dataset_summary
```

新增导入：

```python
from backend.app.tools.group_dataset_summary import build_group_dataset_summary
```

新增 runner：

```python
def run_group_dataset_summary_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = build_group_dataset_summary(
        derivatives_dir=context.derivatives_dir,
        reports_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
        work_dir=context.work_dir,
    )
    result["node_id"] = node.id
    return result
```

更新 `NODE_REGISTRY`：

```python
"group_dataset_summary": run_group_dataset_summary_node,
```

---

## 4. 创建 examples/pipeline_rsfmri_group_summary.yaml

创建文件：

```text
examples/pipeline_rsfmri_group_summary.yaml
```

内容：

```yaml
pipeline_id: rsfmri_group_summary_pipeline
version: "0.1.0"
modality: rs-fMRI
description: "Aggregate subject-level QC, metrics, contracts, and pipeline summaries into a group-level dataset dashboard."

execution:
  stop_on_failure: true
  run_id: "run_rsfmri_group_summary_001"
  scheduler:
    mode: "local"
    max_workers: 1
    matlab_max_workers: 0

nodes:
  - id: group_dataset_summary
    name: Group-level Dataset Summary
    agent: report-runner
    backend: python
    depends_on: []
    inputs:
      - "./derivatives"
      - "./reports"
      - "./work"
    outputs:
      - "./reports/rsfmri/group_summary/dataset_summary.json"
      - "./reports/rsfmri/group_summary/dashboard_data.json"
      - "./reports/rsfmri/group_summary/subject_metrics_table.csv"
      - "./reports/rsfmri/group_summary/pipeline_completeness.json"
      - "./reports/rsfmri/group_summary/contracts_overview.json"
      - "./reports/rsfmri/group_summary/dataset_summary_report.md"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false
```

本 pipeline 不执行任何 SPM / MATLAB / DPABI / GPU。  
它只做 group-level read-only aggregation。

---

## 5. 创建 backend/app/tools/run_rsfmri_group_summary_cli.py

创建文件：

```text
backend/app/tools/run_rsfmri_group_summary_cli.py
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
    pipeline = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_rsfmri_group_summary.yaml")

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
class RsfmriGroupSummaryRequest(BaseModel):
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    pipeline_path: str = Field(default="examples/pipeline_rsfmri_group_summary.yaml")
```

---

## 7. 修改 backend/app/api/routes.py

新增 API：

```text
POST /api/rsfmri/group-summary/run
GET  /api/rsfmri/group-summary
```

新增导入：

```python
from backend.app.api.models import RsfmriGroupSummaryRequest
from backend.app.runtime.pipeline_executor import run_pipeline
```

新增路由：

```python
@router.post("/api/rsfmri/group-summary/run")
def api_run_rsfmri_group_summary(
    request: RsfmriGroupSummaryRequest,
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


@router.get("/api/rsfmri/group-summary")
def api_get_rsfmri_group_summary() -> dict[str, Any]:
    group_base = Path("reports") / "rsfmri" / "group_summary"

    return {
        "ok": True,
        "dataset_summary": _read_json_if_exists(group_base / "dataset_summary.json"),
        "dashboard_data": _read_json_if_exists(group_base / "dashboard_data.json"),
        "pipeline_completeness": _read_json_if_exists(group_base / "pipeline_completeness.json"),
        "contracts_overview": _read_json_if_exists(group_base / "contracts_overview.json"),
        "dataset_summary_report": _read_text_if_exists(group_base / "dataset_summary_report.md"),
        "subject_metrics_table_path": str(group_base / "subject_metrics_table.csv"),
    }
```

注意：本 POST 不需要 approved，因为不执行 SPM / DPABI / GPU，只做只读聚合。

---

## 8. 修改 frontend/src/api.ts

新增：

```ts
export async function runRsfmriGroupSummary(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/group-summary/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getRsfmriGroupSummary(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/group-summary"
  );
}
```

---

## 9. 创建 frontend/src/components/RsfmriGroupSummaryPanel.tsx

创建文件：

```text
frontend/src/components/RsfmriGroupSummaryPanel.tsx
```

内容：

```tsx
import { useState } from "react";
import {
  getRsfmriGroupSummary,
  runRsfmriGroupSummary
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

function renderMetric(value: unknown, digits = 4) {
  if (value === null || value === undefined) return "-";
  const num = Number(value);
  if (!Number.isFinite(num)) return String(value);
  return num.toFixed(digits);
}

export function RsfmriGroupSummaryPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    setStatus("RUNNING");
    setError("");

    try {
      const response = await runRsfmriGroupSummary(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_group_summary.yaml"
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
      const response = await getRsfmriGroupSummary(baseUrl);
      setLoaded(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const dashboard = loaded?.dashboard_data as Record<string, unknown> | undefined;
  const cards = dashboard?.summary_cards as Record<string, unknown> | undefined;
  const metricMeans = dashboard?.metric_means as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button onClick={handleRun}>
          生成 Group Dataset Summary
        </button>
        <button onClick={handleLoad}>加载 Group Dashboard</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="metricGrid">
        <div className="metricCard">
          <span>Subjects</span>
          <strong>{String(cards?.subjects_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Subjects with QC</span>
          <strong>{String(cards?.subjects_with_any_qc ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Warnings</span>
          <strong>{String(cards?.warnings_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Errors</span>
          <strong>{String(cards?.errors_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Contracts</span>
          <strong>{String(cards?.contracts_total ?? "-")}</strong>
        </div>
      </div>

      <div className="metricGrid">
        <div className="metricCard">
          <span>Mean FD</span>
          <strong>{renderMetric(metricMeans?.mean_fd)}</strong>
        </div>
        <div className="metricCard">
          <span>Mean fALFF</span>
          <strong>{renderMetric(metricMeans?.falff_mean)}</strong>
        </div>
        <div className="metricCard">
          <span>Mean ReHo</span>
          <strong>{renderMetric(metricMeans?.reho_mean)}</strong>
        </div>
        <div className="metricCard">
          <span>Mean FC ROI Count</span>
          <strong>{renderMetric(metricMeans?.fc_roi_count, 2)}</strong>
        </div>
      </div>

      <h3>Run Summary</h3>
      <JsonBlock value={result} emptyText="尚未运行" />

      <h3>Dataset Summary</h3>
      <JsonBlock value={loaded?.dataset_summary} emptyText="暂无 dataset summary" />

      <h3>Dashboard Data</h3>
      <JsonBlock value={loaded?.dashboard_data} emptyText="暂无 dashboard data" />

      <h3>Pipeline Completeness</h3>
      <JsonBlock value={loaded?.pipeline_completeness} emptyText="暂无 pipeline completeness" />

      <h3>Contracts Overview</h3>
      <JsonBlock value={loaded?.contracts_overview} emptyText="暂无 contracts overview" />

      <h3>Subject Metrics CSV</h3>
      <JsonBlock value={{ path: loaded?.subject_metrics_table_path }} emptyText="暂无 subject metrics table" />

      <h3>Dataset Summary Report</h3>
      <TextViewer
        text={
          typeof loaded?.dataset_summary_report === "string"
            ? loaded.dataset_summary_report
            : null
        }
        emptyText="暂无 dataset summary report"
      />
    </div>
  );
}
```

---

## 10. 修改 frontend/src/App.tsx

新增导入：

```tsx
import { RsfmriGroupSummaryPanel } from "./components/RsfmriGroupSummaryPanel";
```

在 `rs-fMRI Functional Connectivity` 后新增 Section：

```tsx
<Section
  title="rs-fMRI Group Dataset Dashboard"
  description="聚合所有 subject-level QC、metrics、pipeline runs 和 backend contracts，生成跨 subject 数据集质量总览。"
>
  <RsfmriGroupSummaryPanel baseUrl={baseUrl} />
</Section>
```

---

## 11. 新增轻量测试

创建文件：

```text
tests/unit/test_group_dataset_summary.py
```

内容：

```python
from __future__ import annotations

import json
from pathlib import Path

from backend.app.tools.group_dataset_summary import build_group_dataset_summary


def test_group_dataset_summary_aggregates_subject_qc(tmp_path: Path):
    derivatives = tmp_path / "derivatives"
    reports = tmp_path / "reports"
    work = tmp_path / "work"

    sub = "sub-001"
    qc_dir = derivatives / "rsfmri_qc" / sub
    metrics_dir = derivatives / "rsfmri_metrics" / sub
    fc_dir = derivatives / "rsfmri_fc" / sub
    confounds_dir = derivatives / "rsfmri_confounds" / sub

    qc_dir.mkdir(parents=True)
    metrics_dir.mkdir(parents=True)
    fc_dir.mkdir(parents=True)
    confounds_dir.mkdir(parents=True)

    (qc_dir / "motion_qc.json").write_text(
        json.dumps({
            "ok": True,
            "subject_id": sub,
            "motion_qc_status": "PASS",
            "mean_fd": 0.1,
            "max_fd": 0.2,
            "warnings": [],
            "errors": [],
        }),
        encoding="utf-8",
    )

    (qc_dir / "alff_falff_qc.json").write_text(
        json.dumps({
            "ok": True,
            "subject_id": sub,
            "alff_qc_status": "PASS",
            "alff_mean": 1.2,
            "falff_mean": 0.4,
            "warnings": [],
            "errors": [],
        }),
        encoding="utf-8",
    )

    (qc_dir / "reho_qc.json").write_text(
        json.dumps({
            "ok": True,
            "subject_id": sub,
            "reho_qc_status": "PASS",
            "reho_mean": 0.8,
            "valid_voxel_count": 27,
            "warnings": [],
            "errors": [],
        }),
        encoding="utf-8",
    )

    (qc_dir / "functional_connectivity_qc.json").write_text(
        json.dumps({
            "ok": True,
            "subject_id": sub,
            "fc_qc_status": "PASS",
            "roi_count": 4,
            "empty_roi_count": 0,
            "diagonal_mean": 1.0,
            "warnings": [],
            "errors": [],
        }),
        encoding="utf-8",
    )

    (work / "gpu" / "contracts").mkdir(parents=True)
    (work / "gpu" / "contracts" / "test_contract.json").write_text(
        json.dumps({
            "ok": True,
            "backend_id": "gpu_candidate_test",
            "status": "CONTRACT_ONLY",
            "execution_allowed": False,
            "gpu_executed": False,
        }),
        encoding="utf-8",
    )

    result = build_group_dataset_summary(
        derivatives_dir=str(derivatives),
        reports_dir=str(reports),
        work_dir=str(work),
    )

    assert result["ok"] is True
    assert result["subjects_total"] == 1
    assert result["metric_means"]["mean_fd"] == 0.1
    assert result["metric_means"]["falff_mean"] == 0.4
    assert result["metric_means"]["reho_mean"] == 0.8
    assert result["metric_means"]["fc_roi_count"] == 4.0

    group_dir = reports / "rsfmri" / "group_summary"
    assert (group_dir / "dataset_summary.json").exists()
    assert (group_dir / "dashboard_data.json").exists()
    assert (group_dir / "subject_metrics_table.csv").exists()
    assert (group_dir / "dataset_summary_report.md").exists()

    dashboard = json.loads((group_dir / "dashboard_data.json").read_text(encoding="utf-8"))
    assert dashboard["summary_cards"]["subjects_total"] == 1
```

---

## 12. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

```python
call("GET", "/api/rsfmri/group-summary")
```

可以不在 smoke test 中调用 POST run，避免改变已有 reports；如果已有 smoke test 已经包含只读 GET 为主，保持只读即可。

---

## 13. 更新 README.md

追加第四十七步说明：

```markdown
## Step 47: Group-level Dataset Summary and Cross-subject Dashboard

This step aggregates all subject-level QC, metrics, backend contracts, and pipeline run summaries into a group-level dataset dashboard.

It supports:

- read-only aggregation from derivatives / reports / work
- subject-level wide metrics table
- dataset summary JSON
- dashboard-ready JSON
- pipeline completeness matrix
- contracts overview
- Markdown dataset summary report
- frontend dashboard visualization

It does not execute SPM, MATLAB, DPABI, or GPU code.

### Run

```bash
python -m backend.app.tools.run_rsfmri_group_summary_cli
```

Expected outputs:

```text
reports/rsfmri/group_summary/dataset_summary.json
reports/rsfmri/group_summary/dashboard_data.json
reports/rsfmri/group_summary/subject_metrics_table.csv
reports/rsfmri/group_summary/pipeline_completeness.json
reports/rsfmri/group_summary/contracts_overview.json
reports/rsfmri/group_summary/dataset_summary_report.md
work/pipeline_runs/run_rsfmri_group_summary_001/summary.json
```

### API

```bash
curl http://127.0.0.1:8000/api/rsfmri/group-summary
```

Run aggregation:

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/group-summary/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_rsfmri_group_summary.yaml"
  }'
```

### Frontend

Use:

```text
rs-fMRI Group Dataset Dashboard
```

### Safety

This step:

- only reads derivatives / reports / work
- writes only group summary reports
- does not modify rawdata
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
specs/group_dataset_summary_dashboard_spec.md
backend/app/tools/group_dataset_summary.py
backend/app/runtime/node_registry.py
examples/pipeline_rsfmri_group_summary.yaml
backend/app/tools/run_rsfmri_group_summary_cli.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/RsfmriGroupSummaryPanel.tsx
frontend/src/App.tsx
tests/unit/test_group_dataset_summary.py
backend/app/tools/api_smoke_test.py
README.md
```

运行 group summary：

```bash
python -m backend.app.tools.run_rsfmri_group_summary_cli
```

应生成：

```text
reports/rsfmri/group_summary/dataset_summary.json
reports/rsfmri/group_summary/dashboard_data.json
reports/rsfmri/group_summary/subject_metrics_table.csv
reports/rsfmri/group_summary/pipeline_completeness.json
reports/rsfmri/group_summary/contracts_overview.json
reports/rsfmri/group_summary/dataset_summary_report.md
```

dataset_summary JSON 必须包含：

```json
{
  "node_id": "group_dataset_summary",
  "subjects_total": 0,
  "stage_order": [],
  "stage_status_counts": {},
  "metric_means": {},
  "contracts_overview": {},
  "outputs": []
}
```

实际数值根据已有 synthetic derivatives / reports / work outputs 决定。

运行测试：

```bash
python -m pytest tests/unit/test_group_dataset_summary.py -q
```

启动后端：

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

测试 API：

```bash
curl http://127.0.0.1:8000/api/rsfmri/group-summary

curl -X POST http://127.0.0.1:8000/api/rsfmri/group-summary/run \
  -H "Content-Type: application/json" \
  -d '{}'
```

启动前端：

```bash
cd frontend
npm run dev
```

页面应该能完成：

1. 显示 rs-fMRI Group Dataset Dashboard 区域。
2. 可以点击生成 Group Dataset Summary。
3. 可以加载 group dashboard。
4. 显示 subject 数量。
5. 显示 subjects with QC。
6. 显示 warning / error 总数。
7. 显示 contracts 总数。
8. 显示 mean FD。
9. 显示 mean fALFF。
10. 显示 mean ReHo。
11. 显示 mean FC ROI count。
12. 显示 dataset summary JSON。
13. 显示 dashboard data JSON。
14. 显示 pipeline completeness JSON。
15. 显示 contracts overview JSON。
16. 显示 subject metrics CSV 路径。
17. 显示 dataset summary Markdown report。
18. 不修改 rawdata。
19. 不运行 SPM / MATLAB。
20. 不运行 DPABI。
21. 不运行 GPU。
22. 不执行 group-level statistical inference。

---

## 15. 重要限制

本步骤只做 group-level engineering summary 和 dashboard。

不要实现：

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
3. group summary 如何发现 subjects
4. 如何汇总各 stage QC status
5. subject_metrics_table.csv 包含哪些核心字段
6. pipeline_completeness.json 如何表达 stage 完整性
7. contracts_overview.json 如何检查 DPABI/GPU contract
8. dashboard_data.json 如何服务前端
9. 为什么本步骤不是 group-level statistics
10. 下一步如何实现 Dataset Report Exporter：把 Markdown / JSON / CSV 打包成可交付报告包

```
这一步把分散在各处的 subject-level QC、metrics、contracts 和 pipeline run 汇总到了一个统一的 group-level dashboard。

**写了一个只读的 group summary builder。** `group_dataset_summary.py` 自动扫描 `derivatives/rsfmri_qc/*/`、`rsfmri_metrics/*/`、`rsfmri_fc/*/`、`rsfmri_confounds/*/` 发现所有 subject，读每个 subject 的 12 个 stage QC JSON，从每个 stage 提取 status（PASS/WARNING/FAIL/MISSING）、提取关键指标（mean_fd、GM/WM/CSF 体积、finite fraction、variance ratio、ALFF/fALFF/ReHo/FC 均值等），汇总成一份 wide table CSV、一份 dataset summary JSON、一份 dashboard JSON、一份 pipeline completeness matrix（subject × stage）、一份 contracts overview 和一份 Markdown 报告。

**不需要审批就能运行。** 这一步不调 SPM、不调 MATLAB、不运行 DPABI、不执行 GPU，纯读现有的 derivatives/reports/work 文件，把结果写到 `reports/rsfmri/group_summary/` 下。前端面板显示 subject 总数、warning/error 总数、contracts 数量、mean FD/fALFF/ReHo/FC ROI count 等指标卡片。
```
