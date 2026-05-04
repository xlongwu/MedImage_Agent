你是我的工程搭建助手。前二十八步已经完成：

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
Step 28：完成 Multi-Run Experiment Tracking + Comparison Dashboard 闭环。

现在开始第二十九步。

第二十九步目标：实现“Experiment Dashboard 图表化 + 趋势分析闭环”。

当前系统已经可以：

- 扫描 pipeline runs
- 创建 experiment record
- 比较多个 run
- 生成 comparison JSON / Markdown
- 前端显示 run index 和 comparison

但目前 dashboard 主要是 JSON 文本，还缺少图表化和趋势分析能力。

本步骤要实现：

- 从 run_index.json 中提取 dashboard metrics
- 生成 run duration trend
- 生成 success/failure trend
- 生成 pipeline 类型分布
- 生成 scheduler 使用分布
- 生成 errors/warnings trend
- 生成 outputs count trend
- 生成 dashboard_data.json
- 生成 dashboard_data.csv
- 生成 dashboard_report.md
- 后端 API 暴露 dashboard 数据
- 前端增加图表化 dashboard
- 不依赖额外图表库，先用纯 React + SVG 实现简单图表
- validation suite 增加 dashboard data 轻量测试

本步骤只做读取、聚合、可视化，不执行新的 pipeline。
本步骤不要启动 MATLAB。
本步骤不要运行 DPABI。
本步骤不要运行 DPARSF_run / DPARSFA_run。
本步骤不要调用 DPABI GUI。
本步骤不要处理真实医学影像数据。
本步骤不要修改 rawdata。
本步骤不要修改 DPABI 源码。
本步骤不要删除文件。

---

## 1. 创建 specs/experiment_dashboard_spec.md

创建文件：

```text
specs/experiment_dashboard_spec.md

内容：

# Experiment Dashboard Specification

This document defines the MVP experiment dashboard and trend analytics layer.

## Goals

The dashboard should turn indexed run records into visual and summary metrics.

It should provide:

- run count summary
- status distribution
- pipeline distribution
- run duration trend
- scheduler usage distribution
- node success/failure trend
- warning/error trend
- output count trend
- latest run table

## Scope

Supported in this step:

- read work/experiments/run_index.json
- generate dashboard_data.json
- generate dashboard_data.csv
- generate dashboard_report.md
- API endpoint for dashboard data
- frontend visualization using React and SVG
- lightweight unit test

Unsupported in this step:

- running pipelines
- launching MATLAB
- running DPABI
- running DPARSF_run
- running DPARSFA_run
- real medical image processing
- rawdata modification
- DPABI source modification
- deletion of files
- production analytics database

## Outputs

```text
work/experiments/dashboard_data.json
work/experiments/dashboard_data.csv
reports/experiments/dashboard_report.md
Dashboard Metrics
runs_total
success_total
failed_total
partial_total
unknown_total
mean_duration_seconds
median_duration_seconds
max_duration_seconds
total_outputs
total_warnings
total_errors
status_distribution
pipeline_distribution
scheduler_distribution
duration_trend
error_warning_trend
output_trend
Safety Rules
Do not execute pipelines.
Do not launch MATLAB.
Do not run DPABI.
Do not modify rawdata.
Do not modify DPABI source.
Do not delete files.
Read and summarize existing artifacts only.

---

## 2. 创建 backend/app/tools/experiment_dashboard.py

创建文件：

```text
backend/app/tools/experiment_dashboard.py

目标：读取 run_index.json，生成 dashboard metrics、CSV 和 Markdown report。

提供函数：

build_experiment_dashboard(
    work_dir: str = "./work",
    report_dir: str = "./reports",
    refresh_index: bool = True,
) -> dict

输出：

work/experiments/dashboard_data.json
work/experiments/dashboard_data.csv
reports/experiments/dashboard_report.md

要求：

如果 refresh_index=true，先调用 build_run_index。
如果 run_index.json 不存在，自动生成。
不执行 pipeline。
不启动 MATLAB。
只读已有 summary / report artifacts。
dashboard_data.json 要适合前端直接渲染。
CSV 至少包含：
run_id
run_type
pipeline_id
status
duration_seconds
scheduler_mode
nodes_total
nodes_success
nodes_failed
outputs_count
warnings_count
errors_count

参考实现：

from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import mean, median
from typing import Any

from backend.app.tools.experiment_tracker import build_run_index


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _safe_number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _normalize_status(status: Any) -> str:
    value = str(status or "UNKNOWN").upper()
    if value in {"SUCCESS", "OK", "COMPLETED"}:
        return "SUCCESS"
    if value in {"FAILED", "ERROR"}:
        return "FAILED"
    if value in {"PARTIAL", "WARNING"}:
        return "PARTIAL"
    if value in {"INVALID"}:
        return "INVALID"
    return "UNKNOWN"


def _count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in items:
        value = str(item.get(key) or "unknown")
        out[value] = out.get(value, 0) + 1
    return dict(sorted(out.items(), key=lambda x: x[0]))


def _trend_rows(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []

    for index, run in enumerate(reversed(runs)):
        status = _normalize_status(run.get("status"))
        rows.append({
            "index": index + 1,
            "run_id": run.get("run_id"),
            "run_type": run.get("run_type"),
            "pipeline_id": run.get("pipeline_id"),
            "status": status,
            "success": 1 if status == "SUCCESS" else 0,
            "failed": 1 if status == "FAILED" else 0,
            "partial": 1 if status == "PARTIAL" else 0,
            "duration_seconds": _safe_number(run.get("duration_seconds")),
            "nodes_total": int(_safe_number(run.get("nodes_total"))),
            "nodes_success": int(_safe_number(run.get("nodes_success"))),
            "nodes_failed": int(_safe_number(run.get("nodes_failed"))),
            "outputs_count": int(_safe_number(run.get("outputs_count"))),
            "warnings_count": int(_safe_number(run.get("warnings_count"))),
            "errors_count": int(_safe_number(run.get("errors_count"))),
            "scheduler_mode": run.get("scheduler_mode") or "unknown",
        })

    return rows


def build_experiment_dashboard(
    work_dir: str = "./work",
    report_dir: str = "./reports",
    refresh_index: bool = True,
) -> dict[str, Any]:
    work = Path(work_dir)
    reports = Path(report_dir)

    experiments_dir = work / "experiments"
    experiments_dir.mkdir(parents=True, exist_ok=True)

    report_out = reports / "experiments"
    report_out.mkdir(parents=True, exist_ok=True)

    if refresh_index:
        index = build_run_index(work_dir=work_dir, report_dir=report_dir)
    else:
        index = _read_json(experiments_dir / "run_index.json")
        if not index:
            index = build_run_index(work_dir=work_dir, report_dir=report_dir)

    runs = index.get("runs", []) if index else []
    trend = _trend_rows(runs)

    durations = [
        row["duration_seconds"]
        for row in trend
        if row["duration_seconds"] is not None
    ]

    statuses = [_normalize_status(run.get("status")) for run in runs]

    success_total = sum(1 for item in statuses if item == "SUCCESS")
    failed_total = sum(1 for item in statuses if item == "FAILED")
    partial_total = sum(1 for item in statuses if item == "PARTIAL")
    invalid_total = sum(1 for item in statuses if item == "INVALID")
    unknown_total = sum(1 for item in statuses if item == "UNKNOWN")

    total_outputs = sum(row["outputs_count"] for row in trend)
    total_warnings = sum(row["warnings_count"] for row in trend)
    total_errors = sum(row["errors_count"] for row in trend)

    status_distribution: dict[str, int] = {}
    for status in statuses:
        status_distribution[status] = status_distribution.get(status, 0) + 1

    pipeline_distribution = _count_by(runs, "pipeline_id")
    scheduler_distribution = _count_by(runs, "scheduler_mode")
    run_type_distribution = _count_by(runs, "run_type")

    dashboard = {
        "ok": True,
        "node_id": "experiment_dashboard",
        "backend": "python",
        "runs_total": len(runs),
        "success_total": success_total,
        "failed_total": failed_total,
        "partial_total": partial_total,
        "invalid_total": invalid_total,
        "unknown_total": unknown_total,
        "mean_duration_seconds": mean(durations) if durations else None,
        "median_duration_seconds": median(durations) if durations else None,
        "max_duration_seconds": max(durations) if durations else None,
        "total_outputs": total_outputs,
        "total_warnings": total_warnings,
        "total_errors": total_errors,
        "status_distribution": status_distribution,
        "pipeline_distribution": pipeline_distribution,
        "scheduler_distribution": scheduler_distribution,
        "run_type_distribution": run_type_distribution,
        "duration_trend": [
            {
                "index": row["index"],
                "run_id": row["run_id"],
                "duration_seconds": row["duration_seconds"],
                "status": row["status"],
            }
            for row in trend
        ],
        "error_warning_trend": [
            {
                "index": row["index"],
                "run_id": row["run_id"],
                "warnings_count": row["warnings_count"],
                "errors_count": row["errors_count"],
            }
            for row in trend
        ],
        "output_trend": [
            {
                "index": row["index"],
                "run_id": row["run_id"],
                "outputs_count": row["outputs_count"],
            }
            for row in trend
        ],
        "runs": trend,
        "artifacts": index.get("artifacts", []) if index else [],
        "warnings": index.get("warnings", []) if index else [],
        "errors": index.get("errors", []) if index else [],
    }

    json_path = experiments_dir / "dashboard_data.json"
    csv_path = experiments_dir / "dashboard_data.csv"
    report_path = report_out / "dashboard_report.md"

    json_path.write_text(
        json.dumps(dashboard, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    fieldnames = [
        "index",
        "run_id",
        "run_type",
        "pipeline_id",
        "status",
        "duration_seconds",
        "scheduler_mode",
        "nodes_total",
        "nodes_success",
        "nodes_failed",
        "outputs_count",
        "warnings_count",
        "errors_count",
    ]

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in trend:
            writer.writerow({key: row.get(key) for key in fieldnames})

    lines = []
    lines.append("# Experiment Dashboard Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Runs total: {dashboard['runs_total']}")
    lines.append(f"- Success: {success_total}")
    lines.append(f"- Failed: {failed_total}")
    lines.append(f"- Partial: {partial_total}")
    lines.append(f"- Invalid: {invalid_total}")
    lines.append(f"- Unknown: {unknown_total}")
    lines.append(f"- Mean duration seconds: {dashboard['mean_duration_seconds']}")
    lines.append(f"- Total outputs: {total_outputs}")
    lines.append(f"- Total warnings: {total_warnings}")
    lines.append(f"- Total errors: {total_errors}")
    lines.append("")
    lines.append("## Status Distribution")
    lines.append("")
    for key, value in status_distribution.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Pipeline Distribution")
    lines.append("")
    for key, value in pipeline_distribution.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Latest Runs")
    lines.append("")
    if trend:
        lines.append("| Index | Run ID | Pipeline | Status | Duration | Errors | Warnings |")
        lines.append("|---:|---|---|---|---:|---:|---:|")
        for row in trend[-10:]:
            lines.append(
                f"| {row['index']} | {row['run_id']} | {row['pipeline_id']} | "
                f"{row['status']} | {row['duration_seconds']} | "
                f"{row['errors_count']} | {row['warnings_count']} |"
            )
    else:
        lines.append("No runs found.")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This dashboard only summarizes existing artifacts. It does not execute pipelines or MATLAB.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    dashboard["outputs"] = [str(json_path), str(csv_path), str(report_path)]
    return dashboard
3. 创建 backend/app/tools/run_experiment_dashboard_cli.py

创建文件：

backend/app/tools/run_experiment_dashboard_cli.py

内容：

from __future__ import annotations

import json

from backend.app.tools.experiment_dashboard import build_experiment_dashboard


def main() -> int:
    result = build_experiment_dashboard()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
4. 修改 backend/app/api/routes.py

新增 API：

GET /api/experiments/dashboard
POST /api/experiments/dashboard/refresh

新增导入：

from backend.app.tools.experiment_dashboard import build_experiment_dashboard

新增路由：

@router.get("/api/experiments/dashboard")
def api_get_experiment_dashboard() -> dict[str, Any]:
    base = Path("work") / "experiments"
    report_base = Path("reports") / "experiments"

    dashboard = _read_json_if_exists(base / "dashboard_data.json")
    dashboard_csv = _read_text_if_exists(base / "dashboard_data.csv")
    dashboard_report = _read_text_if_exists(report_base / "dashboard_report.md")

    if dashboard is None:
        dashboard = build_experiment_dashboard(
            work_dir="./work",
            report_dir="./reports",
            refresh_index=True,
        )

    return {
        "ok": True,
        "dashboard": dashboard,
        "dashboard_csv": dashboard_csv,
        "dashboard_report": dashboard_report,
    }


@router.post("/api/experiments/dashboard/refresh")
def api_refresh_experiment_dashboard() -> dict[str, Any]:
    result = build_experiment_dashboard(
        work_dir="./work",
        report_dir="./reports",
        refresh_index=True,
    )

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)

    return result
5. 修改 frontend/src/api.ts

新增：

export async function getExperimentDashboard(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/experiments/dashboard"
  );
}

export async function refreshExperimentDashboard(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/experiments/dashboard/refresh",
    { method: "POST" }
  );
}
6. 创建 frontend/src/components/SimpleCharts.tsx

创建文件：

frontend/src/components/SimpleCharts.tsx

内容：

type BarDatum = {
  label: string;
  value: number;
};

type LineDatum = {
  label: string;
  value: number;
};

type Props = {
  title: string;
};

export function SimpleBarChart({
  title,
  data
}: Props & { data: BarDatum[] }) {
  const maxValue = Math.max(...data.map((item) => item.value), 1);

  return (
    <div className="chartCard">
      <h4>{title}</h4>
      <div className="barChart">
        {data.map((item) => (
          <div className="barRow" key={item.label}>
            <div className="barLabel">{item.label}</div>
            <div className="barTrack">
              <div
                className="barFill"
                style={{ width: `${(item.value / maxValue) * 100}%` }}
              />
            </div>
            <div className="barValue">{item.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SimpleLineChart({
  title,
  data
}: Props & { data: LineDatum[] }) {
  const width = 520;
  const height = 180;
  const padding = 24;
  const maxValue = Math.max(...data.map((item) => item.value), 1);
  const minValue = Math.min(...data.map((item) => item.value), 0);
  const span = Math.max(maxValue - minValue, 1);

  const points = data.map((item, index) => {
    const x =
      data.length === 1
        ? width / 2
        : padding + (index / (data.length - 1)) * (width - padding * 2);
    const y =
      height -
      padding -
      ((item.value - minValue) / span) * (height - padding * 2);

    return { x, y, label: item.label, value: item.value };
  });

  const path = points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`)
    .join(" ");

  return (
    <div className="chartCard">
      <h4>{title}</h4>
      <svg viewBox={`0 0 ${width} ${height}`} className="lineChart">
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} />
        <line x1={padding} y1={padding} x2={padding} y2={height - padding} />
        <path d={path} fill="none" stroke="currentColor" strokeWidth="2" />
        {points.map((point) => (
          <circle key={`${point.label}-${point.x}`} cx={point.x} cy={point.y} r="3" />
        ))}
      </svg>
      <div className="chartHint">
        {data.length} points · max {maxValue}
      </div>
    </div>
  );
}
7. 创建 frontend/src/components/ExperimentDashboard.tsx

创建文件：

frontend/src/components/ExperimentDashboard.tsx

内容：

import { useState } from "react";
import {
  getExperimentDashboard,
  refreshExperimentDashboard
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { SimpleBarChart, SimpleLineChart } from "./SimpleCharts";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

function objectToBars(value: unknown) {
  if (!value || typeof value !== "object") return [];

  return Object.entries(value as Record<string, unknown>).map(([key, val]) => ({
    label: key,
    value: Number(val) || 0
  }));
}

function trendToLine(value: unknown, key: string) {
  if (!Array.isArray(value)) return [];

  return value.map((item: any) => ({
    label: String(item.run_id || item.index),
    value: Number(item[key]) || 0
  }));
}

export function ExperimentDashboard({ baseUrl }: Props) {
  const [payload, setPayload] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleLoadDashboard() {
    setStatus("LOADING");
    setError("");

    try {
      const result = await getExperimentDashboard(baseUrl);
      setPayload(result);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleRefreshDashboard() {
    setStatus("REFRESHING");
    setError("");

    try {
      const result = await refreshExperimentDashboard(baseUrl);
      setPayload({
        ok: true,
        dashboard: result
      });
      setStatus("REFRESHED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const dashboard = payload?.dashboard as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button onClick={handleLoadDashboard}>加载 Dashboard</button>
        <button onClick={handleRefreshDashboard}>刷新 Dashboard</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="metricGrid">
        <div className="metricCard">
          <span>Runs</span>
          <strong>{String(dashboard?.runs_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Success</span>
          <strong>{String(dashboard?.success_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Failed</span>
          <strong>{String(dashboard?.failed_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Total Errors</span>
          <strong>{String(dashboard?.total_errors ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Total Warnings</span>
          <strong>{String(dashboard?.total_warnings ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Mean Duration</span>
          <strong>
            {dashboard?.mean_duration_seconds == null
              ? "-"
              : Number(dashboard.mean_duration_seconds).toFixed(2)}
          </strong>
        </div>
      </div>

      <div className="chartGrid">
        <SimpleBarChart
          title="Status Distribution"
          data={objectToBars(dashboard?.status_distribution)}
        />

        <SimpleBarChart
          title="Pipeline Distribution"
          data={objectToBars(dashboard?.pipeline_distribution)}
        />

        <SimpleBarChart
          title="Scheduler Distribution"
          data={objectToBars(dashboard?.scheduler_distribution)}
        />

        <SimpleLineChart
          title="Duration Trend"
          data={trendToLine(dashboard?.duration_trend, "duration_seconds")}
        />

        <SimpleLineChart
          title="Error Trend"
          data={trendToLine(dashboard?.error_warning_trend, "errors_count")}
        />

        <SimpleLineChart
          title="Output Trend"
          data={trendToLine(dashboard?.output_trend, "outputs_count")}
        />
      </div>

      <h3>Dashboard JSON</h3>
      <JsonBlock value={dashboard} emptyText="尚未加载 dashboard" />

      <h3>Dashboard CSV</h3>
      <TextViewer
        text={
          typeof payload?.dashboard_csv === "string"
            ? payload.dashboard_csv
            : null
        }
        emptyText="暂无 dashboard CSV"
      />

      <h3>Dashboard Report</h3>
      <TextViewer
        text={
          typeof payload?.dashboard_report === "string"
            ? payload.dashboard_report
            : null
        }
        emptyText="暂无 dashboard report"
      />
    </div>
  );
}
8. 修改 frontend/src/App.tsx

新增导入：

import { ExperimentDashboard } from "./components/ExperimentDashboard";

在 Experiment Tracking / Run Comparison section 后面增加：

<Section
  title="Experiment Dashboard / Trend Analytics"
  description="图表化展示 run 状态、耗时、错误、warning、输出数量和 pipeline 分布。"
>
  <ExperimentDashboard baseUrl={baseUrl} />
</Section>
9. 修改 frontend/src/styles.css

追加：

.metricGrid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  margin: 16px 0;
}

.metricCard {
  border: 1px solid #e1e6f2;
  border-radius: 14px;
  padding: 14px;
  background: #ffffff;
  box-shadow: 0 1px 4px rgba(20, 40, 80, 0.04);
}

.metricCard span {
  display: block;
  font-size: 12px;
  color: #667085;
  margin-bottom: 6px;
}

.metricCard strong {
  font-size: 24px;
}

.chartGrid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
  margin: 16px 0;
}

.chartCard {
  border: 1px solid #e1e6f2;
  border-radius: 14px;
  padding: 14px;
  background: #ffffff;
  box-shadow: 0 1px 4px rgba(20, 40, 80, 0.04);
}

.barChart {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.barRow {
  display: grid;
  grid-template-columns: 110px 1fr 50px;
  align-items: center;
  gap: 8px;
}

.barLabel {
  font-size: 12px;
  color: #475467;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.barTrack {
  height: 10px;
  border-radius: 999px;
  background: #eef2f8;
  overflow: hidden;
}

.barFill {
  height: 100%;
  background: #64748b;
  border-radius: 999px;
}

.barValue {
  font-size: 12px;
  text-align: right;
  color: #475467;
}

.lineChart {
  width: 100%;
  height: 180px;
  color: #475467;
}

.lineChart line {
  stroke: #d0d5dd;
}

.lineChart circle {
  fill: currentColor;
}

.chartHint {
  font-size: 12px;
  color: #667085;
}
10. 新增轻量测试

创建文件：

tests/unit/test_experiment_dashboard.py

内容：

from __future__ import annotations

import json
from pathlib import Path

from backend.app.tools.experiment_dashboard import build_experiment_dashboard


def test_experiment_dashboard_builds_metrics(tmp_path: Path):
    work = tmp_path / "work"
    reports = tmp_path / "reports"

    run_dir = work / "pipeline_runs" / "run_test_001"
    run_dir.mkdir(parents=True)

    (run_dir / "summary.json").write_text(
        json.dumps({
            "run_id": "run_test_001",
            "pipeline_id": "test_pipeline",
            "status": "SUCCESS",
            "duration_seconds": 2.5,
            "scheduler": {
                "mode": "sequential",
                "max_workers": 1,
                "matlab_max_workers": 1,
            },
            "nodes": [
                {
                    "id": "node_a",
                    "ok": True,
                    "outputs": ["a.json", "b.json"],
                    "warnings": ["warn"],
                    "errors": [],
                }
            ],
        }),
        encoding="utf-8",
    )

    result = build_experiment_dashboard(
        work_dir=str(work),
        report_dir=str(reports),
        refresh_index=True,
    )

    assert result["ok"] is True
    assert result["runs_total"] == 1
    assert result["success_total"] == 1
    assert result["total_outputs"] == 2
    assert result["total_warnings"] == 1
    assert result["total_errors"] == 0

    assert (work / "experiments" / "dashboard_data.json").exists()
    assert (work / "experiments" / "dashboard_data.csv").exists()
    assert (reports / "experiments" / "dashboard_report.md").exists()
11. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

call("GET", "/api/experiments/dashboard")

不要在 smoke test 中调用 POST refresh，避免写入不必要文件。

12. 更新 README.md

追加第二十九步说明：

## Step 29: Experiment Dashboard and Trend Analytics

This step adds a visual dashboard for experiment tracking.

It supports:

- run count summary
- status distribution
- pipeline distribution
- scheduler distribution
- duration trend
- error/warning trend
- output count trend
- dashboard JSON
- dashboard CSV
- dashboard Markdown report
- frontend SVG charts

It does not execute pipelines.

### Build Dashboard

```bash
python -m backend.app.tools.run_experiment_dashboard_cli

Expected outputs:

work/experiments/dashboard_data.json
work/experiments/dashboard_data.csv
reports/experiments/dashboard_report.md
API
curl http://127.0.0.1:8000/api/experiments/dashboard

Refresh:

curl -X POST http://127.0.0.1:8000/api/experiments/dashboard/refresh
Frontend

Use:

Experiment Dashboard / Trend Analytics
Safety

This step:

does not execute pipelines
does not launch MATLAB
does not run DPABI
does not call DPARSF_run
does not call DPARSFA_run
does not call DPABI GUI
does not modify rawdata

---

## 13. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/experiment_dashboard_spec.md
backend/app/tools/experiment_dashboard.py
backend/app/tools/run_experiment_dashboard_cli.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/SimpleCharts.tsx
frontend/src/components/ExperimentDashboard.tsx
frontend/src/App.tsx
frontend/src/styles.css
tests/unit/test_experiment_dashboard.py
backend/app/tools/api_smoke_test.py
README.md

先确保有至少一个 run：

python -m backend.app.tools.run_validation_cli

然后运行：

python -m backend.app.tools.run_experiment_dashboard_cli

应生成：

work/experiments/dashboard_data.json
work/experiments/dashboard_data.csv
reports/experiments/dashboard_report.md

运行测试：

python -m pytest tests/unit/test_experiment_dashboard.py -q

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl http://127.0.0.1:8000/api/experiments/dashboard
curl -X POST http://127.0.0.1:8000/api/experiments/dashboard/refresh

启动前端：

cd frontend
npm run dev

页面应该能完成：

显示 Experiment Dashboard / Trend Analytics 区域。
点击加载 Dashboard。
显示 runs_total、success_total、failed_total、warnings、errors 等指标卡。
显示 status distribution。
显示 pipeline distribution。
显示 scheduler distribution。
显示 duration trend。
显示 error trend。
显示 output trend。
显示 dashboard JSON。
显示 dashboard CSV。
显示 dashboard report。
不执行任何 pipeline。
不启动 MATLAB。
不运行 DPABI。
不修改 rawdata。
14. 重要限制

本步骤只做 experiment dashboard 和趋势分析。

不要实现：

自动运行 pipeline
自动调参
生产级数据库
MLflow 替代
WebSocket 实时图表
权限系统
真实医学影像处理
DPABI 全流程执行
DPARSF_run 自动执行
DPARSFA_run 自动执行
修改 rawdata
删除文件

完成后请总结：

新增了哪些文件
修改了哪些文件
dashboard 聚合哪些数据
前端用了哪些图表
为什么本步骤不执行 pipeline
当前 dashboard 的限制
下一步如何做 run artifact browser / file preview

'''
Step 29 主要实现的是：

## Experiment Dashboard 图表化 + 趋势分析闭环
### 核心目标
将已有的 run index 数据转化为可视化的图表和趋势分析，让实验追踪从纯文本 JSON 升级为图形化 Dashboard。

### 主要功能
1. Dashboard 数据生成
   
   - 读取 work/experiments/run_index.json
   - 从所有 run 中提取指标
   - 生成汇总统计信息
   - 创建趋势数据
   - 输出 JSON、CSV 和 Markdown 报告
2. 指标计算
   
   - 总运行数 (runs_total)
   - 成功/失败/部分/无效/未知状态分布
   - 平均/中位数/最大持续时间
   - 总输出数、警告数、错误数
   - 状态分布 (status_distribution)
   - Pipeline 分布 (pipeline_distribution)
   - 调度器分布 (scheduler_distribution)
   - 运行类型分布 (run_type_distribution)
3. 趋势分析
   
   - 持续时间趋势 (duration_trend)
   - 错误/警告趋势 (error_warning_trend)
   - 输出数量趋势 (output_trend)
4. 可视化图表 (React + SVG)
   
   - 饼图 - 状态分布
   - 条形图 - Pipeline/调度器/类型分布
   - 折线图 - 持续时间趋势
   - 汇总卡片 - 关键指标
   - 最新运行表格 - 最近 10 个 run 的详细信息
### 解决的问题
当前系统已经能够：

- 扫描 pipeline runs
- 创建 experiment record
- 比较多个 run
- 生成 comparison JSON / Markdown
但 Dashboard 主要是 JSON 文本， 缺少图表化和趋势分析能力 。本步骤将这些数据转化为直观的可视化图表。

### 安全规则
- 只读扫描 - 仅读取现有产物，不执行任何操作
- 不执行 Pipeline
- 不启动 MATLAB
- 不运行 DPABI
- 不修改 rawdata
- 不修改 DPABI 源码
- 不删除文件
### 工作流程
1. 扫描 - 读取 run_index.json
2. 聚合 - 计算指标和趋势
3. 生成 - 创建 JSON、CSV、Markdown 输出
4. 可视化 - 在前端渲染图表
5. 分析 - 查看趋势和分布
'''