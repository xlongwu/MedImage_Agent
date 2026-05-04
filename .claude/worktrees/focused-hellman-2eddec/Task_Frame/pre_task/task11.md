你是我的工程搭建助手。前十步已经完成：

Step 1：完成项目工程骨架，并打通 MATLAB / SPM / DPABI 环境检查闭环。
Step 2：完成单节点执行闭环，可以运行一个 SPM smoke test 节点。
Step 3：完成最小 Pipeline DAG 执行闭环。
Step 4：完成 synthetic BIDS-like 数据集扫描与索引闭环。
Step 5：完成 synthetic subject-level SPM smoothing + QC 闭环。
Step 6：完成数据集级评估与 Markdown/HTML 报告闭环。
Step 7：完成 deterministic Agent Runtime、Plan Mode、Execute Mode、Tool Registry、Hook Manager 和 approval 机制。
Step 8：完成最小长期记忆、后台复盘和错误知识库闭环。
Step 9：完成最小 FastAPI 后端服务闭环。
Step 10：完成最小 React 前端闭环，可以查看配置、pipeline、生成 plan、批准执行、查看报告。

现在开始第十一步。

第十一步目标：实现“Run Monitor + State / Log Viewer 闭环”。

当前前端可以执行 pipeline，但缺少清晰的运行状态视图。  
本步骤要让用户可以在 Web UI 中查看：

- pipeline run summary
- project-level node states
- subject-level node states
- 每个 subject 的节点状态
- stdout / stderr 日志路径
- 安全读取日志内容
- 失败节点的 errors / warnings / metrics
- dataset evaluation 状态
- background review 状态

本步骤只做基于已有 JSON / log 文件的读取和展示。  
不要实现 WebSocket。
不要实现实时流式日志。
不要实现数据库。
不要实现异步队列。
不要实现复杂调度。
不要实现真实 LLM。
不要实现多 Agent 对话。
不要实现 GPU。
不要实现 DPABI pipeline。
不要修改 SPM / DPABI 源码。
不要删除文件。
不要开放任意文件读取。

---

## 1. 创建 specs/run_monitor_spec.md

创建文件：

```text
specs/run_monitor_spec.md

内容：

# Run Monitor Specification

This document defines the MVP run monitor for MedImage Agent.

## Goals

The Run Monitor helps users inspect completed or partially completed pipeline runs.

It should show:

- pipeline summary
- project-level node states
- subject-level node states
- subject-level success/failure
- logs paths
- errors and warnings
- node outputs
- node metrics

## Scope

Supported:

- Read run summary JSON
- Read node state JSON files
- Read safe log files through backend allowlist
- Display run status in frontend
- Display subject-level state table
- Display selected state detail
- Display stdout/stderr logs when available

Unsupported:

- WebSocket streaming
- real-time log tail
- database-backed run history
- parallel execution visualization
- task cancellation
- retry from UI
- editing state files
- deleting outputs

## State Locations

Pipeline summary:

```text
work/pipeline_runs/{run_id}/summary.json

Project-level states:

work/states/{run_id}/{node_id}.json

Subject-level states:

work/states/{run_id}/{subject_id}/{node_id}.json

Agent run summary:

work/agent_runs/{agent_run_id}/agent_summary.json

Background review:

work/agent_runs/{agent_run_id}/review_summary.md
work/agent_runs/{agent_run_id}/proposed_memory_patch.md
Safety Rules
The monitor is read-only.
It must not modify state files.
It must not delete logs.
It must use safe file reading.
It must not expose raw medical images.
It must not read arbitrary system files.

---

## 2. 创建 backend/app/runtime/run_inspector.py

创建文件：

```text
backend/app/runtime/run_inspector.py

目标：读取 run summary 和 state 文件，生成结构化运行状态。

功能要求：

提供函数：
inspect_run(run_id: str, work_dir: str = "./work") -> dict
list_available_runs(work_dir: str = "./work") -> dict
read_state_detail(run_id: str, state_path: str, work_dir: str = "./work") -> dict
读取：
work/pipeline_runs/{run_id}/summary.json
work/states/{run_id}/ 下所有 .json
区分：
project_states
subject_states
subject_states 按 subject_id 分组。
不要读取 rawdata。
不要读取 NIfTI。
只读取 JSON。
所有缺失文件返回 warnings，不要崩溃。

参考实现：

from __future__ import annotations

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


def list_available_runs(work_dir: str = "./work") -> dict[str, Any]:
    root = Path(work_dir) / "pipeline_runs"
    if not root.exists():
        return {
            "ok": True,
            "runs": [],
            "warnings": [f"No pipeline_runs directory found: {root}"],
        }

    runs = []
    for item in sorted(root.iterdir()):
        if not item.is_dir():
            continue
        summary_path = item / "summary.json"
        summary = _read_json(summary_path)
        runs.append({
            "run_id": item.name,
            "summary_path": str(summary_path),
            "status": summary.get("status") if summary else "UNKNOWN",
            "pipeline_id": summary.get("pipeline_id") if summary else None,
        })

    return {
        "ok": True,
        "runs": runs,
        "warnings": [],
    }


def inspect_run(run_id: str, work_dir: str = "./work") -> dict[str, Any]:
    warnings: list[str] = []

    summary_path = Path(work_dir) / "pipeline_runs" / run_id / "summary.json"
    summary = _read_json(summary_path)

    if not summary:
        warnings.append(f"Missing or invalid pipeline summary: {summary_path}")
        summary = None

    states_root = Path(work_dir) / "states" / run_id
    project_states = []
    subject_states: dict[str, list[dict[str, Any]]] = {}

    if not states_root.exists():
        warnings.append(f"Missing states directory: {states_root}")
    else:
        for path in sorted(states_root.rglob("*.json")):
            state = _read_json(path)
            if not state:
                warnings.append(f"Invalid state JSON: {path}")
                continue

            relative_path = str(path)
            subject = str(state.get("subject", "project"))

            payload = {
                "path": relative_path,
                "run_id": state.get("run_id"),
                "subject": subject,
                "node": state.get("node"),
                "status": state.get("status"),
                "started_at": state.get("started_at"),
                "ended_at": state.get("ended_at"),
                "outputs": state.get("outputs", []),
                "errors": state.get("errors", []),
                "warnings": state.get("warnings", []),
                "metrics": state.get("metrics", {}),
                "stdout_log": state.get("stdout_log") or state.get("log_path"),
                "stderr_log": state.get("stderr_log"),
                "result_json": state.get("result_json"),
                "returncode": state.get("returncode"),
            }

            if subject == "project":
                project_states.append(payload)
            else:
                subject_states.setdefault(subject, []).append(payload)

    subjects = []
    for subject_id, states in sorted(subject_states.items()):
        statuses = [str(item.get("status")) for item in states]
        if any(status == "FAILED" for status in statuses):
            aggregate_status = "FAILED"
        elif any(status == "NEEDS_REVIEW" for status in statuses):
            aggregate_status = "NEEDS_REVIEW"
        elif states and all(status == "SUCCESS" for status in statuses):
            aggregate_status = "SUCCESS"
        else:
            aggregate_status = "UNKNOWN"

        subjects.append({
            "subject_id": subject_id,
            "status": aggregate_status,
            "nodes": states,
        })

    return {
        "ok": True,
        "run_id": run_id,
        "summary_path": str(summary_path),
        "summary": summary,
        "project_states": project_states,
        "subjects": subjects,
        "warnings": warnings,
    }


def read_state_detail(
    run_id: str,
    state_path: str,
    work_dir: str = "./work",
) -> dict[str, Any]:
    root = Path(work_dir).resolve()
    target = Path(state_path)

    if not target.is_absolute():
        target = Path.cwd() / target

    target = target.resolve()

    try:
        target.relative_to(root.resolve().parent)
    except ValueError:
        return {
            "ok": False,
            "errors": [f"State path escapes repository: {state_path}"],
        }

    if f"states/{run_id}" not in str(target).replace("\\", "/"):
        return {
            "ok": False,
            "errors": [f"State path does not belong to run {run_id}: {state_path}"],
        }

    state = _read_json(target)
    if not state:
        return {
            "ok": False,
            "errors": [f"Missing or invalid state JSON: {target}"],
        }

    return {
        "ok": True,
        "path": str(target),
        "state": state,
    }
3. 修改 backend/app/api/routes.py

新增这些 API：

GET /api/runs
GET /api/runs/{run_id}
GET /api/runs/{run_id}/state-detail
GET /api/logs/read

要求：

/api/runs 调用 list_available_runs。
/api/runs/{run_id} 调用 inspect_run。
/api/runs/{run_id}/state-detail?path=... 调用 read_state_detail。
/api/logs/read?path=... 使用已有 path_safety.read_safe_text_file。
日志读取只允许 logs/ 下的 .log 文件。
不允许读取 NIfTI。
不允许读取 third_party。
不允许路径穿越。

新增导入：

from backend.app.runtime.run_inspector import (
    inspect_run,
    list_available_runs,
    read_state_detail,
)

新增路由参考：

@router.get("/api/runs")
def api_list_runs() -> dict[str, Any]:
    return list_available_runs("./work")


@router.get("/api/runs/{run_id}")
def api_inspect_run(run_id: str) -> dict[str, Any]:
    if "/" in run_id or "\\" in run_id or ".." in run_id:
        raise HTTPException(status_code=400, detail="Invalid run_id.")
    return inspect_run(run_id, "./work")


@router.get("/api/runs/{run_id}/state-detail")
def api_state_detail(run_id: str, path: str = Query(...)) -> dict[str, Any]:
    if "/" in run_id or "\\" in run_id or ".." in run_id:
        raise HTTPException(status_code=400, detail="Invalid run_id.")

    result = read_state_detail(run_id=run_id, state_path=path, work_dir="./work")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/api/logs/read")
def api_read_log(path: str = Query(...)) -> dict[str, Any]:
    normalized = path.replace("\\", "/")
    if not normalized.startswith("logs/") and "/logs/" not in normalized:
        raise HTTPException(status_code=403, detail="Only logs/ files can be read here.")

    if not normalized.endswith(".log"):
        raise HTTPException(status_code=403, detail="Only .log files can be read here.")

    try:
        return read_safe_text_file(path)
    except PathSafetyError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
4. 修改 frontend/src/types.ts

追加类型：

export type RunListItem = {
  run_id: string;
  summary_path: string;
  status: string;
  pipeline_id?: string | null;
};

export type NodeStateSummary = {
  path: string;
  run_id?: string;
  subject?: string;
  node?: string;
  status?: string;
  started_at?: string;
  ended_at?: string;
  outputs?: string[];
  errors?: string[];
  warnings?: string[];
  metrics?: Record<string, unknown>;
  stdout_log?: string | null;
  stderr_log?: string | null;
  result_json?: string | null;
  returncode?: number | null;
};

export type SubjectRunSummary = {
  subject_id: string;
  status: string;
  nodes: NodeStateSummary[];
};

export type RunInspection = {
  ok: boolean;
  run_id: string;
  summary_path: string;
  summary: unknown | null;
  project_states: NodeStateSummary[];
  subjects: SubjectRunSummary[];
  warnings: string[];
};
5. 修改 frontend/src/api.ts

新增 API 函数：

import type { RunInspection } from "./types";

export async function listRuns(baseUrl: string) {
  return requestJson<{ ok: boolean; runs: Array<Record<string, unknown>> }>(
    baseUrl,
    "/api/runs"
  );
}

export async function inspectRun(baseUrl: string, runId: string) {
  return requestJson<RunInspection>(
    baseUrl,
    `/api/runs/${encodeURIComponent(runId)}`
  );
}

export async function readLog(baseUrl: string, path: string) {
  return requestJson<{
    ok: boolean;
    path: string;
    relative_path: string;
    content: string;
    size_bytes: number;
  }>(baseUrl, `/api/logs/read?path=${encodeURIComponent(path)}`);
}
6. 创建 frontend/src/components/RunMonitor.tsx

创建文件：

frontend/src/components/RunMonitor.tsx

内容：

import { useState } from "react";
import { inspectRun, listRuns, readLog } from "../api";
import type { NodeStateSummary, RunInspection } from "../types";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

function NodeStateCard({
  node,
  onSelect,
  onReadLog
}: {
  node: NodeStateSummary;
  onSelect: (node: NodeStateSummary) => void;
  onReadLog: (path: string) => void;
}) {
  return (
    <div className="stateCard">
      <div className="stateCardHeader">
        <strong>{node.node || "unknown node"}</strong>
        <StatusBadge status={node.status} />
      </div>

      <div className="stateMeta">
        <span>Subject: {node.subject || "project"}</span>
        <span>Return code: {node.returncode ?? "n/a"}</span>
      </div>

      {node.errors && node.errors.length > 0 ? (
        <div className="smallError">
          {node.errors.slice(0, 2).map((item, index) => (
            <div key={index}>{item}</div>
          ))}
        </div>
      ) : null}

      <div className="row">
        <button onClick={() => onSelect(node)}>查看 State</button>
        {node.stdout_log ? (
          <button onClick={() => onReadLog(node.stdout_log as string)}>
            stdout
          </button>
        ) : null}
        {node.stderr_log ? (
          <button onClick={() => onReadLog(node.stderr_log as string)}>
            stderr
          </button>
        ) : null}
      </div>
    </div>
  );
}

export function RunMonitor({ baseUrl }: Props) {
  const [runs, setRuns] = useState<Array<Record<string, unknown>>>([]);
  const [selectedRunId, setSelectedRunId] = useState("run_subject_preprocess_001");
  const [inspection, setInspection] = useState<RunInspection | null>(null);
  const [selectedState, setSelectedState] = useState<NodeStateSummary | null>(null);
  const [logContent, setLogContent] = useState<string | null>(null);
  const [logPath, setLogPath] = useState<string>("");
  const [error, setError] = useState("");

  async function refreshRuns() {
    setError("");
    try {
      const result = await listRuns(baseUrl);
      setRuns(result.runs || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function loadRun(runId = selectedRunId) {
    setError("");
    setSelectedState(null);
    setLogContent(null);

    try {
      const result = await inspectRun(baseUrl, runId);
      setInspection(result);
      setSelectedRunId(runId);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleReadLog(path: string) {
    setError("");
    setLogContent(null);
    setLogPath(path);

    try {
      const result = await readLog(baseUrl, path);
      setLogContent(result.content);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  const summaryStatus =
    inspection?.summary &&
    typeof inspection.summary === "object" &&
    "status" in inspection.summary
      ? String((inspection.summary as { status?: unknown }).status)
      : "UNKNOWN";

  return (
    <div>
      <div className="formGrid">
        <label>
          Run ID
          <input
            value={selectedRunId}
            onChange={(event) => setSelectedRunId(event.target.value)}
          />
        </label>
      </div>

      <div className="row">
        <button onClick={refreshRuns}>刷新 Run 列表</button>
        <button onClick={() => loadRun()}>加载 Run</button>
        {inspection ? <StatusBadge status={summaryStatus} /> : null}
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      {runs.length > 0 ? (
        <div className="pipelineList">
          {runs.map((run) => {
            const runId = String(run.run_id || "");
            return (
              <button
                key={runId}
                className={runId === selectedRunId ? "listItem selected" : "listItem"}
                onClick={() => loadRun(runId)}
              >
                {runId} · {String(run.status || "UNKNOWN")}
              </button>
            );
          })}
        </div>
      ) : null}

      <h3>Pipeline Summary</h3>
      <JsonBlock value={inspection?.summary} emptyText="尚未加载 run summary" />

      <h3>Project-level States</h3>
      {inspection?.project_states?.length ? (
        <div className="stateGrid">
          {inspection.project_states.map((node) => (
            <NodeStateCard
              key={node.path}
              node={node}
              onSelect={setSelectedState}
              onReadLog={handleReadLog}
            />
          ))}
        </div>
      ) : (
        <div className="empty">暂无 project-level state</div>
      )}

      <h3>Subject-level States</h3>
      {inspection?.subjects?.length ? (
        <div className="subjectList">
          {inspection.subjects.map((subject) => (
            <div key={subject.subject_id} className="subjectPanel">
              <div className="stateCardHeader">
                <strong>{subject.subject_id}</strong>
                <StatusBadge status={subject.status} />
              </div>
              <div className="stateGrid">
                {subject.nodes.map((node) => (
                  <NodeStateCard
                    key={node.path}
                    node={node}
                    onSelect={setSelectedState}
                    onReadLog={handleReadLog}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty">暂无 subject-level state</div>
      )}

      <h3>Selected State Detail</h3>
      <JsonBlock value={selectedState} emptyText="请选择一个节点 state" />

      <h3>Log Viewer {logPath ? `· ${logPath}` : ""}</h3>
      <TextViewer text={logContent} emptyText="请选择 stdout 或 stderr 日志" />
    </div>
  );
}
7. 修改 frontend/src/App.tsx

导入 RunMonitor：

import { RunMonitor } from "./components/RunMonitor";

在 Dataset Evaluation Report 之前或之后新增 Section：

<Section
  title="4. Run Monitor"
  description="查看 pipeline summary、project-level state、subject-level state 和日志。"
>
  <RunMonitor baseUrl={baseUrl} />
</Section>

如果原来的 Dataset Evaluation 是第 4 节，可以改成第 5 节。

8. 修改 frontend/src/styles.css

追加样式：

.stateGrid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
  margin: 12px 0;
}

.stateCard {
  border: 1px solid #e4e8f2;
  background: #fbfcff;
  border-radius: 16px;
  padding: 14px;
}

.stateCardHeader {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.stateMeta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: #667085;
  font-size: 13px;
  margin-bottom: 8px;
}

.smallError {
  background: #fff1f2;
  color: #9f1239;
  border: 1px solid #fecdd3;
  border-radius: 10px;
  padding: 8px;
  font-size: 12px;
  margin: 8px 0;
  white-space: pre-wrap;
}

.subjectList {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.subjectPanel {
  border: 1px solid #e4e8f2;
  border-radius: 18px;
  padding: 14px;
  background: #ffffff;
}
9. 更新 backend/app/tools/api_smoke_test.py

增加测试：

GET /api/runs
如果存在 run_subject_preprocess_001，则 GET /api/runs/run_subject_preprocess_001

在已有 checks 里追加：

call("GET", "/api/runs")
call("GET", "/api/runs/run_subject_preprocess_001")

不要自动读日志，不要执行 pipeline。

10. 更新 README.md

追加第十一步说明：

## Step 11: Run Monitor and Log Viewer

This step adds backend APIs and frontend components for inspecting pipeline runs.

### Backend APIs

```text
GET /api/runs
GET /api/runs/{run_id}
GET /api/runs/{run_id}/state-detail?path=...
GET /api/logs/read?path=...
Frontend

The frontend now includes a Run Monitor section.

It can show:

pipeline summary
project-level node states
subject-level node states
errors and warnings
stdout / stderr logs
Run

Start backend:

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

Start frontend:

cd frontend
npm run dev

Open:

http://127.0.0.1:5173
Safety

The Run Monitor is read-only.

It cannot:

delete files
modify state
modify rawdata
read arbitrary files
read NIfTI images

---

## 11. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/run_monitor_spec.md
backend/app/runtime/run_inspector.py
backend/app/api/routes.py
backend/app/tools/api_smoke_test.py
frontend/src/types.ts
frontend/src/api.ts
frontend/src/components/RunMonitor.tsx
frontend/src/App.tsx
frontend/src/styles.css
README.md

后端启动：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl http://127.0.0.1:8000/api/runs
curl http://127.0.0.1:8000/api/runs/run_subject_preprocess_001
python -m backend.app.tools.api_smoke_test

前端启动：

cd frontend
npm run dev

打开：

http://127.0.0.1:5173

页面应该能完成：

Run Monitor 显示 run 列表。
可以加载 run_subject_preprocess_001。
可以看到 pipeline summary。
可以看到 project-level states。
可以看到 sub-001 / sub-002 的 subject-level states。
可以点击节点查看 state detail。
如果 state 中有 stdout_log / stderr_log，可以点击查看日志内容。
如果日志不存在，显示清晰错误。
不能读取 logs/ 之外的任意文件。
不能读取 .nii / .nii.gz。
12. 重要限制

本步骤只做 Run Monitor + State / Log Viewer。

不要实现：

WebSocket
实时日志流
任务取消
任务重试按钮
删除文件
修改状态
数据库 run history
复杂图表
医学影像 viewer
GPU dashboard
DPABI pipeline
多用户权限系统

完成后请总结：

新增了哪些文件
修改了哪些文件
新增了哪些 API
前端 Run Monitor 能查看什么
日志读取的安全限制是什么
如果 run 不显示应该检查哪些文件

'''
这一步（Step 11）主要实现的是 "Run Monitor + State / Log Viewer 闭环" 。

## 核心目标
让用户可以在 Web UI 中清晰地查看 pipeline 的运行状态，包括：

1. Pipeline Run Summary - 运行总体摘要
2. Project-level Node States - 项目级节点状态
3. Subject-level Node States - 受试者级节点状态（按 subject 分组）
4. 日志查看 - stdout / stderr 日志内容
5. 错误和警告 - 失败节点的详细信息
6. 节点指标 - 运行指标和输出
## 关键实现
### 后端
- Run Inspector - 读取和解析 run summary、state 文件
- 4 个新 API 端点 ：
  - GET /api/runs - 列出所有 runs
  - GET /api/runs/{run_id} - 检查特定 run
  - GET /api/runs/{run_id}/state-detail - 读取 state 详情
  - GET /api/logs/read - 安全读取日志文件
### 前端
- RunMonitor 组件 - 完整的运行状态查看界面
- 状态聚合逻辑 - 自动计算 subject 的整体状态（FAILED > NEEDS_REVIEW > SUCCESS > UNKNOWN）
- 日志查看器 - 可以查看 stdout/stderr 日志
## 限制（明确不做）
- ❌ WebSocket 实时流
- ❌ 实时日志 tail
- ❌ 数据库
- ❌ 异步队列
- ❌ 任务取消/重试
- ❌ 修改 state 文件
这一步只做 基于已有 JSON / log 文件的读取和展示 ，保持简单和安全。
'''