你是我的工程搭建助手。前十三步已经完成：

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
Step 13：完成 Checkpoint / Cache / Approved Retry 闭环。

现在开始第十四步。

第十四步目标：实现“最小本地 subject-level 并行调度 + 资源限制闭环”。

当前 pipeline executor 对 subject-level 节点是顺序执行。  
本步骤要在不引入 Celery、Redis、Slurm、数据库的前提下，实现一个本地安全并行调度器：

- 支持 subject-level nodes 的本地并行执行
- 使用 ThreadPoolExecutor 调度 subject-level 任务
- 支持 max_workers
- 支持 matlab_max_workers
- 支持 dry-run 资源计划
- 默认仍然安全：max_workers=1
- 只有配置中启用 local_parallel 才并行
- 保持 project-level nodes 顺序执行
- 保持 subject-level dependencies
- 每个 subject 的 state 文件独立写入
- pipeline summary 增加 scheduler 信息
- API 暴露 scheduler dry-run
- 前端增加 Scheduler / Resource Plan 区域

不要实现：
- Slurm
- Celery
- Redis
- 数据库
- WebSocket
- GPU
- DPABI pipeline
- 真实 LLM
- 自动扩容
- 远程机器调度
- 任务取消
- 复杂重试队列
- 删除文件
- 修改 rawdata
- 修改 SPM / DPABI 源码

本步骤只做本地 MVP 并行调度。

---

## 1. 创建 specs/scheduler_runtime_spec.md

创建文件：

```text
specs/scheduler_runtime_spec.md

内容：

# Scheduler Runtime Specification

This document defines the MVP local scheduler for MedImage Agent.

## Goals

The scheduler improves subject-level execution by supporting safe local parallelism.

It should:

- keep project-level nodes sequential
- allow subject-level nodes to run in parallel
- limit concurrency with max_workers
- limit MATLAB concurrency with matlab_max_workers
- preserve per-subject state files
- preserve pipeline summary
- avoid modifying rawdata
- avoid deleting files

## Scope

Supported:

- local sequential execution
- local subject-level parallel execution
- ThreadPoolExecutor-based scheduling
- max_workers
- matlab_max_workers
- scheduler dry-run resource plan
- per-subject state files
- summary scheduler metadata

Unsupported:

- Slurm
- Celery
- Redis
- database queues
- WebSocket progress
- GPU scheduling
- remote workers
- job cancellation
- distributed execution

## Execution Modes

### sequential

Default mode.

Subject-level nodes run one subject at a time.

### local_parallel

Subject-level nodes run across subjects using local worker threads.

This mode is safe only when:

- rawdata is read-only
- each subject writes to isolated output paths
- MATLAB worker count is limited
- state files are subject-specific

## Pipeline Config Example

```yaml
execution:
  stop_on_failure: true
  run_id: "run_subject_preprocess_parallel_001"
  scheduler:
    mode: "local_parallel"
    max_workers: 2
    matlab_max_workers: 1
Safety Rules
Default max_workers must be 1.
matlab_max_workers must not exceed max_workers.
Subject-level task failures must not crash the whole executor.
Other subjects can continue after one subject fails.
Original rawdata must not be modified.
No files should be deleted.

---

## 2. 修改 examples/project_config_dataset.yaml

在 runtime 下新增 scheduler 默认配置：

```yaml id="project_scheduler_config"
runtime:
  matlab_command: "matlab"
  work_dir: "./work"
  log_dir: "./logs"
  report_dir: "./reports"
  derivatives_dir: "./derivatives"

scheduler:
  mode: "sequential"
  max_workers: 1
  matlab_max_workers: 1

注意：

保持向后兼容。
如果已有 runtime 字段，不要删除。
scheduler 可以放在顶层，也可以放在 runtime 下；本项目统一放在顶层 scheduler。
3. 新增 examples/pipeline_subject_preprocess_parallel.yaml

创建文件：

examples/pipeline_subject_preprocess_parallel.yaml

内容基于 examples/pipeline_subject_preprocess.yaml，但 run_id 和 scheduler 改成并行版本：

pipeline_id: subject_preprocess_parallel_pipeline
version: "0.1.0"
modality: synthetic-rsfmri
description: "Synthetic BIDS-like subject-level preprocessing pipeline using local parallel scheduling."

execution:
  stop_on_failure: true
  run_id: "run_subject_preprocess_parallel_001"
  scheduler:
    mode: "local_parallel"
    max_workers: 2
    matlab_max_workers: 1

nodes:
  - id: create_synthetic_bids
    name: Create Synthetic BIDS Dataset
    agent: data-inspector
    backend: python
    depends_on: []
    inputs: []
    outputs:
      - "./examples/synthetic_bids/rawdata/dataset_description.json"
      - "./examples/synthetic_bids/rawdata/participants.tsv"
    params:
      output_dir: "./examples/synthetic_bids/rawdata"
      subjects:
        - sub-001
        - sub-002
        - sub-003
        - sub-004
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: data_inspection
    name: Data Inspection
    agent: data-inspector
    backend: python
    depends_on:
      - create_synthetic_bids
    inputs:
      - "./examples/synthetic_bids/rawdata"
    outputs:
      - "./work/dataset_index/dataset_index.json"
      - "./work/dataset_index/data_completeness_report.json"
      - "./work/dataset_index/subject_table.csv"
    params:
      rawdata_dir: "./examples/synthetic_bids/rawdata"
      output_dir: "./work/dataset_index"
      read_nifti_metadata: true
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: spm_smooth_subject
    name: SPM Smooth Subject BOLD
    agent: spm-runner
    backend: matlab-spm
    depends_on:
      - data_inspection
    inputs:
      - "./work/dataset_index/dataset_index.json"
    outputs: []
    params:
      dataset_index: "./work/dataset_index/dataset_index.json"
      fwhm: [4, 4, 4]
    parallel_level: subject
    gpu_supported: false
    cache: false

  - id: subject_qc
    name: Subject QC
    agent: qc-agent
    backend: python
    depends_on:
      - spm_smooth_subject
    inputs: []
    outputs: []
    params:
      qc_output_dir: "./derivatives/qc"
    parallel_level: subject
    gpu_supported: false
    cache: false

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
4. 创建 backend/app/runtime/scheduler.py

创建文件：

backend/app/runtime/scheduler.py

目标：提供本地调度配置解析和 dry-run 资源计划。

提供：

get_scheduler_config(project_config: dict, pipeline_execution: dict) -> dict
validate_scheduler_config(config: dict) -> dict
create_scheduler_plan(pipeline, project_config: dict) -> dict

功能要求：

默认：
{
  "mode": "sequential",
  "max_workers": 1,
  "matlab_max_workers": 1
}
pipeline.execution.scheduler 优先级高于 project_config.scheduler。
支持 mode：
sequential
local_parallel
max_workers 最小 1，最大建议 8。
matlab_max_workers 最小 1，不能大于 max_workers。
如果 mode 不合法，返回 ok=false。
create_scheduler_plan 返回：
mode
max_workers
matlab_max_workers
subject_level_nodes
matlab_subject_nodes
warnings
estimated_parallelism

参考实现：

from __future__ import annotations

from typing import Any


DEFAULT_SCHEDULER = {
    "mode": "sequential",
    "max_workers": 1,
    "matlab_max_workers": 1,
}


def get_scheduler_config(
    project_config: dict[str, Any],
    pipeline_execution: dict[str, Any],
) -> dict[str, Any]:
    config = dict(DEFAULT_SCHEDULER)

    project_scheduler = project_config.get("scheduler", {}) or {}
    execution_scheduler = pipeline_execution.get("scheduler", {}) or {}

    config.update(project_scheduler)
    config.update(execution_scheduler)

    return validate_scheduler_config(config)


def validate_scheduler_config(config: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    mode = str(config.get("mode", "sequential"))

    if mode not in {"sequential", "local_parallel"}:
        errors.append(f"Unsupported scheduler mode: {mode}")
        mode = "sequential"

    try:
        max_workers = int(config.get("max_workers", 1))
    except Exception:
        max_workers = 1
        warnings.append("Invalid max_workers; fallback to 1.")

    try:
        matlab_max_workers = int(config.get("matlab_max_workers", 1))
    except Exception:
        matlab_max_workers = 1
        warnings.append("Invalid matlab_max_workers; fallback to 1.")

    if max_workers < 1:
        warnings.append("max_workers < 1; fallback to 1.")
        max_workers = 1

    if max_workers > 8:
        warnings.append("max_workers > 8; capped to 8 for MVP safety.")
        max_workers = 8

    if matlab_max_workers < 1:
        warnings.append("matlab_max_workers < 1; fallback to 1.")
        matlab_max_workers = 1

    if matlab_max_workers > max_workers:
        warnings.append("matlab_max_workers > max_workers; capped to max_workers.")
        matlab_max_workers = max_workers

    if mode == "sequential":
        max_workers = 1
        matlab_max_workers = 1

    return {
        "ok": len(errors) == 0,
        "mode": mode,
        "max_workers": max_workers,
        "matlab_max_workers": matlab_max_workers,
        "warnings": warnings,
        "errors": errors,
    }


def create_scheduler_plan(
    pipeline: Any,
    project_config: dict[str, Any],
) -> dict[str, Any]:
    config = get_scheduler_config(project_config, pipeline.execution)

    subject_nodes = [
        node.id for node in pipeline.nodes if node.parallel_level == "subject"
    ]

    matlab_subject_nodes = [
        node.id
        for node in pipeline.nodes
        if node.parallel_level == "subject" and "matlab" in node.backend
    ]

    warnings = list(config.get("warnings", []))

    if config["mode"] == "local_parallel" and not subject_nodes:
        warnings.append("local_parallel enabled but no subject-level nodes found.")

    if matlab_subject_nodes and config["matlab_max_workers"] > 1:
        warnings.append(
            "Running multiple MATLAB workers may consume multiple MATLAB licenses."
        )

    return {
        "ok": config["ok"],
        "mode": config["mode"],
        "max_workers": config["max_workers"],
        "matlab_max_workers": config["matlab_max_workers"],
        "subject_level_nodes": subject_nodes,
        "matlab_subject_nodes": matlab_subject_nodes,
        "estimated_parallelism": {
            "subject_workers": config["max_workers"],
            "matlab_workers": config["matlab_max_workers"],
        },
        "warnings": warnings,
        "errors": config.get("errors", []),
    }
5. 修改 backend/app/runtime/agent_plan.py

在 plan.json 中加入 scheduler plan。

要求：

导入：
from backend.app.runtime.scheduler import create_scheduler_plan
在 create_agent_plan 中生成：
scheduler_plan = create_scheduler_plan(pipeline, project_config)
plan 中新增字段：
"scheduler_plan": {
  "mode": "local_parallel",
  "max_workers": 2,
  "matlab_max_workers": 1
}
如果 scheduler_plan 有 warnings，合并到 plan warnings。
如果 scheduler_plan ok=false，plan ok=false 或 warnings 中写明错误；不要执行。
6. 修改 backend/app/runtime/pipeline_executor.py

这是本步骤核心。

目标：保留现有行为，同时支持 subject-level local_parallel。

要求：

保持 project-level nodes 顺序执行。
保持 sequential 模式行为不变。
如果 scheduler.mode == "local_parallel"，subject-level node 对 COMPLETE subjects 并行执行。
使用 ThreadPoolExecutor。
对 MATLAB backend 节点使用 matlab_max_workers，而不是 max_workers。
对 Python subject-level 节点使用 max_workers。
每个 subject 的执行结果必须独立捕获异常。
每个 subject 的 state 必须独立写入。
一个 subject 失败不应阻止其他 subject 继续。
如果某个 subject 的前置 subject-level node 失败，该 subject 的后续 subject node 应标记 FAILED 或 SKIPPED，并记录依赖失败。
pipeline summary 增加 scheduler 字段。
pipeline summary 增加 runtime statistics：
started_at
ended_at
duration_seconds
scheduler_mode
max_workers
matlab_max_workers

建议实现辅助函数：

def is_matlab_node(node) -> bool:
    return "matlab" in node.backend

def get_node_worker_count(node, scheduler_config) -> int:
    if scheduler_config["mode"] != "local_parallel":
        return 1
    if is_matlab_node(node):
        return scheduler_config["matlab_max_workers"]
    return scheduler_config["max_workers"]

并新增一个函数：

def run_subject_node_for_subject(...):
    ...

可以把原来 subject-level 单 subject 执行逻辑抽出来复用。

并行执行逻辑参考
from concurrent.futures import ThreadPoolExecutor, as_completed

worker_count = get_node_worker_count(node, scheduler_config)

if worker_count <= 1:
    # existing sequential behavior
else:
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(run_one_subject, subject): subject
            for subject in complete_subjects
        }

        for future in as_completed(futures):
            subject = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {
                    "ok": False,
                    "errors": [f"Subject execution failed: {exc}"],
                }

注意：

不要让 ThreadPoolExecutor 异常导致整个进程崩溃。
每个 subject 的 state 写入需要线程安全。由于每个 subject 写入不同路径，MVP 可以接受。
不要多个线程写同一个 summary；summary 在主线程汇总后写。
7. 修改 backend/app/runtime/state_store.py

确保 write_pipeline_summary 能保存：

{
  "scheduler": {
    "mode": "local_parallel",
    "max_workers": 2,
    "matlab_max_workers": 1
  },
  "duration_seconds": 12.34
}

保持向后兼容。

8. 新增 backend/app/tools/scheduler_plan_cli.py

创建文件：

backend/app/tools/scheduler_plan_cli.py

功能：

默认 project config：
examples/project_config_dataset.yaml
默认 pipeline：
examples/pipeline_subject_preprocess_parallel.yaml
读取 pipeline 和 project config。
调用 create_scheduler_plan。
打印 JSON。
返回码：
ok=true 返回 0
ok=false 返回 1

参考实现：

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.agent_plan import _load_project_config
from backend.app.runtime.scheduler import create_scheduler_plan
from backend.app.schemas.pipeline_schema import load_pipeline_yaml


def main() -> int:
    project_config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/project_config_dataset.yaml")
    pipeline_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("examples/pipeline_subject_preprocess_parallel.yaml")

    project_config = _load_project_config(project_config_path)
    pipeline = load_pipeline_yaml(pipeline_path)

    result = create_scheduler_plan(pipeline, project_config)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
9. 新增 backend/app/tools/run_parallel_pipeline_cli.py

创建文件：

backend/app/tools/run_parallel_pipeline_cli.py

功能：

默认 project config：
examples/project_config_dataset.yaml
默认 pipeline：
examples/pipeline_subject_preprocess_parallel.yaml
调用 run_pipeline。
打印 summary。
返回码：
SUCCESS 返回 0
PARTIAL / FAILED 返回 2
INVALID 返回 1

参考：

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.pipeline_executor import run_pipeline


def main() -> int:
    project_config = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/project_config_dataset.yaml")
    pipeline = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("examples/pipeline_subject_preprocess_parallel.yaml")

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
10. 修改 backend/app/api/models.py

新增：

class SchedulerPlanRequest(BaseModel):
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    pipeline_path: str = Field(default="examples/pipeline_subject_preprocess_parallel.yaml")
11. 修改 backend/app/api/routes.py

新增 API：

POST /api/scheduler/plan

要求：

读取 project config。
读取 pipeline。
调用 create_scheduler_plan。
返回 scheduler plan。
不执行 pipeline。

新增导入：

from backend.app.api.models import SchedulerPlanRequest
from backend.app.runtime.agent_plan import _load_project_config
from backend.app.runtime.scheduler import create_scheduler_plan

新增路由：

@router.post("/api/scheduler/plan")
def api_scheduler_plan(request: SchedulerPlanRequest) -> dict[str, Any]:
    try:
        project_config = _load_project_config(request.project_config_path)
        pipeline = load_pipeline_yaml(request.pipeline_path)
        result = create_scheduler_plan(pipeline, project_config)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
12. 修改 frontend/src/api.ts

新增：

export async function createSchedulerPlan(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
  }
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/scheduler/plan", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
13. 创建 frontend/src/components/SchedulerPanel.tsx

创建文件：

frontend/src/components/SchedulerPanel.tsx

内容：

import { useState } from "react";
import { createSchedulerPlan } from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";

type Props = {
  baseUrl: string;
};

export function SchedulerPanel({ baseUrl }: Props) {
  const [projectConfigPath, setProjectConfigPath] = useState(
    "examples/project_config_dataset.yaml"
  );
  const [pipelinePath, setPipelinePath] = useState(
    "examples/pipeline_subject_preprocess_parallel.yaml"
  );
  const [plan, setPlan] = useState<unknown>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleCreatePlan() {
    setStatus("PLANNING");
    setError("");
    setPlan(null);

    try {
      const result = await createSchedulerPlan(baseUrl, {
        project_config_path: projectConfigPath,
        pipeline_path: pipelinePath
      });
      setPlan(result);
      setStatus("SUCCESS");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  return (
    <div>
      <div className="formGrid">
        <label>
          Project Config
          <input
            value={projectConfigPath}
            onChange={(event) => setProjectConfigPath(event.target.value)}
          />
        </label>

        <label>
          Pipeline
          <input
            value={pipelinePath}
            onChange={(event) => setPipelinePath(event.target.value)}
          />
        </label>
      </div>

      <div className="row">
        <button onClick={handleCreatePlan}>生成 Scheduler Plan</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <JsonBlock value={plan} emptyText="尚未生成 scheduler plan" />
    </div>
  );
}
14. 修改 frontend/src/App.tsx

新增导入：

import { SchedulerPanel } from "./components/SchedulerPanel";

在 Pipeline Explorer 之后或 Agent Plan 之前新增 Section：

<Section
  title="3. Scheduler / Resource Plan"
  description="查看本地 subject-level 并行调度计划和 MATLAB worker 限制。"
>
  <SchedulerPanel baseUrl={baseUrl} />
</Section>

后续章节编号顺延。

15. 修改 backend/app/tools/api_smoke_test.py

新增测试：

call("POST", "/api/scheduler/plan", json={
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_subject_preprocess_parallel.yaml"
})

不要自动执行 parallel pipeline。

16. 更新 README.md

追加第十四步说明：

## Step 14: Local Subject-Level Parallel Scheduler

This step adds MVP local scheduling for subject-level nodes.

It supports:

- sequential mode
- local_parallel mode
- max_workers
- matlab_max_workers
- scheduler dry-run plan
- subject-level parallel execution with ThreadPoolExecutor

### Scheduler Plan

```bash
python -m backend.app.tools.scheduler_plan_cli

Expected output:

{
  "mode": "local_parallel",
  "max_workers": 2,
  "matlab_max_workers": 1
}
Run Parallel Pipeline
python -m backend.app.tools.run_parallel_pipeline_cli

Expected summary:

work/pipeline_runs/run_subject_preprocess_parallel_001/summary.json
API
curl -X POST http://127.0.0.1:8000/api/scheduler/plan \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_subject_preprocess_parallel.yaml"
  }'
Safety
Default scheduler mode is sequential.
local_parallel must be explicitly configured in the pipeline.
MATLAB concurrency is limited by matlab_max_workers.
No rawdata is modified.
No files are deleted.

---

## 17. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/scheduler_runtime_spec.md
examples/project_config_dataset.yaml
examples/pipeline_subject_preprocess_parallel.yaml
backend/app/runtime/scheduler.py
backend/app/runtime/agent_plan.py
backend/app/runtime/pipeline_executor.py
backend/app/runtime/state_store.py
backend/app/tools/scheduler_plan_cli.py
backend/app/tools/run_parallel_pipeline_cli.py
backend/app/api/models.py
backend/app/api/routes.py
backend/app/tools/api_smoke_test.py
frontend/src/api.ts
frontend/src/components/SchedulerPanel.tsx
frontend/src/App.tsx
README.md

运行 scheduler plan：

python -m backend.app.tools.scheduler_plan_cli

应该输出：

{
  "ok": true,
  "mode": "local_parallel",
  "max_workers": 2,
  "matlab_max_workers": 1
}

运行 parallel pipeline：

python -m backend.app.tools.run_parallel_pipeline_cli

成功后应该生成：

work/pipeline_runs/run_subject_preprocess_parallel_001/summary.json
work/states/run_subject_preprocess_parallel_001/sub-001/spm_smooth_subject.json
work/states/run_subject_preprocess_parallel_001/sub-002/spm_smooth_subject.json
work/states/run_subject_preprocess_parallel_001/sub-003/spm_smooth_subject.json
work/states/run_subject_preprocess_parallel_001/sub-004/spm_smooth_subject.json

summary 中应该包含：

{
  "scheduler": {
    "mode": "local_parallel",
    "max_workers": 2,
    "matlab_max_workers": 1
  }
}

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl -X POST http://127.0.0.1:8000/api/scheduler/plan \
  -H "Content-Type: application/json" \
  -d '{"project_config_path":"examples/project_config_dataset.yaml","pipeline_path":"examples/pipeline_subject_preprocess_parallel.yaml"}'

启动前端：

cd frontend
npm run dev

页面应该能完成：

显示 Scheduler / Resource Plan 区域。
输入 parallel pipeline path。
点击生成 scheduler plan。
显示 mode、max_workers、matlab_max_workers。
不自动执行并行 pipeline。
不提供删除按钮。
不修改 rawdata。
18. 重要限制

本步骤只做 MVP 本地 subject-level 并行调度。

不要实现：

Slurm
Celery / Redis
数据库队列
WebSocket 实时进度
任务取消
GPU 调度
DPABI pipeline
远程 worker
自动扩缩容
复杂缓存
自动 retry
删除文件
修改 rawdata

完成后请总结：

新增了哪些文件
修改了哪些文件
如何生成 scheduler plan
如何运行 parallel pipeline
max_workers 和 matlab_max_workers 如何生效
pipeline summary 中如何记录 scheduler 信息
当前并行调度的限制是什么

'''
这一步（Step 14）主要实现的是 "最小本地 subject-level 并行调度 + 资源限制闭环" 。

## 核心目标
让 pipeline executor 能够 安全地并行执行 subject-level 节点 ，同时保持 project-level 节点顺序执行：

1. 支持本地并行 - 使用 ThreadPoolExecutor 调度 subject-level 任务
2. 资源限制 - 通过 max_workers 和 matlab_max_workers 控制并发
3. 默认安全 - max_workers=1（顺序执行），只有显式配置才启用并行
4. 保持依赖 - subject-level 节点间的依赖关系仍然有效
## 关键实现
### 后端
- Scheduler 模块 ( backend/app/runtime/scheduler.py )
  
  - 解析和验证 scheduler 配置
  - 支持 sequential 和 local_parallel 两种模式
  - max_workers 默认 1，上限 8
  - matlab_max_workers 不能超过 max_workers
- Pipeline Executor 增强 ( backend/app/runtime/pipeline_executor.py )
  
  - Project-level 节点：顺序执行（不变）
  - Subject-level 节点：根据配置选择顺序或并行
  - MATLAB 节点使用 matlab_max_workers 限制
  - Python 节点使用 max_workers 限制
  - 使用 ThreadPoolExecutor 实现并行
  - 跟踪失败的 subjects，后续节点跳过
- State Store 增强 ( backend/app/runtime/state_store.py )
  
  - Pipeline summary 增加 scheduler 信息
  - 记录执行时长 duration_seconds
### 配置
```
# 默认配置（顺序执行）
scheduler:
  mode: "sequential"
  max_workers: 1
  matlab_max_workers: 1

# 并行配置（覆盖）
execution:
  scheduler:
    mode: "local_parallel"
    max_workers: 2
    matlab_max_workers: 1
```
### 前端
- SchedulerPanel 组件 ( frontend/src/components/SchedulerPanel.tsx )
  - 选择 project config 和 pipeline
  - 生成 scheduler plan
  - 显示调度配置和并行度估计
## 限制（明确不做）
- ❌ Slurm / Celery / Redis / 数据库队列
- ❌ WebSocket 进度推送
- ❌ GPU 调度
- ❌ 远程 workers
- ❌ 任务取消
- ❌ 分布式执行
- ❌ 自动扩容
- ❌ 复杂重试队列
这一步只做 本地 MVP 并行调度 ，使用 Python 标准库的 ThreadPoolExecutor。

'''