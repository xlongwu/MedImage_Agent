你是我的工程搭建助手。前两步已经完成：

Step 1：完成项目工程骨架，并打通 MATLAB / SPM / DPABI 环境检查闭环。
Step 2：完成单节点执行闭环，可以运行一个 SPM smoke test 节点，并生成 result.json、state.json 和日志。

现在开始第三步。

第三步目标：实现“最小 Pipeline DAG 执行闭环”。

也就是说，现在不要做 UI，不要做完整 Agent Runtime，不要做多 Agent，不要做真实医学影像预处理。现在只做一个最小 pipeline executor：

- 读取 pipeline YAML
- 校验 pipeline schema
- 根据节点顺序执行多个节点
- 支持节点依赖检查
- 支持 node registry
- 支持 environment_check 节点
- 支持 spm_smoke_test 节点
- 为每个节点写 state JSON
- 为整个 pipeline 写 summary JSON
- 如果某个节点失败，pipeline 明确失败并停止
- 如果全部节点成功，pipeline summary 显示 SUCCESS

不要实现 UI。
不要实现 FastAPI 服务。
不要实现完整 Agent Runtime。
不要实现多 Agent 协作。
不要实现并行调度。
不要实现 DPABI pipeline。
不要实现 GPU。
不要处理真实医学影像数据。
不要修改 SPM / DPABI 源码。
不要引入数据库。
不要引入 Celery / Redis。
不要过度抽象。

本步骤只做最小 Pipeline Executor。

---

## 1. 新增 examples/pipeline_mvp.yaml

创建文件：

```text
examples/pipeline_mvp.yaml

内容如下：

pipeline_id: medimage_mvp_pipeline
version: "0.1.0"
modality: test
description: "Minimal MVP pipeline: environment check followed by SPM smoke test."

execution:
  stop_on_failure: true
  run_id: "run_mvp_001"

nodes:
  - id: environment_check
    name: Environment Check
    agent: system
    backend: matlab
    depends_on: []
    inputs: []
    outputs:
      - "./work/environment_check.json"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: spm_smoke_test
    name: SPM Smoke Test
    agent: spm-runner
    backend: matlab-spm
    depends_on:
      - environment_check
    inputs:
      - "./work/environment_check.json"
    outputs:
      - "./work/spm_smoke_test/result.json"
      - "./work/spm_smoke_test/smoothed.nii"
    params:
      image_shape: [20, 20, 20]
      smooth_fwhm: [4, 4, 4]
    parallel_level: project
    gpu_supported: false
    cache: false
2. 新增 specs/pipeline_executor.md

创建文件：

specs/pipeline_executor.md

内容：

# Pipeline Executor

The pipeline executor runs a YAML-defined pipeline.

## Scope

The MVP executor supports:

- sequential execution
- dependency validation
- stop on failure
- node registry
- node state writing
- pipeline summary writing

It does not support:

- parallel execution
- scheduling
- GPU resource allocation
- UI
- database
- real medical image preprocessing

## Execution Rules

1. Load project_config.yaml.
2. Load pipeline YAML.
3. Validate required pipeline fields.
4. Validate all node IDs are unique.
5. Validate dependencies refer to existing node IDs.
6. Execute nodes in YAML order.
7. A node can run only if all dependencies are SUCCESS.
8. If a node fails and stop_on_failure=true, stop the pipeline.
9. Write node state for every attempted node.
10. Write pipeline summary JSON at the end.

## Pipeline Status

- SUCCESS: all nodes succeeded
- FAILED: at least one node failed
- PARTIAL: pipeline stopped after some nodes succeeded and one failed
- INVALID: pipeline YAML is invalid

## Summary Output

```json
{
  "run_id": "run_mvp_001",
  "pipeline_id": "medimage_mvp_pipeline",
  "status": "SUCCESS",
  "nodes_total": 2,
  "nodes_success": 2,
  "nodes_failed": 0,
  "node_states": [
    "outputs/work/states/run_mvp_001/environment_check.json",
    "outputs/work/states/run_mvp_001/spm_smoke_test.json"
  ],
  "errors": []
}

---

## 3. 新增 backend/app/schemas/pipeline_schema.py

创建文件：

```text
backend/app/schemas/pipeline_schema.py

要求：

不要强依赖 pydantic。
使用 dataclasses 即可。
提供：
PipelineNode
PipelineSpec
PipelineValidationError
load_pipeline_yaml(path)
validate_pipeline_dict(data)
校验：
pipeline_id 存在
version 存在
nodes 存在且非空
node id 唯一
depends_on 引用的节点存在
required node fields 存在

参考实现方向：

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class PipelineValidationError(Exception):
    pass


@dataclass
class PipelineNode:
    id: str
    name: str
    agent: str
    backend: str
    depends_on: list[str] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    parallel_level: str = "project"
    gpu_supported: bool = False
    cache: bool = False


@dataclass
class PipelineSpec:
    pipeline_id: str
    version: str
    modality: str
    description: str
    execution: dict[str, Any]
    nodes: list[PipelineNode]


def validate_pipeline_dict(data: dict[str, Any]) -> PipelineSpec:
    ...
    

def load_pipeline_yaml(path: str | Path) -> PipelineSpec:
    ...

如果缺 PyYAML，请给出清晰错误：

pip install pyyaml
4. 新增 backend/app/runtime/node_registry.py

创建文件：

backend/app/runtime/node_registry.py

目标：把 node id 映射到实际 Python callable。

需要支持两个节点：

environment_check
spm_smoke_test

要求：

提供 NodeExecutionContext
提供 get_node_runner(node_id)
runner 输入 context 和 node
runner 返回 dict result
未知 node id 返回清晰错误

参考结构：

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from backend.app.schemas.pipeline_schema import PipelineNode
from backend.app.tools.matlab_runner import run_matlab_check
from backend.app.tools.spm_runner import run_spm_smoke_test


@dataclass
class NodeExecutionContext:
    run_id: str
    project_config: dict[str, Any]
    work_dir: str
    log_dir: str
    matlab_command: str
    spm_dir: str
    dpabi_dir: str


NodeRunner = Callable[[NodeExecutionContext, PipelineNode], dict[str, Any]]


def run_environment_check_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    output_json = f"{context.work_dir}/environment_check.json"
    return run_matlab_check(
        matlab_command=context.matlab_command,
        spm_dir=context.spm_dir,
        dpabi_dir=context.dpabi_dir,
        output_json=output_json,
        log_dir=context.log_dir,
        matlab_script_dir="./matlab",
    )


def run_spm_smoke_test_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    return run_spm_smoke_test(
        matlab_command=context.matlab_command,
        spm_dir=context.spm_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        matlab_script_dir="./matlab",
    )


NODE_REGISTRY: dict[str, NodeRunner] = {
    "environment_check": run_environment_check_node,
    "spm_smoke_test": run_spm_smoke_test_node,
}


def get_node_runner(node_id: str) -> NodeRunner:
    try:
        return NODE_REGISTRY[node_id]
    except KeyError as exc:
        raise KeyError(f"No node runner registered for node id: {node_id}") from exc
5. 修改 backend/app/runtime/state_store.py

在已有 state_store.py 基础上扩展，不要破坏已有函数。

新增函数：

write_pipeline_summary(...)

功能：

写入：

work/pipeline_runs/{run_id}/summary.json

summary 至少包含：

run_id
pipeline_id
status
started_at
ended_at
nodes_total
nodes_success
nodes_failed
nodes_skipped
node_states
errors

参考接口：

def write_pipeline_summary(
    run_id: str,
    pipeline_id: str,
    status: str,
    started_at: str,
    ended_at: str,
    node_states: list[str],
    node_results: list[dict[str, Any]],
    errors: list[str],
    work_dir: str,
) -> Path:
    ...
6. 新增 backend/app/runtime/pipeline_executor.py

创建文件：

backend/app/runtime/pipeline_executor.py

这是第三步核心。

功能要求：

接收：
project_config_path
pipeline_path
读取 project_config.yaml。
读取 pipeline_mvp.yaml。
构建 NodeExecutionContext。
校验 pipeline。
依次执行 nodes。
每个节点执行前检查 depends_on：
如果依赖节点不是 SUCCESS，则当前节点 SKIPPED 或 pipeline FAILED。
MVP 中建议直接 FAILED，并停止。
每个节点：
记录 started_at
调用 node runner
记录 ended_at
根据 result.ok 判断 SUCCESS / FAILED
调用 write_node_state
如果 stop_on_failure=true，节点失败后停止。
最后写 pipeline summary。
返回 summary dict。

不要引入并行。
不要引入线程。
不要引入数据库。

参考结构：

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.app.runtime.node_registry import NodeExecutionContext, get_node_runner
from backend.app.runtime.state_store import (
    determine_status_from_result,
    now_iso,
    write_node_state,
    write_pipeline_summary,
)
from backend.app.schemas.pipeline_schema import load_pipeline_yaml


def load_project_config(path: str | Path) -> dict[str, Any]:
    ...


def run_pipeline(
    project_config_path: str | Path,
    pipeline_path: str | Path,
) -> dict[str, Any]:
    ...

注意：

如果 pipeline YAML 无效，summary status 应该是 INVALID。
如果 node runner 不存在，summary status 应该是 FAILED。
如果 MATLAB 执行失败，不要崩溃，要写 summary。
所有异常尽量转成结构化 errors。
7. 新增 backend/app/tools/run_pipeline_cli.py

创建文件：

backend/app/tools/run_pipeline_cli.py

功能：

默认 project config：
examples/project_config.yaml
默认 pipeline：
examples/pipeline_mvp.yaml
调用 run_pipeline。
打印 summary JSON。
返回码：
SUCCESS 返回 0
INVALID 返回 1
FAILED / PARTIAL 返回 2

参考用法：

python -m backend.app.tools.run_pipeline_cli examples/project_config.yaml examples/pipeline_mvp.yaml

如果用户不传参数，则使用默认路径。

8. 更新 README.md

追加第三步说明：

## Step 3: Minimal Pipeline Executor

This step runs a minimal YAML-defined pipeline with two nodes:

1. environment_check
2. spm_smoke_test

Run:

```bash
python -m backend.app.tools.run_pipeline_cli examples/project_config.yaml examples/pipeline_mvp.yaml

Expected outputs:

work/environment_check.json
work/spm_smoke_test/input.nii
work/spm_smoke_test/smoothed.nii
work/spm_smoke_test/result.json
work/states/run_mvp_001/environment_check.json
work/states/run_mvp_001/spm_smoke_test.json
work/pipeline_runs/run_mvp_001/summary.json
logs/matlab_check_stdout.log
logs/matlab_check_stderr.log
logs/spm_smoke_test_stdout.log
logs/spm_smoke_test_stderr.log

Success criteria:

summary.json has status=SUCCESS.
both node states have status=SUCCESS.
spm_smoke_test produced smoothed.nii.

---

## 9. 验收标准

完成后，确认新增或修改了这些文件：

```text
examples/pipeline_mvp.yaml
specs/pipeline_executor.md
backend/app/schemas/pipeline_schema.py
backend/app/runtime/node_registry.py
backend/app/runtime/pipeline_executor.py
backend/app/runtime/state_store.py
backend/app/tools/run_pipeline_cli.py
README.md

运行：

python -m backend.app.tools.run_pipeline_cli examples/project_config.yaml examples/pipeline_mvp.yaml

成功后应该生成：

work/environment_check.json
work/spm_smoke_test/input.nii
work/spm_smoke_test/smoothed.nii
work/spm_smoke_test/result.json
work/states/run_mvp_001/environment_check.json
work/states/run_mvp_001/spm_smoke_test.json
work/pipeline_runs/run_mvp_001/summary.json

其中：

work/pipeline_runs/run_mvp_001/summary.json

应该包含：

{
  "run_id": "run_mvp_001",
  "pipeline_id": "medimage_mvp_pipeline",
  "status": "SUCCESS",
  "nodes_total": 2,
  "nodes_success": 2,
  "nodes_failed": 0
}

如果 environment_check 失败，spm_smoke_test 不应该继续执行，summary 应该显示 FAILED 或 PARTIAL，并清楚记录错误。

如果 pipeline YAML 中 depends_on 指向不存在的节点，程序应该显示 INVALID，而不是执行任何节点。

10. 重要限制

本步骤只做最小 Pipeline DAG 执行闭环。

不要实现：

UI
FastAPI 服务
Agent Runtime
多 Agent
并行调度
GPU
DPABI pipeline
真实医学影像数据处理
数据库
复杂缓存系统

完成后请总结：

新增了哪些文件
修改了哪些文件
如何运行 pipeline
成功输出是什么
如果失败应该看哪些日志


'''
这一步主要实现的是**"最小 Pipeline DAG 执行闭环"**，也就是让项目能够按照 YAML 配置顺序执行多个节点，并支持节点依赖检查和整体 Pipeline 状态管理。

具体来说，完成了以下工作：

## 1. 定义了 Pipeline 执行规范
- Pipeline Schema ( backend/app/schemas/pipeline_schema.py )：使用 dataclass 定义 Pipeline 数据结构，包含：
  
  - Pipeline 级别字段（pipeline_id、version、modality、execution 配置）
  - Node 级别字段（id、name、agent、backend、depends_on、inputs、outputs、params 等）
  - 校验逻辑：必填字段检查、节点 ID 唯一性、依赖节点存在性校验
- Pipeline Executor 规范 ( specs/pipeline_executor.md )：定义执行规则：
  
  - 顺序执行节点
  - 依赖检查（节点只能在前置节点 SUCCESS 后执行）
  - 失败停止策略（stop_on_failure）
  - Pipeline 状态定义（SUCCESS、FAILED、PARTIAL、INVALID）
## 2. 实现了节点注册和调度机制
Node Registry ( backend/app/runtime/node_registry.py )：

- 将 node_id 映射到实际 Python 执行函数
- 当前支持两个节点：
  - environment_check → run_environment_check_node
  - spm_smoke_test → run_spm_smoke_test_node
- 提供 NodeExecutionContext 传递配置和上下文
## 3. 实现了 Pipeline 执行器
Pipeline Executor ( backend/app/runtime/pipeline_executor.py )：

- 加载 project_config.yaml 和 pipeline YAML
- 校验 Pipeline 结构有效性
- 按顺序执行节点，每个节点：
  - 检查依赖是否满足（所有 depends_on 节点状态为 SUCCESS）
  - 从 Registry 获取 runner 并执行
  - 记录 started_at / ended_at
  - 写入节点状态 JSON
- 如果 stop_on_failure=true ，节点失败时停止后续执行
- 最后写入 Pipeline Summary JSON
## 4. 扩展了状态存储
State Store ( backend/app/runtime/state_store.py )：

- 新增 write_pipeline_summary() 函数
- 汇总所有节点执行结果
- 计算统计信息（total/success/failed/skipped）
- 输出到 work/pipeline_runs/{run_id}/summary.json
## 5. 完整的执行流程
```
Pipeline YAML (pipeline_mvp.yaml)
    ↓
Schema Validation
    ↓
Sequential Node Execution:
    ├── Node 1: environment_check
    │      ├── Check deps (none)
    │      ├── Run → MATLAB check
    │      └── Write state
    │
    └── Node 2: spm_smoke_test
           ├── Check deps (env_check SUCCESS?)
           ├── Run → MATLAB SPM smoke
           └── Write state
    ↓
Write Pipeline Summary
```
## 6. 这一步不做的事情
- 不实现并行执行（顺序执行）
- 不实现复杂调度策略
- 不实现 GPU 资源分配
- 不实现真实医学影像预处理
- 不实现 UI 或 FastAPI 服务
- 不实现数据库持久化
- 不实现复杂缓存系统
## 核心交付
这是一个 最小可执行的 Pipeline DAG 系统 ，验证了：

- ✅ YAML 定义的 Pipeline 可以被解析和执行
- ✅ 节点依赖关系可以被正确检查和执行
- ✅ 节点失败可以阻止后续节点执行（stop_on_failure）
- ✅ Pipeline 整体状态可以被正确汇总和记录
- ✅ 每个节点和整个 Pipeline 都有完整的状态追踪
这为第四步（并行执行、真实预处理节点、Agent Runtime）打下了基础！
'''