你是我的工程搭建助手。前五步已经完成：

Step 1：完成项目工程骨架，并打通 MATLAB / SPM / DPABI 环境检查闭环。
Step 2：完成单节点执行闭环，可以运行一个 SPM smoke test 节点。
Step 3：完成最小 Pipeline DAG 执行闭环，可以执行 environment_check → spm_smoke_test。
Step 4：完成数据集导入、扫描与索引闭环，可以创建 synthetic BIDS-like 数据集，并生成 dataset_index.json、data_completeness_report.json、subject_table.csv。
Step 5：完成 synthetic subject-level 预处理与 QC 闭环，可以对每个 COMPLETE subject 执行 SPM smoothing，并生成 subject_qc.json。

现在开始第六步。

第六步目标：实现“数据集级评估与报告生成闭环”。

也就是说，本步骤要在 Step 5 的输出基础上，聚合所有 subject-level 结果，生成数据集级别评估结果和可读报告：

- 读取 dataset_index.json
- 读取 subject_table.csv
- 读取每个 subject 的 subject_qc.json
- 读取每个 subject 的 state JSON
- 汇总 subject 处理状态
- 汇总 QC 指标
- 生成 subject_qc_table.csv
- 生成 exclusion_recommendations.csv
- 生成 dataset_summary.json
- 生成 dataset_evaluation_report.md
- 生成 dataset_evaluation_report.html
- 将 dataset_evaluation 作为 project-level pipeline node 接入现有 Pipeline Executor

不要实现 UI。
不要实现 FastAPI 服务。
不要实现完整 Agent Runtime。
不要实现多 Agent 协作。
不要做并行调度。
不要做 GPU。
不要做 DPABI pipeline。
不要处理真实医学影像数据。
不要修改 SPM / DPABI 源码。
不要引入数据库。
不要生成 PDF。
不要引入复杂前端依赖。

本步骤只做数据集级评估与 Markdown/HTML 报告闭环。

---

## 1. 创建 specs/dataset_evaluation_spec.md

创建文件：

```text
specs/dataset_evaluation_spec.md

内容：

# Dataset Evaluation Specification

This document defines the MVP dataset-level evaluation behavior.

## Scope

The Dataset Evaluator aggregates subject-level preprocessing and QC results.

The MVP supports:

- dataset_index.json
- subject_table.csv
- subject_qc.json files
- subject-level node states
- dataset-level summary JSON
- subject-level QC table CSV
- exclusion recommendation CSV
- Markdown report
- HTML report

Unsupported in this step:

- PDF generation
- statistical group comparison
- clinical diagnosis
- disease inference
- GPU metrics
- real medical imaging interpretation
- UI

## Input Files

Expected inputs:

```text
work/dataset_index/dataset_index.json
work/dataset_index/subject_table.csv
work/states/{run_id}/{subject_id}/spm_smooth_subject.json
work/states/{run_id}/{subject_id}/subject_qc.json
derivatives/qc/{subject_id}/subject_qc.json
Output Files

The Dataset Evaluator writes:

reports/dataset_evaluation/dataset_summary.json
reports/dataset_evaluation/subject_qc_table.csv
reports/dataset_evaluation/exclusion_recommendations.csv
reports/dataset_evaluation/dataset_evaluation_report.md
reports/dataset_evaluation/dataset_evaluation_report.html
Subject Recommendation Categories
INCLUDE: subject passed preprocessing and QC
MANUAL_REVIEW: subject has warnings or suspicious metrics
EXCLUDE: subject failed preprocessing or QC
MVP Exclusion Rules

A subject should be EXCLUDE if:

preprocessing failed
subject_qc failed
smoothed output is missing
nan_count > 0
finite_voxel_count == 0

A subject should be MANUAL_REVIEW if:

QC metrics are missing
std is 0 or null
shape is missing
subject status in dataset_index is not COMPLETE

Otherwise:

INCLUDE
Dataset Quality Score

MVP score ranges from 0 to 100.

Suggested scoring:

Data completeness: 30 points
Preprocessing success: 30 points
QC pass rate: 30 points
Warning penalty: 10 points

This score is only an engineering QC indicator. It is not a clinical or scientific conclusion.

Safety Rules
Do not modify rawdata.
Do not delete files.
Do not modify derivatives except writing reports.
Do not make clinical conclusions.
Do not infer disease status.
Always distinguish automatic recommendation from human review.

---

## 2. 创建 backend/app/tools/dataset_evaluator.py

创建文件：

```text
backend/app/tools/dataset_evaluator.py

目标：聚合 subject-level preprocessing 和 QC 输出，生成数据集级评估结果。

提供函数：

evaluate_dataset(
    run_id: str,
    work_dir: str,
    derivatives_dir: str,
    report_dir: str,
    dataset_index_path: str | None = None,
) -> dict

功能要求：

读取 dataset_index.json。
读取每个 subject 的 dataset status。
查找 subject-level state：
work/states/{run_id}/{subject_id}/spm_smooth_subject.json
work/states/{run_id}/{subject_id}/subject_qc.json
查找 subject QC：
derivatives/qc/{subject_id}/subject_qc.json
生成 subject-level 评估表。
生成数据集级 summary。
生成推荐：
INCLUDE
MANUAL_REVIEW
EXCLUDE
写入：
dataset_summary.json
subject_qc_table.csv
exclusion_recommendations.csv
返回结构化 dict。
不要因为某个 subject 文件缺失而崩溃，要记录为 warning 或 error。

输出目录：

reports/dataset_evaluation/

返回示例：

{
  "ok": true,
  "node_id": "dataset_evaluation",
  "backend": "python",
  "outputs": [
    "reports/dataset_evaluation/dataset_summary.json",
    "reports/dataset_evaluation/subject_qc_table.csv",
    "reports/dataset_evaluation/exclusion_recommendations.csv"
  ],
  "metrics": {
    "subjects_total": 2,
    "subjects_include": 2,
    "subjects_manual_review": 0,
    "subjects_exclude": 0,
    "dataset_quality_score": 100
  },
  "warnings": [],
  "errors": []
}

请实现辅助函数：

_read_json(path: Path) -> dict | None
_load_dataset_index(path: Path) -> dict
_find_subjects(dataset_index: dict) -> list[dict]
_load_subject_state(work_dir: str, run_id: str, subject_id: str, node_id: str) -> dict | None
_load_subject_qc(derivatives_dir: str, subject_id: str) -> dict | None
_recommend_subject(...)
_compute_dataset_quality_score(...)
_write_csv(...)

请使用标准库 pathlib、json、csv，不要引入 pandas。

参考实现方向：

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _subject_id_from_record(record: dict[str, Any]) -> str:
    return str(record.get("subject_id") or record.get("id") or "")


def _load_subject_state(
    work_dir: str,
    run_id: str,
    subject_id: str,
    node_id: str,
) -> dict[str, Any] | None:
    path = Path(work_dir) / "states" / run_id / subject_id / f"{node_id}.json"
    return _read_json(path)


def _load_subject_qc(
    derivatives_dir: str,
    subject_id: str,
) -> dict[str, Any] | None:
    path = Path(derivatives_dir) / "qc" / subject_id / "subject_qc.json"
    return _read_json(path)


def _recommend_subject(
    dataset_status: str,
    smooth_state: dict[str, Any] | None,
    qc_state: dict[str, Any] | None,
    qc_payload: dict[str, Any] | None,
) -> tuple[str, list[str]]:
    reasons: list[str] = []

    if dataset_status != "COMPLETE":
        reasons.append(f"dataset_status={dataset_status}")
        return "MANUAL_REVIEW", reasons

    if not smooth_state:
        reasons.append("missing spm_smooth_subject state")
        return "EXCLUDE", reasons

    if smooth_state.get("status") != "SUCCESS":
        reasons.append("spm_smooth_subject did not succeed")
        return "EXCLUDE", reasons

    if not qc_state:
        reasons.append("missing subject_qc state")
        return "EXCLUDE", reasons

    if qc_state.get("status") != "SUCCESS":
        reasons.append("subject_qc did not succeed")
        return "EXCLUDE", reasons

    if not qc_payload:
        reasons.append("missing subject_qc payload")
        return "MANUAL_REVIEW", reasons

    if not qc_payload.get("ok"):
        reasons.append("subject_qc payload ok=false")
        return "EXCLUDE", reasons

    metrics = qc_payload.get("metrics", {})
    nan_count = metrics.get("nan_count")
    finite_voxel_count = metrics.get("finite_voxel_count")
    std = metrics.get("std")
    shape = metrics.get("shape")

    if nan_count is not None and int(nan_count) > 0:
        reasons.append(f"nan_count={nan_count}")
        return "EXCLUDE", reasons

    if finite_voxel_count is not None and int(finite_voxel_count) == 0:
        reasons.append("finite_voxel_count=0")
        return "EXCLUDE", reasons

    if std is None or float(std) == 0.0:
        reasons.append("std is missing or zero")
        return "MANUAL_REVIEW", reasons

    if not shape:
        reasons.append("shape is missing")
        return "MANUAL_REVIEW", reasons

    return "INCLUDE", reasons


def _compute_dataset_quality_score(
    subjects_total: int,
    subjects_complete: int,
    subjects_preprocess_success: int,
    subjects_qc_success: int,
    subjects_manual_review: int,
    subjects_exclude: int,
) -> int:
    if subjects_total <= 0:
        return 0

    completeness_score = 30.0 * subjects_complete / subjects_total
    preprocess_score = 30.0 * subjects_preprocess_success / subjects_total
    qc_score = 30.0 * subjects_qc_success / subjects_total
    warning_penalty = min(10.0, 10.0 * subjects_manual_review / subjects_total)
    exclude_penalty = min(20.0, 20.0 * subjects_exclude / subjects_total)

    score = completeness_score + preprocess_score + qc_score + 10.0
    score -= warning_penalty
    score -= exclude_penalty

    return max(0, min(100, int(round(score))))


def evaluate_dataset(
    run_id: str,
    work_dir: str,
    derivatives_dir: str,
    report_dir: str,
    dataset_index_path: str | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    dataset_index_file = Path(dataset_index_path) if dataset_index_path else Path(work_dir) / "dataset_index" / "dataset_index.json"
    dataset_index = _read_json(dataset_index_file)

    if not dataset_index:
        return {
            "ok": False,
            "node_id": "dataset_evaluation",
            "backend": "python",
            "outputs": [],
            "metrics": {},
            "warnings": warnings,
            "errors": [f"Dataset index not found or invalid: {dataset_index_file}"],
        }

    subjects = dataset_index.get("subjects", [])
    out_dir = Path(report_dir) / "dataset_evaluation"
    out_dir.mkdir(parents=True, exist_ok=True)

    subject_rows: list[dict[str, Any]] = []
    recommendation_rows: list[dict[str, Any]] = []

    subjects_total = len(subjects)
    subjects_complete = 0
    subjects_preprocess_success = 0
    subjects_qc_success = 0
    subjects_include = 0
    subjects_manual_review = 0
    subjects_exclude = 0

    for subject_record in subjects:
        subject_id = _subject_id_from_record(subject_record)
        dataset_status = str(subject_record.get("status", "UNKNOWN"))

        if dataset_status == "COMPLETE":
            subjects_complete += 1

        smooth_state = _load_subject_state(work_dir, run_id, subject_id, "spm_smooth_subject")
        qc_state = _load_subject_state(work_dir, run_id, subject_id, "subject_qc")
        qc_payload = _load_subject_qc(derivatives_dir, subject_id)

        smooth_status = smooth_state.get("status") if smooth_state else "MISSING"
        qc_status = qc_state.get("status") if qc_state else "MISSING"

        if smooth_status == "SUCCESS":
            subjects_preprocess_success += 1
        if qc_status == "SUCCESS" and qc_payload and qc_payload.get("ok"):
            subjects_qc_success += 1

        recommendation, reasons = _recommend_subject(
            dataset_status=dataset_status,
            smooth_state=smooth_state,
            qc_state=qc_state,
            qc_payload=qc_payload,
        )

        if recommendation == "INCLUDE":
            subjects_include += 1
        elif recommendation == "MANUAL_REVIEW":
            subjects_manual_review += 1
        elif recommendation == "EXCLUDE":
            subjects_exclude += 1

        metrics = qc_payload.get("metrics", {}) if qc_payload else {}

        row = {
            "subject_id": subject_id,
            "dataset_status": dataset_status,
            "smooth_status": smooth_status,
            "qc_status": qc_status,
            "recommendation": recommendation,
            "reasons": "; ".join(reasons),
            "shape": json.dumps(metrics.get("shape"), ensure_ascii=False),
            "dtype": metrics.get("dtype"),
            "mean": metrics.get("mean"),
            "std": metrics.get("std"),
            "min": metrics.get("min"),
            "max": metrics.get("max"),
            "nan_count": metrics.get("nan_count"),
            "finite_voxel_count": metrics.get("finite_voxel_count"),
        }
        subject_rows.append(row)

        if recommendation != "INCLUDE":
            recommendation_rows.append({
                "subject_id": subject_id,
                "recommendation": recommendation,
                "reasons": "; ".join(reasons),
            })

    dataset_quality_score = _compute_dataset_quality_score(
        subjects_total=subjects_total,
        subjects_complete=subjects_complete,
        subjects_preprocess_success=subjects_preprocess_success,
        subjects_qc_success=subjects_qc_success,
        subjects_manual_review=subjects_manual_review,
        subjects_exclude=subjects_exclude,
    )

    dataset_summary = {
        "run_id": run_id,
        "dataset_index": str(dataset_index_file),
        "subjects_total": subjects_total,
        "subjects_complete": subjects_complete,
        "subjects_preprocess_success": subjects_preprocess_success,
        "subjects_qc_success": subjects_qc_success,
        "subjects_include": subjects_include,
        "subjects_manual_review": subjects_manual_review,
        "subjects_exclude": subjects_exclude,
        "dataset_quality_score": dataset_quality_score,
        "warnings": warnings,
        "errors": errors,
        "disclaimer": "This report is for engineering QC and research preprocessing support only. It is not a clinical diagnosis.",
    }

    dataset_summary_path = out_dir / "dataset_summary.json"
    subject_qc_table_path = out_dir / "subject_qc_table.csv"
    exclusion_path = out_dir / "exclusion_recommendations.csv"

    dataset_summary_path.write_text(
        json.dumps(dataset_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if subject_rows:
        with subject_qc_table_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(subject_rows[0].keys()))
            writer.writeheader()
            writer.writerows(subject_rows)
    else:
        subject_qc_table_path.write_text("", encoding="utf-8")

    rec_fields = ["subject_id", "recommendation", "reasons"]
    with exclusion_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rec_fields)
        writer.writeheader()
        writer.writerows(recommendation_rows)

    return {
        "ok": True,
        "node_id": "dataset_evaluation",
        "backend": "python",
        "outputs": [
            str(dataset_summary_path),
            str(subject_qc_table_path),
            str(exclusion_path),
        ],
        "metrics": {
            "subjects_total": subjects_total,
            "subjects_complete": subjects_complete,
            "subjects_preprocess_success": subjects_preprocess_success,
            "subjects_qc_success": subjects_qc_success,
            "subjects_include": subjects_include,
            "subjects_manual_review": subjects_manual_review,
            "subjects_exclude": subjects_exclude,
            "dataset_quality_score": dataset_quality_score,
        },
        "warnings": warnings,
        "errors": errors,
    }

可以在此基础上调整，但不要删除核心字段。

3. 创建 backend/app/tools/report_writer.py

创建文件：

backend/app/tools/report_writer.py

目标：根据 dataset_summary.json 和 subject_qc_table.csv 生成 Markdown 和 HTML 报告。

提供函数：

write_dataset_evaluation_report(
    dataset_summary_path: str,
    subject_qc_table_path: str,
    exclusion_recommendations_path: str,
    output_dir: str,
) -> dict

输出：

reports/dataset_evaluation/dataset_evaluation_report.md
reports/dataset_evaluation/dataset_evaluation_report.html

要求：

使用标准库即可。
不要引入 jinja2。
报告必须包含：
Title
Executive Summary
Dataset Overview
Preprocessing Success
QC Summary
Recommendation Summary
Exclusion / Manual Review List
Reproducibility Inputs
Disclaimer
HTML 可以是简单静态 HTML。
返回结构化 dict。
不生成 PDF。

Markdown 报告示例结构：

# Dataset Evaluation Report

## Executive Summary

- Total subjects:
- Included subjects:
- Manual review:
- Excluded subjects:
- Dataset quality score:

## Dataset Overview

...

## Recommendation Summary

...

## Subjects Requiring Attention

...

## Disclaimer

This report is for engineering QC and research preprocessing support only. It is not a clinical diagnosis.

参考实现方向：

from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_dataset_evaluation_report(
    dataset_summary_path: str,
    subject_qc_table_path: str,
    exclusion_recommendations_path: str,
    output_dir: str,
) -> dict[str, Any]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = _read_json(Path(dataset_summary_path))
    subject_rows = _read_csv_rows(Path(subject_qc_table_path))
    attention_rows = _read_csv_rows(Path(exclusion_recommendations_path))

    md_path = out_dir / "dataset_evaluation_report.md"
    html_path = out_dir / "dataset_evaluation_report.html"

    lines: list[str] = []
    lines.append("# Dataset Evaluation Report")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"- Run ID: {summary.get('run_id')}")
    lines.append(f"- Total subjects: {summary.get('subjects_total')}")
    lines.append(f"- Complete subjects: {summary.get('subjects_complete')}")
    lines.append(f"- Preprocessing success: {summary.get('subjects_preprocess_success')}")
    lines.append(f"- QC success: {summary.get('subjects_qc_success')}")
    lines.append(f"- Included subjects: {summary.get('subjects_include')}")
    lines.append(f"- Manual review: {summary.get('subjects_manual_review')}")
    lines.append(f"- Excluded subjects: {summary.get('subjects_exclude')}")
    lines.append(f"- Dataset quality score: {summary.get('dataset_quality_score')} / 100")
    lines.append("")
    lines.append("## Dataset Overview")
    lines.append("")
    lines.append(f"- Dataset index: `{summary.get('dataset_index')}`")
    lines.append("")
    lines.append("## Recommendation Summary")
    lines.append("")
    lines.append("| Category | Count |")
    lines.append("|---|---:|")
    lines.append(f"| INCLUDE | {summary.get('subjects_include')} |")
    lines.append(f"| MANUAL_REVIEW | {summary.get('subjects_manual_review')} |")
    lines.append(f"| EXCLUDE | {summary.get('subjects_exclude')} |")
    lines.append("")
    lines.append("## Subjects Requiring Attention")
    lines.append("")
    if attention_rows:
        lines.append("| Subject | Recommendation | Reasons |")
        lines.append("|---|---|---|")
        for row in attention_rows:
            lines.append(
                f"| {row.get('subject_id')} | {row.get('recommendation')} | {row.get('reasons')} |"
            )
    else:
        lines.append("No subjects require exclusion or manual review based on MVP rules.")
    lines.append("")
    lines.append("## Subject QC Table")
    lines.append("")
    lines.append(f"Subject-level QC table: `{subject_qc_table_path}`")
    lines.append("")
    lines.append("## Reproducibility Inputs")
    lines.append("")
    lines.append(f"- Dataset summary: `{dataset_summary_path}`")
    lines.append(f"- Subject QC table: `{subject_qc_table_path}`")
    lines.append(f"- Exclusion recommendations: `{exclusion_recommendations_path}`")
    lines.append("")
    lines.append("## Disclaimer")
    lines.append("")
    lines.append(
        "This report is for engineering QC and research preprocessing support only. "
        "It is not a clinical diagnosis and does not provide medical conclusions."
    )
    lines.append("")

    md_content = "\n".join(lines)
    md_path.write_text(md_content, encoding="utf-8")

    body = html.escape(md_content)
    html_content = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Dataset Evaluation Report</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      max-width: 960px;
      margin: 40px auto;
      line-height: 1.6;
      padding: 0 24px;
    }}
    pre {{
      white-space: pre-wrap;
      background: #f6f8fa;
      padding: 16px;
      border-radius: 8px;
    }}
  </style>
</head>
<body>
  <pre>{body}</pre>
</body>
</html>
"""
    html_path.write_text(html_content, encoding="utf-8")

    return {
        "ok": True,
        "node_id": "report_writer",
        "backend": "python",
        "outputs": [str(md_path), str(html_path)],
        "metrics": {
            "subjects_in_report": len(subject_rows),
            "attention_subjects": len(attention_rows),
        },
        "warnings": [],
        "errors": [],
    }
4. 修改 backend/app/tools/dataset_evaluator.py

在 evaluate_dataset 末尾集成 report_writer。

要求：

在写完：
dataset_summary.json
subject_qc_table.csv
exclusion_recommendations.csv

之后调用：

write_dataset_evaluation_report(...)
将 report_writer 的 outputs 合并到 evaluate_dataset 返回值。
如果报告生成失败，evaluate_dataset 应该 ok=false 或 warnings 记录失败原因。
report_writer 失败不能导致未捕获异常。

新增导入：

from backend.app.tools.report_writer import write_dataset_evaluation_report

返回 outputs 应包含：

reports/dataset_evaluation/dataset_summary.json
reports/dataset_evaluation/subject_qc_table.csv
reports/dataset_evaluation/exclusion_recommendations.csv
reports/dataset_evaluation/dataset_evaluation_report.md
reports/dataset_evaluation/dataset_evaluation_report.html
5. 修改 examples/pipeline_subject_preprocess.yaml

在现有 pipeline 末尾新增 dataset_evaluation 节点。

当前 pipeline 应该类似：

create_synthetic_bids
data_inspection
spm_smooth_subject
subject_qc

请在最后追加：

  - id: dataset_evaluation
    name: Dataset Evaluation
    agent: dataset-evaluator
    backend: python
    depends_on:
      - subject_qc
    inputs:
      - "./work/dataset_index/dataset_index.json"
    outputs:
      - "./reports/dataset_evaluation/dataset_summary.json"
      - "./reports/dataset_evaluation/subject_qc_table.csv"
      - "./reports/dataset_evaluation/exclusion_recommendations.csv"
      - "./reports/dataset_evaluation/dataset_evaluation_report.md"
      - "./reports/dataset_evaluation/dataset_evaluation_report.html"
    params:
      dataset_index: "./work/dataset_index/dataset_index.json"
      output_dir: "./reports/dataset_evaluation"
    parallel_level: project
    gpu_supported: false
    cache: false
6. 修改 backend/app/runtime/node_registry.py

新增 dataset_evaluation node runner。

要求：

不破坏已有节点。
从 context 读取：
run_id
work_dir
derivatives_dir
report_dir
从 node.params 读取 dataset_index。
调用 evaluate_dataset。
返回结构化 dict。

新增导入：

from backend.app.tools.dataset_evaluator import evaluate_dataset

新增 runner：

def run_dataset_evaluation_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    dataset_index_path = node.params.get("dataset_index")

    result = evaluate_dataset(
        run_id=context.run_id,
        work_dir=context.work_dir,
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
        dataset_index_path=dataset_index_path,
    )
    result["node_id"] = node.id
    result["backend"] = "python"
    return result

更新 NODE_REGISTRY：

NODE_REGISTRY = {
    "environment_check": run_environment_check_node,
    "spm_smoke_test": run_spm_smoke_test_node,
    "create_synthetic_bids": run_create_synthetic_bids_node,
    "data_inspection": run_data_inspection_node,
    "spm_smooth_subject": run_spm_smooth_subject_node,
    "subject_qc": run_subject_qc_node,
    "dataset_evaluation": run_dataset_evaluation_node,
}
7. 修改 backend/app/runtime/pipeline_executor.py

现有 executor 已支持 project-level 和 subject-level 节点。

现在需要确保：

project-level 节点可以出现在 subject-level 节点之后。
如果 project-level 节点 depends_on 一个 subject-level 节点，例如 subject_qc：
只有当所有 COMPLETE subjects 的 subject_qc 成功时，才认为依赖成功。
如果部分 subject_qc 失败，dataset_evaluation 仍然可以运行，但 pipeline summary 最终应为 PARTIAL。
dataset_evaluation 应尽可能运行，即使部分 subject 失败，因为它需要总结失败情况。
如果所有 subject 都失败且没有任何 QC 输出，dataset_evaluation 也应生成报告，报告显示失败和 EXCLUDE。
不要让 dependency 机制阻止 dataset_evaluation 运行，除非 dataset_index.json 缺失。

建议做法：

在 executor 内维护 node_aggregate_status：
project node：SUCCESS / FAILED
subject node：SUCCESS if all subject executions success, PARTIAL if some failed, FAILED if all failed
project node 检查 depends_on 时：
如果依赖是 SUCCESS：继续
如果依赖是 PARTIAL 且当前 node.id == "dataset_evaluation"：允许继续
如果依赖 FAILED：停止或跳过

保持逻辑简单，不要过度抽象。

8. 修改 backend/app/runtime/state_store.py

确保 project-level dataset_evaluation 的 state 能保存：

outputs
metrics
warnings
errors

路径应为：

work/states/{run_id}/dataset_evaluation.json

summary 应保存 dataset_evaluation 的 metrics，例如：

{
  "dataset_quality_score": 100,
  "subjects_include": 2,
  "subjects_manual_review": 0,
  "subjects_exclude": 0
}
9. 新增 backend/app/tools/run_dataset_evaluation_cli.py

创建文件：

backend/app/tools/run_dataset_evaluation_cli.py

功能：

默认 project config：
examples/project_config_dataset.yaml
默认 pipeline：
examples/pipeline_subject_preprocess.yaml
调用 run_pipeline。
打印 summary JSON。
返回码：
SUCCESS 返回 0
PARTIAL 返回 2
FAILED 返回 2
INVALID 返回 1

参考实现：

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.pipeline_executor import run_pipeline


def main() -> int:
    project_config = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/project_config_dataset.yaml")
    pipeline = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("examples/pipeline_subject_preprocess.yaml")

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
10. 更新 README.md

追加第六步说明：

## Step 6: Dataset Evaluation and Report

This step aggregates subject-level preprocessing and QC outputs into a dataset-level evaluation report.

It produces:

- dataset_summary.json
- subject_qc_table.csv
- exclusion_recommendations.csv
- dataset_evaluation_report.md
- dataset_evaluation_report.html

Run:

```bash
python -m backend.app.tools.run_dataset_evaluation_cli

Or explicitly:

python -m backend.app.tools.run_dataset_evaluation_cli examples/project_config_dataset.yaml examples/pipeline_subject_preprocess.yaml

Expected outputs:

reports/dataset_evaluation/dataset_summary.json
reports/dataset_evaluation/subject_qc_table.csv
reports/dataset_evaluation/exclusion_recommendations.csv
reports/dataset_evaluation/dataset_evaluation_report.md
reports/dataset_evaluation/dataset_evaluation_report.html

work/states/run_subject_preprocess_001/dataset_evaluation.json
work/pipeline_runs/run_subject_preprocess_001/summary.json

Success criteria:

dataset_summary.json exists.
subject_qc_table.csv contains sub-001 and sub-002.
dataset_evaluation_report.md exists.
dataset_evaluation_report.html exists.
dataset_summary.json contains dataset_quality_score.

---

## 11. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/dataset_evaluation_spec.md
backend/app/tools/dataset_evaluator.py
backend/app/tools/report_writer.py
examples/pipeline_subject_preprocess.yaml
backend/app/runtime/node_registry.py
backend/app/runtime/pipeline_executor.py
backend/app/runtime/state_store.py
backend/app/tools/run_dataset_evaluation_cli.py
README.md

运行：

pip install numpy nibabel pyyaml
python -m backend.app.tools.run_dataset_evaluation_cli

成功后应该生成：

reports/dataset_evaluation/dataset_summary.json
reports/dataset_evaluation/subject_qc_table.csv
reports/dataset_evaluation/exclusion_recommendations.csv
reports/dataset_evaluation/dataset_evaluation_report.md
reports/dataset_evaluation/dataset_evaluation_report.html

work/states/run_subject_preprocess_001/dataset_evaluation.json
work/pipeline_runs/run_subject_preprocess_001/summary.json

其中：

reports/dataset_evaluation/dataset_summary.json

应该包含类似：

{
  "run_id": "run_subject_preprocess_001",
  "subjects_total": 2,
  "subjects_complete": 2,
  "subjects_preprocess_success": 2,
  "subjects_qc_success": 2,
  "subjects_include": 2,
  "subjects_manual_review": 0,
  "subjects_exclude": 0,
  "dataset_quality_score": 100
}

其中：

reports/dataset_evaluation/subject_qc_table.csv

应该包含：

sub-001
sub-002

其中：

reports/dataset_evaluation/dataset_evaluation_report.md

应该包含：

# Dataset Evaluation Report
## Executive Summary
## Recommendation Summary
## Disclaimer

如果某个 subject 的 smoothing 或 QC 失败：

dataset_evaluation 仍应运行。
失败 subject 应进入 EXCLUDE。
summary status 可以是 PARTIAL。
report 中应列出需要关注的 subject。
不要因为单个 subject 失败导致报告不生成。
12. 重要限制

本步骤只做数据集级评估与 Markdown/HTML 报告。

不要实现：

UI
FastAPI 服务
Agent Runtime
多 Agent
并行调度
GPU
DPABI pipeline
真实医学影像预处理
数据库
PDF 生成
复杂统计分析
临床诊断结论

完成后请总结：

新增了哪些文件
修改了哪些文件
如何运行 dataset evaluation
成功输出是什么
如果部分 subject 失败，报告如何体现
如果失败应该看哪些日志或 JSON


'''
这一步主要做的是：

## 第六步：数据集级评估与报告生成闭环
这是在 Step 5 的 subject-level 预处理基础上， 聚合所有被试结果，生成数据集级别的评估报告 。

### 核心目标
1. 聚合 subject-level 结果
   
   - 读取 dataset_index.json - 获取被试列表和状态
   - 读取 subject_table.csv - 获取被试基本信息
   - 读取每个被试的 subject_qc.json - 获取 QC 指标
   - 读取每个被试的 state JSON - 获取预处理状态
2. 生成数据集级输出文件
   
   - dataset_summary.json - 数据集整体统计信息
   - subject_qc_table.csv - 所有被试的 QC 指标表
   - exclusion_recommendations.csv - 被试纳入/排除建议
3. 生成可读报告
   
   - dataset_evaluation_report.md - Markdown 格式报告
   - dataset_evaluation_report.html - HTML 格式报告（带样式）
### 被试推荐分类规则
类别 条件 INCLUDE 预处理成功 + QC 通过 + 无异常指标 MANUAL_REVIEW QC 指标缺失 / std 为 0 / shape 缺失 / dataset_index 状态非 COMPLETE EXCLUDE 预处理失败 / QC 失败 / 平滑输出缺失 / nan_count > 0 / finite_voxel_count == 0

### 数据集质量评分 (0-100)
- 数据完整性: 30 分
- 预处理成功率: 30 分
- QC 通过率: 30 分
- 基础分: 10 分
- 警告惩罚: 最多扣 10 分
- 排除惩罚: 最多扣 20 分
### 执行流程
```
create_synthetic_bids → data_inspection → spm_smooth_subject → 
subject_qc → dataset_evaluation
                         (project)          (subject-level)      
                         (subject)      (project)
```
### 明确不做的事情
- ❌ PDF 生成
- ❌ 统计组间比较
- ❌ 临床诊断
- ❌ 疾病推断
- ❌ GPU 指标
- ❌ 真实医学影像解释
- ❌ UI / FastAPI
- ❌ 并行调度
这一步已经 全部完成 并验证通过。成功生成了完整的数据集评估报告，2 个被试全部通过，数据集质量评分 100 分。
'''