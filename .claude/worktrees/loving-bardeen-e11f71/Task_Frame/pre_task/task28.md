你是我的工程搭建助手。前二十七步已经完成：

Step 1：完成项目工程骨架，并打通 MATLAB / SPM / DPABI 环境检查闭环。
Step 2：完成单节点执行闭环。
Step 3：完成最小 Pipeline DAG 执行闭环。
Step 4：完成 synthetic BIDS-like 数据集扫描与索引闭环。
Step 5：完成 synthetic subject-level SPM smoothing + QC 闭环。
Step 6：完成数据集级评估与 Markdown/HTML 报告闭环。
Step 7：完成 deterministic Agent Runtime、Plan Mode、Execute Mode、Tool Registry、Hook Manager 和 approval 机制。
Step 8：完成最小长期记忆、后台复盘和错误知识库闭环。
Step 9：完成最小 FastAPI 后端服务闭环。
Step 10：完成最小 React 前端闭环。
Step 11：完成 Run Monitor + State / Log Viewer 闭环。
Step 12：完成 Error Diagnosis + Retry Plan 闭环。
Step 13：完成 Checkpoint / Cache / Approved Retry 闭环。
Step 14：完成本地 subject-level 并行调度与资源限制闭环。
Step 15：完成 GPU ALFF / fALFF 原型与 CPU fallback + Benchmark 闭环。
Step 16：完成 Validation / Benchmark / Regression Suite 闭环。
Step 17：完成 DPABI Capability Inspector + Wrapper Scaffold 闭环。
Step 18：完成 DPABI Dataset Adapter + Batch Config Preflight 闭环。
Step 19：完成 DPABI 参数审查 + Approved Run Plan 闭环。
Step 20：完成 DPABI Approved Sandbox Smoke Run + Execution Audit 闭环。
Step 21：完成 DPABI Function Signature Probe + Wrapper Contract Registry 闭环。
Step 22：完成 DPABI Single-Function Wrapper Sandbox + Contract Test 闭环。
Step 23：完成 DPABI Single-Function Subject Wrapper + SPM Baseline Comparison 闭环。
Step 24：完成 DPABI Wrapper Validation Suite + Function Compatibility Matrix 闭环。
Step 25：完成 DPABI Pipeline Template Library + Promotable Wrapper 模板化闭环。
Step 26：完成 DPABI Template Instantiation + Approved Synthetic Execution 闭环。
Step 27：完成 DPABI Parameterized Pipeline Wizard + Review UI 闭环。

现在开始第二十八步。

第二十八步目标：实现“Multi-Run Experiment Tracking + Comparison Dashboard 闭环”。

当前系统已经能产生很多运行结果：

- work/pipeline_runs/*/summary.json
- work/states/*
- reports/dataset_evaluation/*
- reports/gpu_benchmark/*
- reports/dpabi/*
- reports/validation/*
- work/dpabi/template_instances/*/execution_summary.json

但这些结果目前是分散的，缺少统一的实验追踪、run index、run comparison 和可视化 dashboard。

本步骤要实现：

- 扫描所有 pipeline run summary
- 扫描 DPABI template instance execution summary
- 扫描 dataset evaluation / GPU benchmark / DPABI wrapper / validation 报告
- 生成统一 run index
- 创建 experiment record
- 支持为 run 添加 tags / notes / group
- 支持比较多个 run
- 生成 comparison JSON
- 生成 comparison Markdown report
- 后端 API 暴露 run index、experiment record、comparison
- 前端增加 Experiment Tracking / Run Comparison Dashboard
- validation suite 增加 experiment tracker 轻量测试

本步骤只做追踪和对比，不执行新的 pipeline。
本步骤不要启动 MATLAB。
本步骤不要运行 DPABI。
本步骤不要运行 DPARSF_run / DPARSFA_run。
本步骤不要调用 DPABI GUI。
本步骤不要处理真实医学影像数据。
本步骤不要修改 rawdata。
本步骤不要修改 DPABI 源码。
本步骤不要删除文件。

---

## 1. 创建 specs/experiment_tracking_spec.md

创建文件：

```text
specs/experiment_tracking_spec.md

内容：

# Experiment Tracking and Run Comparison Specification

This document defines the MVP multi-run experiment tracking system for MedImage Agent.

## Goals

The experiment tracker should provide a unified view of pipeline runs and generated reports.

It should:

- index pipeline runs
- index DPABI template instance runs
- index report artifacts
- create experiment records
- compare selected runs
- generate comparison JSON
- generate Markdown comparison report
- expose data through API and frontend dashboard

## Scope

Supported in this step:

- scan work/pipeline_runs
- scan work/dpabi/template_instances
- scan reports/dataset_evaluation
- scan reports/gpu_benchmark
- scan reports/dpabi
- scan reports/validation
- create experiment records
- compare multiple run summaries
- compare status, duration, scheduler, node status, output counts
- API and frontend visibility
- lightweight unit test

Unsupported in this step:

- running pipelines
- running MATLAB
- running DPABI
- running DPARSF_run
- running DPARSFA_run
- GUI automation
- real medical image processing
- rawdata modification
- DPABI source modification
- deletion of files
- production-grade MLflow replacement

## Outputs

```text
work/experiments/run_index.json
work/experiments/records/{experiment_id}.json
reports/experiments/{experiment_id}_comparison.json
reports/experiments/{experiment_id}_comparison_report.md
Run Types
pipeline_run
dpabi_template_instance
dataset_evaluation
gpu_benchmark
dpabi_report
validation_report
unknown
Comparison Metrics
run_id
pipeline_id
status
started_at
ended_at
duration_seconds
scheduler_mode
max_workers
matlab_max_workers
nodes_total
nodes_success
nodes_failed
outputs_count
warnings_count
errors_count
Safety Rules
Do not execute pipelines.
Do not launch MATLAB.
Do not run DPABI.
Do not modify rawdata.
Do not modify DPABI source.
Do not delete files.
Read and summarize existing artifacts only.
2. 创建 backend/app/tools/experiment_tracker.py

创建文件：

backend/app/tools/experiment_tracker.py

目标：统一扫描 run、创建实验记录、比较 run。

提供函数：

build_run_index(
    work_dir: str = "./work",
    report_dir: str = "./reports",
) -> dict

create_experiment_record(
    experiment_id: str,
    name: str,
    run_ids: list[str],
    tags: list[str] | None = None,
    notes: str = "",
    work_dir: str = "./work",
) -> dict

compare_experiment_runs(
    experiment_id: str,
    run_ids: list[str],
    work_dir: str = "./work",
    report_dir: str = "./reports",
) -> dict

输出：

work/experiments/run_index.json
work/experiments/records/{experiment_id}.json
reports/experiments/{experiment_id}_comparison.json
reports/experiments/{experiment_id}_comparison_report.md

实现要求：

只读扫描。
不删除任何文件。
不运行 pipeline。
不调用 MATLAB。
对不存在或损坏的 JSON 记录 warning，不崩溃。
run index 至少包括：
run_id
run_type
status
pipeline_id
summary_path
duration_seconds
scheduler
nodes_total
nodes_success
nodes_failed
outputs_count
warnings_count
errors_count
比较多个 run 时生成表格。
支持 run_ids 为空时默认比较最近 5 个 run。

参考实现：

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _safe_id(value: str) -> bool:
    return bool(value) and "/" not in value and "\\" not in value and ".." not in value


def _count_node_status(summary: dict[str, Any]) -> dict[str, int]:
    nodes = summary.get("nodes", []) or summary.get("node_results", []) or []
    total = len(nodes)
    success = 0
    failed = 0

    for node in nodes:
        status = str(node.get("status", "")).upper()
        ok = node.get("ok")
        if ok is True or status in {"SUCCESS", "COMPLETED", "OK"}:
            success += 1
        elif ok is False or status in {"FAILED", "ERROR"}:
            failed += 1

    return {
        "nodes_total": total,
        "nodes_success": success,
        "nodes_failed": failed,
    }


def _count_outputs(summary: dict[str, Any]) -> int:
    count = 0
    nodes = summary.get("nodes", []) or summary.get("node_results", []) or []
    for node in nodes:
        outputs = node.get("outputs", [])
        if isinstance(outputs, list):
            count += len(outputs)
    return count


def _count_messages(summary: dict[str, Any], key: str) -> int:
    count = 0

    direct = summary.get(key, [])
    if isinstance(direct, list):
        count += len(direct)

    nodes = summary.get("nodes", []) or summary.get("node_results", []) or []
    for node in nodes:
        messages = node.get(key, [])
        if isinstance(messages, list):
            count += len(messages)

    return count


def _summarize_pipeline_run(path: Path) -> dict[str, Any] | None:
    summary = _read_json(path)
    if not summary:
        return None

    node_counts = _count_node_status(summary)
    scheduler = summary.get("scheduler", {}) or {}

    run_id = (
        summary.get("run_id")
        or summary.get("execution", {}).get("run_id")
        or path.parent.name
    )

    return {
        "run_id": run_id,
        "run_type": "pipeline_run",
        "pipeline_id": summary.get("pipeline_id"),
        "status": summary.get("status"),
        "started_at": summary.get("started_at"),
        "ended_at": summary.get("ended_at"),
        "duration_seconds": summary.get("duration_seconds"),
        "scheduler_mode": scheduler.get("mode") or summary.get("scheduler_mode"),
        "max_workers": scheduler.get("max_workers") or summary.get("max_workers"),
        "matlab_max_workers": scheduler.get("matlab_max_workers") or summary.get("matlab_max_workers"),
        "summary_path": str(path),
        "nodes_total": node_counts["nodes_total"],
        "nodes_success": node_counts["nodes_success"],
        "nodes_failed": node_counts["nodes_failed"],
        "outputs_count": _count_outputs(summary),
        "warnings_count": _count_messages(summary, "warnings"),
        "errors_count": _count_messages(summary, "errors"),
    }


def _summarize_template_instance(path: Path) -> dict[str, Any] | None:
    payload = _read_json(path)
    if not payload:
        return None

    instance_id = path.parent.name
    pipeline_summary = payload.get("pipeline_summary", {}) or {}

    return {
        "run_id": instance_id,
        "run_type": "dpabi_template_instance",
        "pipeline_id": pipeline_summary.get("pipeline_id"),
        "status": pipeline_summary.get("status"),
        "started_at": pipeline_summary.get("started_at"),
        "ended_at": pipeline_summary.get("ended_at"),
        "duration_seconds": pipeline_summary.get("duration_seconds"),
        "scheduler_mode": pipeline_summary.get("scheduler", {}).get("mode"),
        "max_workers": pipeline_summary.get("scheduler", {}).get("max_workers"),
        "matlab_max_workers": pipeline_summary.get("scheduler", {}).get("matlab_max_workers"),
        "summary_path": str(path),
        "nodes_total": _count_node_status(pipeline_summary)["nodes_total"],
        "nodes_success": _count_node_status(pipeline_summary)["nodes_success"],
        "nodes_failed": _count_node_status(pipeline_summary)["nodes_failed"],
        "outputs_count": _count_outputs(pipeline_summary),
        "warnings_count": _count_messages(pipeline_summary, "warnings"),
        "errors_count": _count_messages(pipeline_summary, "errors"),
    }


def build_run_index(
    work_dir: str = "./work",
    report_dir: str = "./reports",
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    work = Path(work_dir)
    reports = Path(report_dir)
    out_dir = work / "experiments"
    out_dir.mkdir(parents=True, exist_ok=True)

    runs: list[dict[str, Any]] = []

    pipeline_runs_root = work / "pipeline_runs"
    if pipeline_runs_root.exists():
        for summary_path in sorted(pipeline_runs_root.glob("*/summary.json")):
            item = _summarize_pipeline_run(summary_path)
            if item:
                runs.append(item)
            else:
                warnings.append(f"Invalid pipeline summary: {summary_path}")

    template_instances_root = work / "dpabi" / "template_instances"
    if template_instances_root.exists():
        for execution_path in sorted(template_instances_root.glob("*/execution_summary.json")):
            item = _summarize_template_instance(execution_path)
            if item:
                runs.append(item)
            else:
                warnings.append(f"Invalid template instance summary: {execution_path}")

    report_artifacts = {
        "dataset_evaluation": reports / "dataset_evaluation" / "dataset_summary.json",
        "gpu_benchmark": reports / "gpu_benchmark" / "gpu_benchmark_summary.json",
        "dpabi_subject_wrapper": reports / "dpabi" / "dpabi_subject_wrapper_summary.json",
        "dpabi_wrapper_validation": work / "dpabi" / "dpabi_wrapper_compatibility_matrix.json",
        "validation": reports / "validation" / "validation_summary.json",
    }

    artifacts: list[dict[str, Any]] = []
    for name, path in report_artifacts.items():
        exists = path.exists()
        artifacts.append({
            "name": name,
            "exists": exists,
            "path": str(path),
        })

    runs = sorted(
        runs,
        key=lambda item: str(item.get("started_at") or item.get("run_id") or ""),
        reverse=True,
    )

    payload = {
        "ok": True,
        "node_id": "experiment_run_index",
        "backend": "python",
        "generated_at": _now_iso(),
        "runs_total": len(runs),
        "runs": runs,
        "artifacts": artifacts,
        "warnings": warnings,
        "errors": errors,
    }

    index_path = out_dir / "run_index.json"
    index_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    payload["outputs"] = [str(index_path)]
    return payload


def create_experiment_record(
    experiment_id: str,
    name: str,
    run_ids: list[str],
    tags: list[str] | None = None,
    notes: str = "",
    work_dir: str = "./work",
) -> dict[str, Any]:
    if not _safe_id(experiment_id):
        return {
            "ok": False,
            "errors": ["Invalid experiment_id."],
            "warnings": [],
        }

    index = build_run_index(work_dir=work_dir)
    available = {item.get("run_id"): item for item in index.get("runs", [])}

    missing = [run_id for run_id in run_ids if run_id not in available]

    record = {
        "ok": len(missing) == 0,
        "experiment_id": experiment_id,
        "name": name,
        "run_ids": run_ids,
        "tags": tags or [],
        "notes": notes,
        "created_at": _now_iso(),
        "missing_run_ids": missing,
        "runs": [available[run_id] for run_id in run_ids if run_id in available],
        "warnings": [f"Missing run_id: {item}" for item in missing],
        "errors": [],
    }

    out_dir = Path(work_dir) / "experiments" / "records"
    out_dir.mkdir(parents=True, exist_ok=True)

    record_path = out_dir / f"{experiment_id}.json"
    record_path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    record["outputs"] = [str(record_path)]
    return record


def compare_experiment_runs(
    experiment_id: str,
    run_ids: list[str],
    work_dir: str = "./work",
    report_dir: str = "./reports",
) -> dict[str, Any]:
    if not _safe_id(experiment_id):
        return {
            "ok": False,
            "errors": ["Invalid experiment_id."],
            "warnings": [],
        }

    index = build_run_index(work_dir=work_dir, report_dir=report_dir)
    runs = index.get("runs", [])

    if not run_ids:
        run_ids = [item.get("run_id") for item in runs[:5] if item.get("run_id")]

    selected = [item for item in runs if item.get("run_id") in set(run_ids)]
    missing = [run_id for run_id in run_ids if run_id not in {item.get("run_id") for item in selected}]

    comparison_rows = []
    for item in selected:
        comparison_rows.append({
            "run_id": item.get("run_id"),
            "run_type": item.get("run_type"),
            "pipeline_id": item.get("pipeline_id"),
            "status": item.get("status"),
            "duration_seconds": item.get("duration_seconds"),
            "scheduler_mode": item.get("scheduler_mode"),
            "max_workers": item.get("max_workers"),
            "matlab_max_workers": item.get("matlab_max_workers"),
            "nodes_total": item.get("nodes_total"),
            "nodes_success": item.get("nodes_success"),
            "nodes_failed": item.get("nodes_failed"),
            "outputs_count": item.get("outputs_count"),
            "warnings_count": item.get("warnings_count"),
            "errors_count": item.get("errors_count"),
            "summary_path": item.get("summary_path"),
        })

    out_dir = Path(report_dir) / "experiments"
    out_dir.mkdir(parents=True, exist_ok=True)

    comparison_json = out_dir / f"{experiment_id}_comparison.json"
    comparison_md = out_dir / f"{experiment_id}_comparison_report.md"

    payload = {
        "ok": len(selected) > 0,
        "experiment_id": experiment_id,
        "generated_at": _now_iso(),
        "run_ids": run_ids,
        "runs_compared": len(selected),
        "missing_run_ids": missing,
        "rows": comparison_rows,
        "warnings": [f"Missing run_id: {item}" for item in missing],
        "errors": [] if selected else ["No runs selected for comparison."],
    }

    comparison_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# Experiment Run Comparison Report")
    lines.append("")
    lines.append(f"- Experiment ID: {experiment_id}")
    lines.append(f"- Runs compared: {len(selected)}")
    lines.append(f"- Missing run IDs: {missing}")
    lines.append("")
    lines.append("## Comparison")
    lines.append("")
    if comparison_rows:
        lines.append("| Run ID | Type | Pipeline | Status | Duration | Scheduler | Nodes OK/Total | Errors | Warnings |")
        lines.append("|---|---|---|---|---:|---|---:|---:|---:|")
        for row in comparison_rows:
            lines.append(
                f"| {row['run_id']} | {row['run_type']} | {row['pipeline_id']} | "
                f"{row['status']} | {row['duration_seconds']} | {row['scheduler_mode']} | "
                f"{row['nodes_success']}/{row['nodes_total']} | {row['errors_count']} | "
                f"{row['warnings_count']} |"
            )
    else:
        lines.append("No runs available for comparison.")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This comparison only reads existing artifacts and does not execute pipelines or MATLAB.")

    comparison_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    payload["outputs"] = [str(comparison_json), str(comparison_md)]
    return payload
3. 创建 backend/app/tools/run_experiment_tracker_cli.py

创建文件：

backend/app/tools/run_experiment_tracker_cli.py

功能：

默认生成 run index。
如果传入 --compare，生成默认 comparison。
打印 JSON。

内容：

from __future__ import annotations

import json
import sys

from backend.app.tools.experiment_tracker import (
    build_run_index,
    compare_experiment_runs,
)


def main() -> int:
    args = sys.argv[1:]

    if "--compare" in args:
        experiment_id = "latest_comparison"
        run_ids = [arg for arg in args if arg != "--compare"]
        result = compare_experiment_runs(
            experiment_id=experiment_id,
            run_ids=run_ids,
        )
    else:
        result = build_run_index()

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
4. 修改 backend/app/api/models.py

新增 request models：

class ExperimentRecordRequest(BaseModel):
    experiment_id: str = Field(default="experiment_001")
    name: str = Field(default="Synthetic DPABI Experiment")
    run_ids: list[str] = Field(default=[])
    tags: list[str] = Field(default=[])
    notes: str = Field(default="")


class ExperimentCompareRequest(BaseModel):
    experiment_id: str = Field(default="latest_comparison")
    run_ids: list[str] = Field(default=[])
5. 修改 backend/app/api/routes.py

新增 API：

GET  /api/experiments/runs
POST /api/experiments/records
POST /api/experiments/compare
GET  /api/experiments/latest

新增导入：

from backend.app.api.models import ExperimentCompareRequest, ExperimentRecordRequest
from backend.app.tools.experiment_tracker import (
    build_run_index,
    compare_experiment_runs,
    create_experiment_record,
)

新增路由：

@router.get("/api/experiments/runs")
def api_experiment_runs() -> dict[str, Any]:
    return build_run_index(work_dir="./work", report_dir="./reports")


@router.post("/api/experiments/records")
def api_create_experiment_record(request: ExperimentRecordRequest) -> dict[str, Any]:
    result = create_experiment_record(
        experiment_id=request.experiment_id,
        name=request.name,
        run_ids=request.run_ids,
        tags=request.tags,
        notes=request.notes,
        work_dir="./work",
    )

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)

    return result


@router.post("/api/experiments/compare")
def api_compare_experiment_runs(request: ExperimentCompareRequest) -> dict[str, Any]:
    result = compare_experiment_runs(
        experiment_id=request.experiment_id,
        run_ids=request.run_ids,
        work_dir="./work",
        report_dir="./reports",
    )

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)

    return result


@router.get("/api/experiments/latest")
def api_experiment_latest() -> dict[str, Any]:
    base = Path("reports") / "experiments"

    latest_json = None
    latest_md = None

    if base.exists():
        json_files = sorted(base.glob("*_comparison.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        md_files = sorted(base.glob("*_comparison_report.md"), key=lambda p: p.stat().st_mtime, reverse=True)

        if json_files:
            latest_json = _read_json_if_exists(json_files[0])
        if md_files:
            latest_md = _read_text_if_exists(md_files[0])

    return {
        "ok": True,
        "latest_comparison": latest_json,
        "latest_report": latest_md,
    }
6. 修改 frontend/src/api.ts

新增：

export async function getExperimentRuns(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/experiments/runs");
}

export async function createExperimentRecord(
  baseUrl: string,
  payload: {
    experiment_id: string;
    name: string;
    run_ids: string[];
    tags: string[];
    notes: string;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/experiments/records",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function compareExperimentRuns(
  baseUrl: string,
  payload: {
    experiment_id: string;
    run_ids: string[];
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/experiments/compare",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getExperimentLatest(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/experiments/latest");
}
7. 创建 frontend/src/components/ExperimentPanel.tsx

创建文件：

frontend/src/components/ExperimentPanel.tsx

内容：

import { useState } from "react";
import {
  compareExperimentRuns,
  createExperimentRecord,
  getExperimentLatest,
  getExperimentRuns
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

function parseList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function ExperimentPanel({ baseUrl }: Props) {
  const [runIndex, setRunIndex] = useState<Record<string, unknown> | null>(null);
  const [experimentId, setExperimentId] = useState("latest_comparison");
  const [experimentName, setExperimentName] = useState("Synthetic DPABI Experiment");
  const [runIdsText, setRunIdsText] = useState("");
  const [tagsText, setTagsText] = useState("synthetic, dpabi");
  const [notes, setNotes] = useState("");
  const [record, setRecord] = useState<Record<string, unknown> | null>(null);
  const [comparison, setComparison] = useState<Record<string, unknown> | null>(null);
  const [latest, setLatest] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleLoadRuns() {
    setStatus("LOADING_RUNS");
    setError("");

    try {
      const result = await getExperimentRuns(baseUrl);
      setRunIndex(result);
      setStatus("RUNS_LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleCreateRecord() {
    setStatus("CREATING_RECORD");
    setError("");

    try {
      const result = await createExperimentRecord(baseUrl, {
        experiment_id: experimentId,
        name: experimentName,
        run_ids: parseList(runIdsText),
        tags: parseList(tagsText),
        notes
      });
      setRecord(result);
      setStatus("RECORD_CREATED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleCompareRuns() {
    setStatus("COMPARING");
    setError("");

    try {
      const result = await compareExperimentRuns(baseUrl, {
        experiment_id: experimentId,
        run_ids: parseList(runIdsText)
      });
      setComparison(result);
      setStatus("COMPARISON_READY");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleLoadLatest() {
    setError("");

    try {
      const result = await getExperimentLatest(baseUrl);
      setLatest(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div>
      <div className="row">
        <button onClick={handleLoadRuns}>扫描 Run Index</button>
        <button onClick={handleLoadLatest}>加载最新 Comparison</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="formGrid">
        <label>
          Experiment ID
          <input
            value={experimentId}
            onChange={(event) => setExperimentId(event.target.value)}
          />
        </label>

        <label>
          Name
          <input
            value={experimentName}
            onChange={(event) => setExperimentName(event.target.value)}
          />
        </label>

        <label>
          Run IDs
          <input
            placeholder="留空则默认比较最近 5 个 run"
            value={runIdsText}
            onChange={(event) => setRunIdsText(event.target.value)}
          />
        </label>

        <label>
          Tags
          <input
            value={tagsText}
            onChange={(event) => setTagsText(event.target.value)}
          />
        </label>
      </div>

      <label>
        Notes
        <textarea
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
        />
      </label>

      <div className="row">
        <button onClick={handleCreateRecord}>创建 Experiment Record</button>
        <button onClick={handleCompareRuns}>比较 Runs</button>
      </div>

      <h3>Run Index</h3>
      <JsonBlock value={runIndex} emptyText="尚未扫描 run index" />

      <h3>Experiment Record</h3>
      <JsonBlock value={record} emptyText="尚未创建 experiment record" />

      <h3>Comparison</h3>
      <JsonBlock value={comparison || latest?.latest_comparison} emptyText="尚未生成 comparison" />

      <h3>Comparison Report</h3>
      <TextViewer
        text={
          typeof latest?.latest_report === "string"
            ? latest.latest_report
            : null
        }
        emptyText="暂无 comparison report"
      />
    </div>
  );
}
8. 修改 frontend/src/App.tsx

新增导入：

import { ExperimentPanel } from "./components/ExperimentPanel";

在 Validation / Regression 或 DPABI Panel 后增加 Section：

<Section
  title="Experiment Tracking / Run Comparison"
  description="扫描 pipeline runs、创建实验记录，并比较多个运行结果。"
>
  <ExperimentPanel baseUrl={baseUrl} />
</Section>
9. 修改 frontend/src/styles.css

如果没有 textarea 样式，追加：

textarea {
  border: 1px solid #d2d8e8;
  border-radius: 10px;
  padding: 9px 12px;
  min-width: 280px;
  min-height: 90px;
  background: white;
  font-family: inherit;
}
10. 新增轻量测试

创建文件：

tests/unit/test_experiment_tracker.py

内容：

from __future__ import annotations

import json
from pathlib import Path

from backend.app.tools.experiment_tracker import (
    build_run_index,
    compare_experiment_runs,
    create_experiment_record,
)


def test_experiment_tracker_indexes_and_compares_runs(tmp_path: Path):
    work = tmp_path / "work"
    reports = tmp_path / "reports"

    run_dir = work / "pipeline_runs" / "run_test_001"
    run_dir.mkdir(parents=True)

    summary_path = run_dir / "summary.json"
    summary_path.write_text(
        json.dumps({
            "run_id": "run_test_001",
            "pipeline_id": "test_pipeline",
            "status": "SUCCESS",
            "duration_seconds": 1.23,
            "scheduler": {
                "mode": "sequential",
                "max_workers": 1,
                "matlab_max_workers": 1,
            },
            "nodes": [
                {
                    "id": "node_a",
                    "ok": True,
                    "outputs": ["a.json"],
                    "warnings": [],
                    "errors": [],
                }
            ],
        }),
        encoding="utf-8",
    )

    index = build_run_index(work_dir=str(work), report_dir=str(reports))

    assert index["ok"] is True
    assert index["runs_total"] == 1
    assert index["runs"][0]["run_id"] == "run_test_001"

    record = create_experiment_record(
        experiment_id="experiment_test",
        name="Test Experiment",
        run_ids=["run_test_001"],
        tags=["unit"],
        notes="test",
        work_dir=str(work),
    )

    assert record["ok"] is True

    comparison = compare_experiment_runs(
        experiment_id="experiment_test",
        run_ids=["run_test_001"],
        work_dir=str(work),
        report_dir=str(reports),
    )

    assert comparison["ok"] is True
    assert comparison["runs_compared"] == 1
    assert comparison["rows"][0]["status"] == "SUCCESS"

    assert (reports / "experiments" / "experiment_test_comparison.json").exists()
    assert (reports / "experiments" / "experiment_test_comparison_report.md").exists()
11. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

call("GET", "/api/experiments/runs")
call("GET", "/api/experiments/latest")

不要在 smoke test 中自动创建 experiment record 或 comparison。

12. 更新 README.md

追加第二十八步说明：

## Step 28: Experiment Tracking and Run Comparison

This step adds multi-run experiment tracking.

It supports:

- scanning pipeline run summaries
- scanning DPABI template instance summaries
- indexing report artifacts
- creating experiment records
- comparing selected runs
- generating comparison JSON and Markdown report
- frontend run comparison dashboard

It does not execute pipelines.

### Build Run Index

```bash
python -m backend.app.tools.run_experiment_tracker_cli

Expected output:

work/experiments/run_index.json
Compare Latest Runs
python -m backend.app.tools.run_experiment_tracker_cli --compare

Expected outputs:

reports/experiments/latest_comparison_comparison.json
reports/experiments/latest_comparison_comparison_report.md
API
curl http://127.0.0.1:8000/api/experiments/runs
curl http://127.0.0.1:8000/api/experiments/latest

Create experiment record:

curl -X POST http://127.0.0.1:8000/api/experiments/records \
  -H "Content-Type: application/json" \
  -d '{
    "experiment_id": "experiment_001",
    "name": "Synthetic DPABI Experiment",
    "run_ids": ["run_dpabi_subject_wrapper_001"],
    "tags": ["synthetic", "dpabi"],
    "notes": "Compare DPABI wrapper runs."
  }'

Compare runs:

curl -X POST http://127.0.0.1:8000/api/experiments/compare \
  -H "Content-Type: application/json" \
  -d '{
    "experiment_id": "experiment_001",
    "run_ids": ["run_dpabi_subject_wrapper_001"]
  }'
Frontend

Use:

Experiment Tracking / Run Comparison
Safety

This step:

does not execute pipelines
does not launch MATLAB
does not run DPABI
does not call DPARSF_run
does not call DPARSFA_run
does not call DPABI GUI
does not modify rawdata
13. 验收标准

完成后确认新增或修改了这些文件：

specs/experiment_tracking_spec.md
backend/app/tools/experiment_tracker.py
backend/app/tools/run_experiment_tracker_cli.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/ExperimentPanel.tsx
frontend/src/App.tsx
frontend/src/styles.css
tests/unit/test_experiment_tracker.py
backend/app/tools/api_smoke_test.py
README.md

先确保已经有至少一个 pipeline summary：

python -m backend.app.tools.run_validation_cli

然后运行：

python -m backend.app.tools.run_experiment_tracker_cli

应生成：

work/experiments/run_index.json

再运行：

python -m backend.app.tools.run_experiment_tracker_cli --compare

应生成：

reports/experiments/latest_comparison_comparison.json
reports/experiments/latest_comparison_comparison_report.md

运行测试：

python -m pytest tests/unit/test_experiment_tracker.py -q

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl http://127.0.0.1:8000/api/experiments/runs
curl http://127.0.0.1:8000/api/experiments/latest

启动前端：

cd frontend
npm run dev

页面应该能完成：

显示 Experiment Tracking / Run Comparison 区域。
点击扫描 Run Index。
显示所有 pipeline runs。
可以输入 experiment_id。
可以输入 run_ids。
可以创建 experiment record。
可以比较多个 run。
可以显示 comparison JSON。
可以显示 comparison Markdown report。
不执行任何 pipeline。
不启动 MATLAB。
不运行 DPABI。
不修改 rawdata。
14. 重要限制

本步骤只做 experiment tracking 和 run comparison。

不要实现：

自动运行 pipeline
自动调参
自动实验搜索
MLflow 替代品
数据库
WebSocket 实时对比
真实医学影像处理
DPABI 全流程执行
DPARSF_run 自动执行
DPARSFA_run 自动执行
修改 rawdata
删除文件

完成后请总结：

新增了哪些文件
修改了哪些文件
run index 扫描哪些来源
experiment record 记录哪些字段
comparison report 比较哪些指标
为什么本步骤不执行 pipeline
下一步如何做 experiment dashboard 的图表化和趋势分析

'''
Step 28 主要实现的是：

## Multi-Run Experiment Tracking + Comparison Dashboard 闭环
### 核心目标
实现一个统一的实验追踪系统，用于索引和比较 Pipeline 运行结果。

### 主要功能
1. 扫描所有运行结果
   
   - 扫描 work/pipeline_runs/*/summary.json - Pipeline 运行摘要
   - 扫描 work/dpabi/template_instances/*/execution_summary.json - DPABI 模板实例执行摘要
   - 扫描各类报告：
     - reports/dataset_evaluation/* - 数据集评估报告
     - reports/gpu_benchmark/* - GPU 基准测试报告
     - reports/dpabi/* - DPABI 相关报告
     - reports/validation/* - 验证报告
2. 生成统一 Run Index
   
   - 创建 work/experiments/run_index.json
   - 包含所有 run 的元数据（ID、类型、状态、持续时间、调度器配置等）
   - 包含节点统计（总数、成功、失败）
   - 包含输出、警告、错误计数
3. 创建实验记录
   
   - 支持为实验命名
   - 关联多个 run
   - 添加 tags 和 notes
   - 保存到 work/experiments/records/{experiment_id}.json
4. Run 比较
   
   - 并排比较多个 run 的关键指标
   - 比较状态、持续时间、调度器、节点状态、输出数量
   - 生成 comparison JSON
   - 生成 Markdown 比较报告
   - 支持默认比较最近 5 个 run
5. 后端 API
   
   - /api/experiments/run-index - 获取 run 索引
   - /api/experiments/record - 创建实验记录
   - /api/experiments/compare - 比较 runs
   - /api/experiments/record/{id} - 获取实验记录
   - /api/experiments/comparison/{id} - 获取比较结果
6. 前端 Dashboard
   
   - Run Index 表格展示
   - 报告产物状态指示
   - Run 选择（复选框）
   - 实验记录创建表单
   - 比较结果表格
   - 可视化状态指示器
### 安全规则
- 只读扫描 - 仅读取现有产物，不执行任何操作
- 不执行 Pipeline
- 不启动 MATLAB
- 不运行 DPABI
- 不修改 rawdata
- 不修改 DPABI 源码
- 不删除文件
### 解决的问题
当前系统产生了很多分散的结果文件，缺少统一的实验追踪、run 索引、run 比较和可视化 dashboard。本步骤将这些分散的结果整合到一个统一的追踪系统中。
'''