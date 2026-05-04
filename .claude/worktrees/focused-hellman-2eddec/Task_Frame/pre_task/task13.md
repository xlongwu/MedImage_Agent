你是我的工程搭建助手。前十二步已经完成：

Step 1：完成项目工程骨架，并打通 MATLAB / SPM / DPABI 环境检查闭环。
Step 2：完成单节点执行闭环，可以运行一个 SPM smoke test 节点。
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

现在开始第十三步。

第十三步目标：实现“Checkpoint / Cache / Approved Retry 闭环”。

当前系统已经可以生成 retry_plan.json，但 retry plan 只是 advisory。  
本步骤要实现一个最小的、可审批的 retry runner：

- 读取 retry_plan.json
- 校验 retry plan
- 默认 dry-run，不执行任何重跑
- 只有显式 approved=true 才允许执行
- 只支持 allowlisted retry action
- 支持 RERUN_ENVIRONMENT_CHECK
- 支持 SAFE_RETRY subject-level node：
  - spm_smooth_subject
  - subject_qc
- 支持重新运行 dataset_evaluation
- 不支持删除旧输出
- 不覆盖 rawdata
- 不修改 SPM / DPABI 源码
- 重跑结果写入新的 retry run 目录
- 生成 retry_execution_summary.json
- 后端 API 暴露 retry dry-run 和 approved execute
- 前端 Error Diagnosis 区域增加 Retry Plan / Dry Run / Approved Retry 控制

不要实现：
- 自动 retry
- 无审批 retry
- 删除文件
- 覆盖 rawdata
- 修改 state 文件历史
- 复杂缓存系统
- 并行 retry
- GPU
- DPABI pipeline
- 真实 LLM
- WebSocket
- 数据库
- 任意命令执行

本步骤只做安全、可审批、可追踪的最小 retry execution。

---

## 1. 创建 specs/retry_runtime_spec.md

创建文件：

```text
specs/retry_runtime_spec.md

内容：

# Retry Runtime Specification

This document defines the MVP approved retry runtime for MedImage Agent.

## Goals

The retry runtime executes selected safe retry steps from retry_plan.json.

It must be:

- explicit
- approved
- auditable
- non-destructive
- limited to allowlisted actions
- safe for medical imaging workflows

## Inputs

```text
work/diagnosis/{run_id}/retry_plan.json
work/dataset_index/dataset_index.json
examples/project_config_dataset.yaml
Outputs
work/retry_runs/{retry_run_id}/retry_execution_summary.json
work/retry_runs/{retry_run_id}/dry_run_summary.json
work/states/{retry_run_id}/...
Supported Retry Actions
RERUN_ENVIRONMENT_CHECK

Runs the existing environment_check node.

SAFE_RETRY

Only allowed for allowlisted nodes:

spm_smooth_subject
subject_qc
dataset_evaluation
FIX_CONFIG_THEN_RETRY

Dry-run only in MVP. Requires user to fix config manually.

FIX_DEPENDENCY_THEN_RETRY

Dry-run only in MVP. Requires user to install dependencies manually.

MANUAL_REVIEW

Dry-run only. No automatic execution.

NO_RETRY

No execution.

Approval Rules
Dry run does not require approval.
Execution requires approved=true.
Execution must never run automatically after diagnosis.
Execution must never delete old outputs.
Execution must write a new retry run ID.
State Rules

Original run state must remain unchanged.

Retry execution writes new state files:

work/states/{retry_run_id}/...
Safety Rules
Do not delete files.
Do not modify rawdata.
Do not modify third_party.
Do not edit original state JSON.
Do not execute unsupported actions.
Do not execute retry without approval.
Do not execute MANUAL_REVIEW steps.

---

## 2. 创建 backend/app/runtime/retry_runtime.py

创建文件：

```text
backend/app/runtime/retry_runtime.py

目标：实现 retry dry-run 和 approved retry execution。

提供函数：

load_retry_plan(run_id: str, work_dir: str = "./work") -> dict
dry_run_retry_plan(
    run_id: str,
    retry_run_id: str | None = None,
    work_dir: str = "./work",
) -> dict
execute_retry_plan(
    run_id: str,
    project_config_path: str,
    retry_run_id: str | None = None,
    approved: bool = False,
    work_dir: str = "./work",
) -> dict

要求：

load_retry_plan 读取：
work/diagnosis/{run_id}/retry_plan.json
dry_run_retry_plan：
不执行任何节点
生成 dry_run_summary.json
标记哪些 steps 可执行、哪些不可执行
输出到：
work/retry_runs/{retry_run_id}/dry_run_summary.json
execute_retry_plan：
如果 approved=false，直接失败
只执行 allowlisted action
不执行 MANUAL_REVIEW / FIX_CONFIG_THEN_RETRY / FIX_DEPENDENCY_THEN_RETRY / NO_RETRY
对不支持的 action 记录 skipped
写 retry_execution_summary.json
使用新的 retry_run_id，例如：
retry_run_subject_preprocess_001_001
支持执行：
RERUN_ENVIRONMENT_CHECK
SAFE_RETRY spm_smooth_subject
SAFE_RETRY subject_qc
SAFE_RETRY dataset_evaluation
对 subject-level node：
从 dataset_index.json 找到 subject_record
创建 NodeExecutionContext
调用 node_registry 里的 runner
写入新的 state：
work/states/{retry_run_id}/{subject_id}/{node_id}.json
对 project-level node：
写入：
work/states/{retry_run_id}/{node_id}.json
不删除旧输出。
不修改原 run state。
不修改 retry_plan.json。
所有异常转为结构化 errors。
3. retry_runtime.py 参考实现方向

请基于现有代码实现，允许调整，但保留核心字段。

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.app.runtime.agent_plan import _load_project_config
from backend.app.runtime.node_registry import (
    NodeExecutionContext,
    get_node_runner,
)
from backend.app.runtime.pipeline_executor import (
    get_complete_subjects,
    load_dataset_index,
)
from backend.app.runtime.state_store import (
    determine_status_from_result,
    now_iso,
    write_node_state,
)


EXECUTABLE_ACTIONS = {"RERUN_ENVIRONMENT_CHECK", "SAFE_RETRY"}
ALLOWLISTED_RETRY_NODES = {
    "environment_check",
    "spm_smooth_subject",
    "subject_qc",
    "dataset_evaluation",
}


def _default_retry_run_id(run_id: str) -> str:
    return f"retry_{run_id}_001"


def load_retry_plan(run_id: str, work_dir: str = "./work") -> dict[str, Any]:
    path = Path(work_dir) / "diagnosis" / run_id / "retry_plan.json"
    if not path.exists():
        return {
            "ok": False,
            "errors": [f"Retry plan not found: {path}"],
            "path": str(path),
        }

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "ok": False,
            "errors": [f"Failed to parse retry plan: {exc}"],
            "path": str(path),
        }

    data["ok"] = True
    data["path"] = str(path)
    return data


def _classify_retry_step(step: dict[str, Any]) -> dict[str, Any]:
    action = str(step.get("action", ""))
    node = step.get("node")
    subject_id = step.get("subject_id")

    executable = False
    reason = ""

    if action not in EXECUTABLE_ACTIONS:
        executable = False
        reason = f"Action is advisory-only in MVP: {action}"
    elif action == "RERUN_ENVIRONMENT_CHECK":
        executable = True
        node = "environment_check"
        reason = "Environment check can be safely rerun."
    elif action == "SAFE_RETRY":
        if node not in ALLOWLISTED_RETRY_NODES:
            executable = False
            reason = f"Node is not allowlisted for retry: {node}"
        else:
            executable = True
            reason = "Step is allowlisted for safe retry."
    else:
        executable = False
        reason = f"Unsupported retry action: {action}"

    return {
        "step_id": step.get("step_id"),
        "action": action,
        "node": node,
        "subject_id": subject_id,
        "executable": executable,
        "reason": reason,
        "original_step": step,
    }


def dry_run_retry_plan(
    run_id: str,
    retry_run_id: str | None = None,
    work_dir: str = "./work",
) -> dict[str, Any]:
    retry_run_id = retry_run_id or _default_retry_run_id(run_id)
    plan = load_retry_plan(run_id, work_dir)

    out_dir = Path(work_dir) / "retry_runs" / retry_run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    if not plan.get("ok"):
        summary = {
            "ok": False,
            "mode": "DRY_RUN",
            "run_id": run_id,
            "retry_run_id": retry_run_id,
            "steps": [],
            "errors": plan.get("errors", []),
        }
    else:
        steps = [_classify_retry_step(step) for step in plan.get("steps", [])]
        summary = {
            "ok": True,
            "mode": "DRY_RUN",
            "run_id": run_id,
            "retry_run_id": retry_run_id,
            "steps_total": len(steps),
            "steps_executable": sum(1 for step in steps if step["executable"]),
            "steps_skipped": sum(1 for step in steps if not step["executable"]),
            "steps": steps,
            "errors": [],
            "warnings": [],
        }

    path = out_dir / "dry_run_summary.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    summary["dry_run_summary_path"] = str(path)
    return summary


def _load_subject_record(subject_id: str, work_dir: str) -> dict[str, Any] | None:
    dataset_index_path = Path(work_dir) / "dataset_index" / "dataset_index.json"
    dataset_index = load_dataset_index(dataset_index_path)
    for subject in get_complete_subjects(dataset_index):
        if subject.get("subject_id") == subject_id:
            return subject
    return None


def _build_context(
    retry_run_id: str,
    project_config: dict[str, Any],
    subject_id: str | None = None,
    subject_record: dict[str, Any] | None = None,
    previous_subject_results: dict[str, dict[str, Any]] | None = None,
) -> NodeExecutionContext:
    runtime = project_config.get("runtime", {})
    third_party = project_config.get("third_party", {})

    return NodeExecutionContext(
        run_id=retry_run_id,
        project_config=project_config,
        work_dir=runtime.get("work_dir", "./work"),
        log_dir=runtime.get("log_dir", "./logs"),
        matlab_command=runtime.get("matlab_command", "matlab"),
        spm_dir=third_party.get("spm_dir", "./third_party/spm12"),
        dpabi_dir=third_party.get("dpabi_dir", "./third_party/DPABI_V8.2_240510"),
        derivatives_dir=runtime.get("derivatives_dir", "./derivatives"),
        subject_id=subject_id,
        subject_record=subject_record,
        previous_subject_results=previous_subject_results or {},
    )


def _minimal_node(node_id: str, params: dict[str, Any] | None = None):
    from backend.app.schemas.pipeline_schema import PipelineNode

    return PipelineNode(
        id=node_id,
        name=node_id,
        agent="retry-runtime",
        backend="python",
        depends_on=[],
        inputs=[],
        outputs=[],
        params=params or {},
        parallel_level="subject" if node_id in {"spm_smooth_subject", "subject_qc"} else "project",
        gpu_supported=False,
        cache=False,
    )


def _run_single_retry_step(
    retry_run_id: str,
    project_config: dict[str, Any],
    classified_step: dict[str, Any],
) -> dict[str, Any]:
    action = classified_step["action"]
    node_id = classified_step["node"]
    subject_id = classified_step.get("subject_id")

    if not classified_step["executable"]:
        return {
            "ok": True,
            "status": "SKIPPED",
            "step_id": classified_step.get("step_id"),
            "node": node_id,
            "subject_id": subject_id,
            "reason": classified_step.get("reason"),
            "outputs": [],
            "errors": [],
        }

    if action == "RERUN_ENVIRONMENT_CHECK":
        node_id = "environment_check"
        context = _build_context(retry_run_id, project_config)
        node = _minimal_node("environment_check")
    else:
        if node_id in {"spm_smooth_subject", "subject_qc"}:
            if not subject_id or subject_id == "project":
                return {
                    "ok": False,
                    "status": "FAILED",
                    "step_id": classified_step.get("step_id"),
                    "node": node_id,
                    "subject_id": subject_id,
                    "errors": ["Subject-level retry requires subject_id."],
                }

            subject_record = _load_subject_record(subject_id, project_config.get("runtime", {}).get("work_dir", "./work"))
            if not subject_record:
                return {
                    "ok": False,
                    "status": "FAILED",
                    "step_id": classified_step.get("step_id"),
                    "node": node_id,
                    "subject_id": subject_id,
                    "errors": [f"Subject record not found or not COMPLETE: {subject_id}"],
                }

            context = _build_context(
                retry_run_id=retry_run_id,
                project_config=project_config,
                subject_id=subject_id,
                subject_record=subject_record,
            )
            node = _minimal_node(node_id, params={"fwhm": [4, 4, 4]})
        elif node_id == "dataset_evaluation":
            context = _build_context(retry_run_id, project_config)
            node = _minimal_node(
                "dataset_evaluation",
                params={"dataset_index": "./work/dataset_index/dataset_index.json"},
            )
        else:
            return {
                "ok": False,
                "status": "FAILED",
                "step_id": classified_step.get("step_id"),
                "node": node_id,
                "subject_id": subject_id,
                "errors": [f"Unsupported allowlisted retry node: {node_id}"],
            }

    started_at = now_iso()

    try:
        runner = get_node_runner(node_id)
        result = runner(context, node)
    except Exception as exc:
        result = {
            "ok": False,
            "node_id": node_id,
            "subject_id": subject_id or "project",
            "outputs": [],
            "errors": [f"Retry runner failed: {exc}"],
        }

    ended_at = now_iso()
    status = determine_status_from_result(result)
    subject_for_state = subject_id if subject_id and subject_id != "project" else "project"

    state_path = write_node_state(
        run_id=retry_run_id,
        node_id=node_id,
        subject=subject_for_state,
        status=status,
        started_at=started_at,
        ended_at=ended_at,
        result=result,
        work_dir=project_config.get("runtime", {}).get("work_dir", "./work"),
    )

    return {
        "ok": result.get("ok", False),
        "status": status,
        "step_id": classified_step.get("step_id"),
        "node": node_id,
        "subject_id": subject_for_state,
        "state_path": str(state_path),
        "result": result,
        "errors": result.get("errors", []),
    }


def execute_retry_plan(
    run_id: str,
    project_config_path: str,
    retry_run_id: str | None = None,
    approved: bool = False,
    work_dir: str = "./work",
) -> dict[str, Any]:
    retry_run_id = retry_run_id or _default_retry_run_id(run_id)

    if not approved:
        return {
            "ok": False,
            "mode": "EXECUTE",
            "run_id": run_id,
            "retry_run_id": retry_run_id,
            "errors": ["Retry execution requires approved=true."],
        }

    project_config = _load_project_config(project_config_path)
    dry_run = dry_run_retry_plan(run_id, retry_run_id, work_dir)

    out_dir = Path(work_dir) / "retry_runs" / retry_run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    if not dry_run.get("ok"):
        return dry_run

    results = []
    for step in dry_run.get("steps", []):
        result = _run_single_retry_step(
            retry_run_id=retry_run_id,
            project_config=project_config,
            classified_step=step,
        )
        results.append(result)

    failed = [item for item in results if item.get("status") == "FAILED"]
    executed = [item for item in results if item.get("status") != "SKIPPED"]

    summary = {
        "ok": len(failed) == 0,
        "mode": "EXECUTE",
        "run_id": run_id,
        "retry_run_id": retry_run_id,
        "approved": approved,
        "steps_total": len(results),
        "steps_executed": len(executed),
        "steps_failed": len(failed),
        "steps_skipped": sum(1 for item in results if item.get("status") == "SKIPPED"),
        "results": results,
        "errors": [err for item in failed for err in item.get("errors", [])],
        "warnings": [],
    }

    path = out_dir / "retry_execution_summary.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    summary["retry_execution_summary_path"] = str(path)
    return summary
4. 新增 backend/app/tools/retry_plan_cli.py

创建文件：

backend/app/tools/retry_plan_cli.py

功能：

默认 run_id：
run_subject_preprocess_001
默认 project_config：
examples/project_config_dataset.yaml
默认模式是 dry-run。
只有传入 --approve 才执行。
支持可选 retry_run_id。
打印 JSON。
返回码：
dry-run ok 返回 0
execute ok 返回 0
失败返回 2

参考实现：

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.retry_runtime import (
    dry_run_retry_plan,
    execute_retry_plan,
)


def main() -> int:
    args = sys.argv[1:]
    approved = "--approve" in args
    args = [arg for arg in args if arg != "--approve"]

    run_id = args[0] if len(args) > 0 else "run_subject_preprocess_001"
    project_config = Path(args[1]) if len(args) > 1 else Path("examples/project_config_dataset.yaml")
    retry_run_id = args[2] if len(args) > 2 else None

    if approved:
        result = execute_retry_plan(
            run_id=run_id,
            project_config_path=str(project_config),
            retry_run_id=retry_run_id,
            approved=True,
        )
    else:
        result = dry_run_retry_plan(
            run_id=run_id,
            retry_run_id=retry_run_id,
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
5. 修改 backend/app/api/models.py

新增 request model：

class RetryDryRunRequest(BaseModel):
    run_id: str = Field(default="run_subject_preprocess_001")
    retry_run_id: str | None = Field(default=None)


class RetryExecuteRequest(BaseModel):
    run_id: str = Field(default="run_subject_preprocess_001")
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    retry_run_id: str | None = Field(default=None)
    approved: bool = Field(default=False)
6. 修改 backend/app/api/routes.py

新增 API：

POST /api/retry/dry-run
POST /api/retry/execute
GET  /api/retry-runs/{retry_run_id}

要求：

dry-run 不需要 approved。
execute 必须 approved=true。
execute 不允许自动执行没有 approval 的 retry。
GET /api/retry-runs/{retry_run_id} 读取：
work/retry_runs/{retry_run_id}/dry_run_summary.json
work/retry_runs/{retry_run_id}/retry_execution_summary.json
所有 retry_run_id 都要校验，禁止路径穿越。

新增导入：

from backend.app.api.models import RetryDryRunRequest, RetryExecuteRequest
from backend.app.runtime.retry_runtime import dry_run_retry_plan, execute_retry_plan

新增路由：

@router.post("/api/retry/dry-run")
def api_retry_dry_run(request: RetryDryRunRequest) -> dict[str, Any]:
    result = dry_run_retry_plan(
        run_id=request.run_id,
        retry_run_id=request.retry_run_id,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/api/retry/execute")
def api_retry_execute(request: RetryExecuteRequest) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(status_code=403, detail="Retry execution requires approved=true.")

    result = execute_retry_plan(
        run_id=request.run_id,
        project_config_path=request.project_config_path,
        retry_run_id=request.retry_run_id,
        approved=request.approved,
    )

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)

    return result


@router.get("/api/retry-runs/{retry_run_id}")
def api_get_retry_run(retry_run_id: str) -> dict[str, Any]:
    if "/" in retry_run_id or "\\" in retry_run_id or ".." in retry_run_id:
        raise HTTPException(status_code=400, detail="Invalid retry_run_id.")

    base = Path("work") / "retry_runs" / retry_run_id

    return {
        "ok": True,
        "retry_run_id": retry_run_id,
        "dry_run_summary": _read_json_if_exists(base / "dry_run_summary.json"),
        "retry_execution_summary": _read_json_if_exists(base / "retry_execution_summary.json"),
    }
7. 修改 frontend/src/api.ts

新增函数：

export async function dryRunRetry(
  baseUrl: string,
  payload: {
    run_id: string;
    retry_run_id?: string | null;
  }
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/retry/dry-run", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function executeRetry(
  baseUrl: string,
  payload: {
    run_id: string;
    project_config_path: string;
    retry_run_id?: string | null;
    approved: boolean;
  }
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/retry/execute", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getRetryRun(baseUrl: string, retryRunId: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/retry-runs/${encodeURIComponent(retryRunId)}`
  );
}
8. 创建 frontend/src/components/RetryControls.tsx

创建文件：

frontend/src/components/RetryControls.tsx

内容：

import { useState } from "react";
import { dryRunRetry, executeRetry, getRetryRun } from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";

type Props = {
  baseUrl: string;
  defaultRunId?: string;
};

export function RetryControls({
  baseUrl,
  defaultRunId = "run_subject_preprocess_001"
}: Props) {
  const [runId, setRunId] = useState(defaultRunId);
  const [retryRunId, setRetryRunId] = useState("");
  const [projectConfigPath, setProjectConfigPath] = useState(
    "examples/project_config_dataset.yaml"
  );
  const [dryRunResult, setDryRunResult] = useState<unknown>(null);
  const [executeResult, setExecuteResult] = useState<unknown>(null);
  const [retryRunDetail, setRetryRunDetail] = useState<unknown>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  const effectiveRetryRunId =
    retryRunId.trim() || `retry_${runId}_001`;

  async function handleDryRun() {
    setStatus("DRY_RUN");
    setError("");
    setDryRunResult(null);

    try {
      const result = await dryRunRetry(baseUrl, {
        run_id: runId,
        retry_run_id: retryRunId.trim() || null
      });
      setDryRunResult(result);
      setStatus("DRY_RUN_READY");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleExecute() {
    const confirmed = window.confirm(
      "确认执行 approved retry？这只会执行 allowlisted retry steps，但可能调用 MATLAB。"
    );

    if (!confirmed) return;

    setStatus("EXECUTING_RETRY");
    setError("");
    setExecuteResult(null);

    try {
      const result = await executeRetry(baseUrl, {
        run_id: runId,
        project_config_path: projectConfigPath,
        retry_run_id: retryRunId.trim() || null,
        approved: true
      });
      setExecuteResult(result);
      setStatus("RETRY_EXECUTED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleLoadRetryRun() {
    setError("");
    try {
      const result = await getRetryRun(baseUrl, effectiveRetryRunId);
      setRetryRunDetail(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div>
      <div className="formGrid">
        <label>
          Original Run ID
          <input value={runId} onChange={(event) => setRunId(event.target.value)} />
        </label>

        <label>
          Retry Run ID
          <input
            value={retryRunId}
            placeholder={`retry_${runId}_001`}
            onChange={(event) => setRetryRunId(event.target.value)}
          />
        </label>

        <label>
          Project Config
          <input
            value={projectConfigPath}
            onChange={(event) => setProjectConfigPath(event.target.value)}
          />
        </label>
      </div>

      <div className="row">
        <button onClick={handleDryRun}>Retry Dry Run</button>
        <button className="dangerButton" onClick={handleExecute}>
          批准并执行 Retry
        </button>
        <button onClick={handleLoadRetryRun}>加载 Retry Run</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <h3>Dry Run Result</h3>
      <JsonBlock value={dryRunResult} emptyText="尚未 dry-run" />

      <h3>Retry Execute Result</h3>
      <JsonBlock value={executeResult} emptyText="尚未执行 retry" />

      <h3>Retry Run Detail</h3>
      <JsonBlock value={retryRunDetail} emptyText="尚未加载 retry run" />
    </div>
  );
}
9. 修改 frontend/src/App.tsx

新增导入：

import { RetryControls } from "./components/RetryControls";

在 Error Diagnosis 后面新增 Section：

<Section
  title="6. Approved Retry"
  description="读取 retry_plan.json，先 dry-run，再显式批准执行 allowlisted retry steps。"
>
  <RetryControls baseUrl={baseUrl} />
</Section>

后面的 Dataset Evaluation Report 顺延编号。

10. 修改 backend/app/tools/api_smoke_test.py

增加 dry-run API 测试：

call("POST", "/api/retry/dry-run", json={
    "run_id": "run_subject_preprocess_001",
    "retry_run_id": "retry_run_subject_preprocess_001_001"
})

不要在 smoke test 中调用 /api/retry/execute，避免误触发 MATLAB。

11. 更新 README.md

追加第十三步说明：

## Step 13: Checkpoint / Cache / Approved Retry

This step adds a minimal approved retry runtime.

It reads:

```text
work/diagnosis/{run_id}/retry_plan.json

It can dry-run retry steps and, with explicit approval, execute allowlisted retry steps.

Dry Run
python -m backend.app.tools.retry_plan_cli run_subject_preprocess_001

Expected output:

work/retry_runs/retry_run_subject_preprocess_001_001/dry_run_summary.json
Approved Execute
python -m backend.app.tools.retry_plan_cli run_subject_preprocess_001 examples/project_config_dataset.yaml retry_run_subject_preprocess_001_001 --approve

Expected output:

work/retry_runs/retry_run_subject_preprocess_001_001/retry_execution_summary.json
work/states/retry_run_subject_preprocess_001_001/...
API
curl -X POST http://127.0.0.1:8000/api/retry/dry-run \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "run_subject_preprocess_001",
    "retry_run_id": "retry_run_subject_preprocess_001_001"
  }'

Approved execution:

curl -X POST http://127.0.0.1:8000/api/retry/execute \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "run_subject_preprocess_001",
    "project_config_path": "examples/project_config_dataset.yaml",
    "retry_run_id": "retry_run_subject_preprocess_001_001",
    "approved": true
  }'
Safety
Retry is never automatic.
Retry execution requires approval.
Only allowlisted actions are executed.
Old state files are not modified.
Rawdata is not modified.
Files are not deleted.

---

## 12. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/retry_runtime_spec.md
backend/app/runtime/retry_runtime.py
backend/app/tools/retry_plan_cli.py
backend/app/api/models.py
backend/app/api/routes.py
backend/app/tools/api_smoke_test.py
frontend/src/api.ts
frontend/src/components/RetryControls.tsx
frontend/src/App.tsx
README.md

先确保已有 diagnosis：

python -m backend.app.tools.diagnose_run_cli run_subject_preprocess_001

运行 dry-run：

python -m backend.app.tools.retry_plan_cli run_subject_preprocess_001

应该生成：

work/retry_runs/retry_run_subject_preprocess_001_001/dry_run_summary.json

运行 approved retry：

python -m backend.app.tools.retry_plan_cli run_subject_preprocess_001 examples/project_config_dataset.yaml retry_run_subject_preprocess_001_001 --approve

应该生成：

work/retry_runs/retry_run_subject_preprocess_001_001/retry_execution_summary.json

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl -X POST http://127.0.0.1:8000/api/retry/dry-run \
  -H "Content-Type: application/json" \
  -d '{"run_id":"run_subject_preprocess_001"}'

未批准 retry execute 应该失败：

curl -X POST http://127.0.0.1:8000/api/retry/execute \
  -H "Content-Type: application/json" \
  -d '{"run_id":"run_subject_preprocess_001","approved":false}'

应该返回 403 或清晰错误。

前端启动：

cd frontend
npm run dev

页面应该能完成：

输入 original run_id。
点击 Retry Dry Run。
显示 dry_run_summary。
点击批准执行 Retry 前出现确认弹窗。
approved retry 后显示 retry_execution_summary。
不提供删除按钮。
不自动执行 retry。
不修改原 run 的 state 文件。
13. 重要限制

本步骤只做最小 approved retry runtime。

不要实现：

自动 retry
无审批 retry
retry 按钮绕过 approval
删除旧输出
修改原 state
修改 rawdata
修改 derivatives 历史输出
复杂缓存系统
并行 retry
GPU retry
DPABI retry
数据库
WebSocket
真实 LLM 决策

完成后请总结：

新增了哪些文件
修改了哪些文件
如何 dry-run retry
如何 approved execute retry
retry 输出在哪里
为什么 retry 必须 approval
当前支持哪些 retry action


'''
这一步（Step 13）主要实现的是 "Checkpoint / Cache / Approved Retry 闭环" 。

## 核心目标
让系统能够 安全、可审批、可追踪地执行重试 ：

1. 读取 retry_plan.json - 从诊断结果中读取重试计划
2. 校验 retry plan - 验证哪些步骤可以执行
3. 默认 dry-run - 不执行任何操作，只预览
4. 显式批准执行 - 只有 approved=true 才允许执行
5. 限制执行范围 - 只允许 allowlisted 的 retry action
## 关键实现
### 后端
- Retry Runtime - 核心重试执行引擎
  
  - dry_run_retry_plan() - 预览模式
  - execute_retry_plan() - 批准执行模式
  - 分类步骤：可执行 vs 跳过
- 支持的 Retry Actions ：
  
  Action 说明 RERUN_ENVIRONMENT_CHECK 重新运行环境检查 SAFE_RETRY + spm_smooth_subject 安全重试平滑处理 SAFE_RETRY + subject_qc 安全重试 QC SAFE_RETRY + dataset_evaluation 安全重试数据集评估 FIX_CONFIG_THEN_RETRY 仅 dry-run，需手动修复配置 FIX_DEPENDENCY_THEN_RETRY 仅 dry-run，需手动安装依赖 MANUAL_REVIEW 仅 dry-run，需人工审查 NO_RETRY 不执行
- 3 个新 API 端点 ：
  
  - POST /api/retry/dry-run - Dry run
  - POST /api/retry/execute - 执行批准的 retry
  - GET /api/retry-runs/{retry_run_id} - 获取状态
### 前端
- ErrorDiagnosis 组件增强 - 添加 Retry Plan 控制区域
  - 输入 Retry Run ID
  - "Dry Run" 按钮 - 预览可执行步骤
  - "批准并执行 Retry" 按钮 - 执行
  - 显示执行结果
## 输出文件
```
work/retry_runs/{retry_run_id}/
├── dry_run_summary.json          # Dry run 结果
└── retry_execution_summary.json  # 执行结果

work/states/{retry_run_id}/...    # 新的 state 文件
```
## 限制（明确不做）
- ❌ 自动重跑
- ❌ 无审批重跑
- ❌ 删除文件
- ❌ 覆盖 rawdata
- ❌ 修改原 run 的 state
- ❌ 复杂缓存系统
- ❌ 并行 retry
这一步只做 安全、可审批、可追踪的最小 retry execution 。
'''