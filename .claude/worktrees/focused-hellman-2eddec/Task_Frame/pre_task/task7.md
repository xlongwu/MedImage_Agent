你是我的工程搭建助手。前六步已经完成：

Step 1：完成项目工程骨架，并打通 MATLAB / SPM / DPABI 环境检查闭环。
Step 2：完成单节点执行闭环，可以运行一个 SPM smoke test 节点。
Step 3：完成最小 Pipeline DAG 执行闭环。
Step 4：完成 synthetic BIDS-like 数据集扫描与索引闭环。
Step 5：完成 synthetic subject-level SPM smoothing + QC 闭环。
Step 6：完成数据集级评估与 Markdown/HTML 报告闭环。

现在开始第七步。

第七步目标：实现“最小 Agent Runtime + Plan Mode + Tool/Hook 权限闭环”。

这一步开始把前面已经能跑的 pipeline 包装成一个最小 Agent 系统，但不要接真实大模型 API。  
现在只实现确定性的 Agent Runtime 骨架，为后续接入 LLM、Trae、Hermes-like memory、Claude Code-like subagent 做准备。

本步骤要实现：

- Agent spec 文件
- Tool Registry
- Tool Permission Registry
- Hook Manager
- Plan Mode
- Execute Mode
- Agent Runtime
- 最小 Orchestrator Agent
- 通过 Agent 生成 plan.json
- 用户显式传入 approve 后执行 pipeline
- 保存 agent run summary
- 不接真实 LLM
- 不做 UI
- 不做多 Agent 智能协作
- 不做并行调度
- 不做 GPU
- 不修改 SPM / DPABI 源码

本步骤只做 Agent Runtime 最小闭环。

---

## 1. 创建 specs/agent_runtime_spec.md

创建文件：

```text
specs/agent_runtime_spec.md

内容：

# Agent Runtime Specification

This document defines the MVP Agent Runtime for MedImage Agent.

## Design Inspiration

The MVP runtime borrows two architecture ideas:

1. Claude Code-like execution control:
   - Tool-use loop
   - Plan Mode before Execute Mode
   - Tool permission metadata
   - Hooks before and after tool execution

2. Hermes-like long-running agent foundation:
   - Agent specs
   - Memory-ready structure
   - Background review-ready structure
   - Skill-ready structure

## Scope

The MVP supports:

- deterministic orchestrator agent
- plan generation
- explicit approval before execution
- tool registry
- tool permission registry
- hook manager
- pipeline execution as a tool
- agent run summary

The MVP does not support:

- real LLM API
- autonomous tool selection
- natural language planning
- multi-agent communication
- UI
- database
- background review
- memory mutation
- GPU execution
- parallel execution

## Modes

### Plan Mode

Plan Mode is read-only.

Allowed actions:

- read project config
- read pipeline YAML
- validate pipeline
- inspect expected outputs
- estimate affected paths
- generate plan.json

Forbidden actions:

- run MATLAB
- write derivatives
- run pipeline
- delete files
- overwrite outputs

### Execute Mode

Execute Mode can run the approved plan.

Requirements:

- an existing plan.json
- approval flag set to true
- tool permissions checked
- pre-run hooks passed
- post-run hooks executed

## Agent Run Outputs

```text
work/agent_runs/{agent_run_id}/plan.json
work/agent_runs/{agent_run_id}/agent_summary.json
Safety Rules
Never execute a pipeline without explicit approval.
Never modify rawdata.
Never delete files.
Never overwrite derivatives unless explicitly configured.
Always write logs and summaries.
Always preserve the original pipeline summary.

---

## 2. 创建 agents/orchestrator.md

创建目录和文件：

```text
agents/orchestrator.md

内容：

---
name: orchestrator
description: plan and execute MedImage Agent pipelines by coordinating project configuration, pipeline YAML, tool permissions, hooks, and runtime summaries. use when the user wants to run, inspect, plan, or summarize a medical imaging pipeline.
tools:
  - pipeline.plan
  - pipeline.execute
  - filesystem.read
  - report.read
model: deterministic
---

# Orchestrator Agent

You are the top-level orchestrator for MedImage Agent.

Responsibilities:

- Generate execution plans.
- Enforce Plan Mode before Execute Mode.
- Require explicit approval before execution.
- Use registered tools only.
- Respect tool permission metadata.
- Preserve rawdata.
- Summarize pipeline outputs.

Rules:

- Do not run pipelines during Plan Mode.
- Do not modify SPM or DPABI source code.
- Do not delete files.
- Do not overwrite derivatives unless explicitly approved.
- Do not make clinical conclusions.
- Treat dataset evaluation as engineering QC, not diagnosis.

Current MVP behavior:

- This agent is deterministic.
- It does not call an LLM.
- It creates a structured plan from config and pipeline YAML.
- It executes the approved plan by calling the pipeline executor.
3. 创建 backend/app/runtime/tool_registry.py

创建文件：

backend/app/runtime/tool_registry.py

目标：实现工具注册表和权限声明。

要求：

定义 ToolSpec。
定义 ToolExecutionError。
注册两个 MVP 工具：
pipeline.plan
pipeline.execute
每个工具必须包含权限元信息：
read_only
writes_files
destructive
requires_confirmation
parallel_safe
allowed_read_paths
allowed_write_paths
提供：
get_tool_spec(name)
list_tool_specs()
assert_tool_allowed(name, approved=False)

参考实现：

from __future__ import annotations

from dataclasses import dataclass, field


class ToolExecutionError(Exception):
    pass


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    read_only: bool
    writes_files: bool
    destructive: bool
    requires_confirmation: bool
    parallel_safe: bool
    allowed_read_paths: list[str] = field(default_factory=list)
    allowed_write_paths: list[str] = field(default_factory=list)


TOOL_REGISTRY: dict[str, ToolSpec] = {
    "pipeline.plan": ToolSpec(
        name="pipeline.plan",
        description="Read project config and pipeline YAML and generate an execution plan.",
        read_only=False,
        writes_files=True,
        destructive=False,
        requires_confirmation=False,
        parallel_safe=True,
        allowed_read_paths=["examples/", "specs/", "work/"],
        allowed_write_paths=["work/agent_runs/"],
    ),
    "pipeline.execute": ToolSpec(
        name="pipeline.execute",
        description="Execute an approved pipeline plan.",
        read_only=False,
        writes_files=True,
        destructive=False,
        requires_confirmation=True,
        parallel_safe=False,
        allowed_read_paths=["examples/", "work/", "matlab/", "third_party/"],
        allowed_write_paths=["work/", "logs/", "reports/", "derivatives/"],
    ),
}


def get_tool_spec(name: str) -> ToolSpec:
    try:
        return TOOL_REGISTRY[name]
    except KeyError as exc:
        raise ToolExecutionError(f"Unknown tool: {name}") from exc


def list_tool_specs() -> list[ToolSpec]:
    return list(TOOL_REGISTRY.values())


def assert_tool_allowed(name: str, approved: bool = False) -> ToolSpec:
    spec = get_tool_spec(name)
    if spec.requires_confirmation and not approved:
        raise ToolExecutionError(
            f"Tool requires explicit approval before execution: {name}"
        )
    return spec
4. 创建 backend/app/runtime/hook_manager.py

创建文件：

backend/app/runtime/hook_manager.py

目标：实现最小 Hook Manager。

要求：

支持 hook 名称：
before_plan
after_plan
before_execute
after_execute
on_error
Hook 当前只做安全检查和记录，不需要插件系统。
before_execute 要检查 approved=true。
before_execute 要检查 plan 文件存在。
before_execute 要检查 rawdata_readonly=true。
after_execute 返回执行摘要。
异常转为结构化错误。

参考实现：

from __future__ import annotations

from pathlib import Path
from typing import Any


class HookError(Exception):
    pass


def run_before_plan(
    project_config: dict[str, Any],
    pipeline_path: str,
) -> list[str]:
    warnings: list[str] = []
    if not Path(pipeline_path).exists():
        raise HookError(f"Pipeline file not found: {pipeline_path}")

    safety = project_config.get("safety", {})
    if not safety.get("rawdata_readonly", True):
        warnings.append("rawdata_readonly is not enabled.")

    return warnings


def run_after_plan(plan: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if not plan.get("nodes"):
        warnings.append("Plan contains no nodes.")
    return warnings


def run_before_execute(
    project_config: dict[str, Any],
    plan_path: str,
    approved: bool,
) -> list[str]:
    warnings: list[str] = []

    if not approved:
        raise HookError("Execution requires explicit approval.")

    if not Path(plan_path).exists():
        raise HookError(f"Plan file not found: {plan_path}")

    safety = project_config.get("safety", {})
    if not safety.get("rawdata_readonly", True):
        raise HookError("Refusing to execute because rawdata_readonly is false.")

    if safety.get("allow_overwrite_derivatives", False):
        warnings.append("allow_overwrite_derivatives is enabled.")

    return warnings


def run_after_execute(summary: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if summary.get("status") not in {"SUCCESS", "PARTIAL"}:
        warnings.append(f"Pipeline finished with status={summary.get('status')}")
    return warnings


def run_on_error(exc: Exception) -> dict[str, Any]:
    return {
        "ok": False,
        "error_type": exc.__class__.__name__,
        "error": str(exc),
    }
5. 创建 backend/app/runtime/agent_plan.py

创建文件：

backend/app/runtime/agent_plan.py

目标：生成 deterministic plan.json。

提供函数：

create_agent_plan(
    agent_run_id: str,
    project_config_path: str,
    pipeline_path: str,
) -> dict

功能要求：

读取 project_config。
读取 pipeline YAML。
不执行 pipeline。
输出 plan.json 到：
work/agent_runs/{agent_run_id}/plan.json
plan 内容包含：
agent_run_id
mode: PLAN
project_config_path
pipeline_path
pipeline_id
run_id
nodes
expected_outputs
requires_approval: true
approved: false
risk_summary
warnings
调用 before_plan 和 after_plan hooks。
返回结构化 dict。

参考实现：

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.app.runtime.hook_manager import run_after_plan, run_before_plan
from backend.app.schemas.pipeline_schema import load_pipeline_yaml


def _load_project_config(path: str | Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("Missing dependency: PyYAML. Install with: pip install pyyaml") from exc

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Project config not found: {p}")

    return yaml.safe_load(p.read_text(encoding="utf-8"))


def create_agent_plan(
    agent_run_id: str,
    project_config_path: str,
    pipeline_path: str,
) -> dict[str, Any]:
    project_config = _load_project_config(project_config_path)
    warnings = run_before_plan(project_config, pipeline_path)

    pipeline = load_pipeline_yaml(pipeline_path)
    runtime = project_config.get("runtime", {})
    work_dir = runtime.get("work_dir", "./work")

    out_dir = Path(work_dir) / "agent_runs" / agent_run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    nodes = []
    expected_outputs: list[str] = []

    for node in pipeline.nodes:
        node_payload = {
            "id": node.id,
            "name": node.name,
            "backend": node.backend,
            "agent": node.agent,
            "parallel_level": node.parallel_level,
            "depends_on": node.depends_on,
            "outputs": node.outputs,
        }
        nodes.append(node_payload)
        expected_outputs.extend(node.outputs)

    plan = {
        "ok": True,
        "agent_run_id": agent_run_id,
        "agent": "orchestrator",
        "mode": "PLAN",
        "project_config_path": str(project_config_path),
        "pipeline_path": str(pipeline_path),
        "pipeline_id": pipeline.pipeline_id,
        "run_id": pipeline.execution.get("run_id", agent_run_id),
        "nodes_total": len(nodes),
        "nodes": nodes,
        "expected_outputs": expected_outputs,
        "requires_approval": True,
        "approved": False,
        "risk_summary": {
            "will_run_matlab": any("matlab" in node.backend for node in pipeline.nodes),
            "will_write_derivatives": any(
                "derivatives/" in output or "./derivatives/" in output
                for output in expected_outputs
            ),
            "will_modify_rawdata": False,
            "will_delete_files": False,
        },
        "warnings": warnings,
        "errors": [],
    }

    warnings.extend(run_after_plan(plan))
    plan["warnings"] = warnings

    plan_path = out_dir / "plan.json"
    plan_path.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    plan["plan_path"] = str(plan_path)

    return plan
6. 创建 backend/app/runtime/agent_runtime.py

创建文件：

backend/app/runtime/agent_runtime.py

目标：实现最小 deterministic Agent Runtime。

提供函数：

run_orchestrator_plan(...)
run_orchestrator_execute(...)

功能要求：

plan 模式：
调用 pipeline.plan tool
生成 plan.json
不执行 pipeline
execute 模式：
要求 approved=true
检查 plan.json 存在
调用 pipeline.execute tool
执行现有 run_pipeline
写 agent_summary.json
agent_summary 输出到：
work/agent_runs/{agent_run_id}/agent_summary.json
agent_summary 包含：
agent_run_id
agent
mode
approved
plan_path
pipeline_summary_path
pipeline_status
outputs
warnings
errors
不接真实 LLM。
不要做自然语言理解。
不要做异步后台任务。

参考实现：

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.app.runtime.agent_plan import _load_project_config, create_agent_plan
from backend.app.runtime.hook_manager import (
    run_after_execute,
    run_before_execute,
    run_on_error,
)
from backend.app.runtime.pipeline_executor import run_pipeline
from backend.app.runtime.tool_registry import assert_tool_allowed


def run_orchestrator_plan(
    agent_run_id: str,
    project_config_path: str,
    pipeline_path: str,
) -> dict[str, Any]:
    try:
        assert_tool_allowed("pipeline.plan", approved=True)
        return create_agent_plan(
            agent_run_id=agent_run_id,
            project_config_path=project_config_path,
            pipeline_path=pipeline_path,
        )
    except Exception as exc:
        return run_on_error(exc)


def run_orchestrator_execute(
    agent_run_id: str,
    project_config_path: str,
    pipeline_path: str,
    plan_path: str,
    approved: bool,
) -> dict[str, Any]:
    try:
        assert_tool_allowed("pipeline.execute", approved=approved)

        project_config = _load_project_config(project_config_path)
        warnings = run_before_execute(
            project_config=project_config,
            plan_path=plan_path,
            approved=approved,
        )

        plan_file = Path(plan_path)
        plan = json.loads(plan_file.read_text(encoding="utf-8"))

        if plan.get("pipeline_path") != str(pipeline_path):
            warnings.append("Pipeline path differs from plan pipeline_path.")

        summary = run_pipeline(project_config_path, pipeline_path)
        warnings.extend(run_after_execute(summary))

        runtime = project_config.get("runtime", {})
        work_dir = runtime.get("work_dir", "./work")
        out_dir = Path(work_dir) / "agent_runs" / agent_run_id
        out_dir.mkdir(parents=True, exist_ok=True)

        pipeline_summary_path = (
            Path(work_dir)
            / "pipeline_runs"
            / str(summary.get("run_id", plan.get("run_id", agent_run_id)))
            / "summary.json"
        )

        agent_summary = {
            "ok": summary.get("status") in {"SUCCESS", "PARTIAL"},
            "agent_run_id": agent_run_id,
            "agent": "orchestrator",
            "mode": "EXECUTE",
            "approved": approved,
            "plan_path": str(plan_path),
            "pipeline_id": summary.get("pipeline_id"),
            "pipeline_status": summary.get("status"),
            "pipeline_summary_path": str(pipeline_summary_path),
            "outputs": summary.get("outputs", []),
            "metrics": summary.get("metrics", {}),
            "warnings": warnings,
            "errors": summary.get("errors", []),
        }

        agent_summary_path = out_dir / "agent_summary.json"
        agent_summary_path.write_text(
            json.dumps(agent_summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        agent_summary["agent_summary_path"] = str(agent_summary_path)

        return agent_summary

    except Exception as exc:
        return run_on_error(exc)

如果 summary 中没有 outputs 或 metrics，不要报错。

7. 新增 backend/app/tools/agent_plan_cli.py

创建文件：

backend/app/tools/agent_plan_cli.py

功能：

默认 project config：
examples/project_config_dataset.yaml
默认 pipeline：
examples/pipeline_subject_preprocess.yaml
默认 agent_run_id：
agent_run_001
调用 run_orchestrator_plan。
打印 plan JSON。
返回码：
ok=true 返回 0
ok=false 返回 1

参考实现：

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.agent_runtime import run_orchestrator_plan


def main() -> int:
    project_config = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/project_config_dataset.yaml")
    pipeline = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("examples/pipeline_subject_preprocess.yaml")
    agent_run_id = sys.argv[3] if len(sys.argv) > 3 else "agent_run_001"

    result = run_orchestrator_plan(
        agent_run_id=agent_run_id,
        project_config_path=str(project_config),
        pipeline_path=str(pipeline),
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
8. 新增 backend/app/tools/agent_execute_cli.py

创建文件：

backend/app/tools/agent_execute_cli.py

功能：

默认 project config：
examples/project_config_dataset.yaml
默认 pipeline：
examples/pipeline_subject_preprocess.yaml
默认 agent_run_id：
agent_run_001
默认 plan_path：
work/agent_runs/agent_run_001/plan.json
必须显式传入：
--approve

否则不执行。

调用 run_orchestrator_execute。
打印 agent_summary JSON。
返回码：
ok=true 返回 0
ok=false 返回 2

参考实现：

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.agent_runtime import run_orchestrator_execute


def main() -> int:
    args = sys.argv[1:]
    approved = "--approve" in args
    args = [arg for arg in args if arg != "--approve"]

    project_config = Path(args[0]) if len(args) > 0 else Path("examples/project_config_dataset.yaml")
    pipeline = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_subject_preprocess.yaml")
    agent_run_id = args[2] if len(args) > 2 else "agent_run_001"

    plan_path = Path("work") / "agent_runs" / agent_run_id / "plan.json"

    result = run_orchestrator_execute(
        agent_run_id=agent_run_id,
        project_config_path=str(project_config),
        pipeline_path=str(pipeline),
        plan_path=str(plan_path),
        approved=approved,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
9. 创建 specs/tool_permission_runtime.md

创建文件：

specs/tool_permission_runtime.md

内容：

# Tool Permission Runtime

The MVP tool permission system prevents accidental execution.

## Tool Metadata

Each tool declares:

- read_only
- writes_files
- destructive
- requires_confirmation
- parallel_safe
- allowed_read_paths
- allowed_write_paths

## MVP Tools

### pipeline.plan

- Can read project config and pipeline YAML.
- Can write plan.json.
- Does not run MATLAB.
- Does not write derivatives.
- Does not require approval.

### pipeline.execute

- Runs the approved pipeline.
- Can call MATLAB through pipeline nodes.
- Can write work/, logs/, derivatives/, reports/.
- Requires explicit approval.

## Approval Rule

The CLI must require `--approve` before executing pipeline.execute.

If approval is missing, execution must fail safely.
10. 更新 README.md

追加第七步说明：

## Step 7: MVP Agent Runtime and Plan Mode

This step adds a deterministic Orchestrator Agent Runtime.

It supports:

- Plan Mode
- Execute Mode
- Tool Registry
- Tool Permissions
- Hooks
- Agent run summaries

It does not call a real LLM yet.

### Plan

```bash
python -m backend.app.tools.agent_plan_cli

Expected output:

work/agent_runs/agent_run_001/plan.json
Execute

Execution requires explicit approval:

python -m backend.app.tools.agent_execute_cli --approve

Expected output:

work/agent_runs/agent_run_001/agent_summary.json

If --approve is omitted, execution must fail safely.

Success Criteria
plan.json is created.
plan.json has mode=PLAN.
plan.json has requires_approval=true.
agent_execute_cli without --approve refuses to run.
agent_execute_cli with --approve runs the pipeline.
agent_summary.json is created.

---

## 11. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/agent_runtime_spec.md
specs/tool_permission_runtime.md
agents/orchestrator.md
backend/app/runtime/tool_registry.py
backend/app/runtime/hook_manager.py
backend/app/runtime/agent_plan.py
backend/app/runtime/agent_runtime.py
backend/app/tools/agent_plan_cli.py
backend/app/tools/agent_execute_cli.py
README.md

运行：

python -m backend.app.tools.agent_plan_cli

应该生成：

work/agent_runs/agent_run_001/plan.json

其中 plan.json 应包含：

{
  "ok": true,
  "agent": "orchestrator",
  "mode": "PLAN",
  "requires_approval": true,
  "approved": false
}

然后运行：

python -m backend.app.tools.agent_execute_cli

因为没有 --approve，应该安全失败，不能执行 pipeline。

然后运行：

python -m backend.app.tools.agent_execute_cli --approve

应该执行 pipeline，并生成：

work/agent_runs/agent_run_001/agent_summary.json

其中 agent_summary.json 应包含：

{
  "agent": "orchestrator",
  "mode": "EXECUTE",
  "approved": true
}

并且 pipeline 仍应生成：

reports/dataset_evaluation/dataset_summary.json
reports/dataset_evaluation/dataset_evaluation_report.md
reports/dataset_evaluation/dataset_evaluation_report.html
12. 重要限制

本步骤只做 deterministic Agent Runtime 骨架。

不要实现：

真实 LLM API
自然语言理解
多 Agent 对话
UI
FastAPI 服务
WebSocket
并行调度
GPU
DPABI pipeline
数据库
复杂长期记忆
后台复盘
Skill 自动生成

完成后请总结：

新增了哪些文件
修改了哪些文件
如何生成 plan
如何安全执行
如果没有 --approve 会发生什么
agent_summary.json 在哪里

'''
这一步主要做的是：

## 第七步：最小 Agent Runtime + Plan Mode + Tool/Hook 权限闭环
这是在前六步能跑的 pipeline 基础上， 包装成一个最小 Agent 系统 ，为后续接入 LLM、多 Agent 协作做准备。

### 核心目标
1. 实现 Agent Runtime 骨架
   
   - Deterministic Orchestrator Agent（ 不接真实 LLM ）
   - 借鉴 Claude Code 的 execution control 思想
   - 借鉴 Hermes 的 long-running agent 结构
2. Plan Mode / Execute Mode 分离
   
   - Plan Mode（只读） ：
     
     - 读取 project config 和 pipeline YAML
     - 验证 pipeline 结构
     - 生成 plan.json
     - 不执行 pipeline 、不写 derivatives、不运行 MATLAB
   - Execute Mode（需显式批准） ：
     
     - 需要 --approve 标志
     - 检查 plan.json 存在
     - 执行 pipeline
     - 生成 agent_summary.json
3. Tool Registry + 权限控制
   
   - 每个工具有权限元数据：
     - read_only - 是否只读
     - writes_files - 是否写文件
     - destructive - 是否可删除
     - requires_confirmation - 是否需要确认
     - parallel_safe - 是否可并行
   Tool 需确认 pipeline.plan 否 pipeline.execute 是
4. Hook Manager
   
   - before_plan - 计划前检查
   - after_plan - 计划后验证
   - before_execute - 执行前检查（approval、rawdata_readonly）
   - after_execute - 执行后验证
   - on_error - 错误处理
### 执行流程
```
Plan Mode:
  agent_plan_cli → run_orchestrator_plan → create_agent_plan → 
  plan.json

Execute Mode:
  agent_execute_cli --approve → run_orchestrator_execute → 
  run_pipeline → agent_summary.json
```
### 输出文件位置
```
work/agent_runs/{agent_run_id}/
├── plan.json              # 执行计划
└── agent_summary.json     # Agent 执行摘要
```
### 明确不做的事情
- ❌ 真实 LLM API
- ❌ 自主工具选择
- ❌ 自然语言规划
- ❌ 多 Agent 通信
- ❌ UI / FastAPI
- ❌ 数据库
- ❌ 后台 review
- ❌ 内存 mutation
- ❌ GPU 执行
- ❌ 并行执行
这一步已经 全部完成 并验证通过。成功实现了：

- Plan Mode 生成计划 ✅
- 无批准时拒绝执行 ✅
- 有批准时成功执行 ✅
- 生成 agent_summary.json ✅
'''