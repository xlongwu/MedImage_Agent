# 系统架构 (ARCHITECTURE)

## 1. 架构总览

MedImage Agent 采用四层架构，自上而下为：

```
┌──────────────────────────────────────────────────────────────┐
│                    Frontend Layer                             │
│  React 18 + TypeScript + Vite                                │
│  Pipeline Canvas | QC Report Viewer | Approval Gate UI       │
│  Insights Dashboard | Run History Timeline                   │
├──────────────────────────────────────────────────────────────┤
│                    API Layer                                  │
│  FastAPI + Pydantic + SSE                                    │
│  RESTful Endpoints | Streaming Logs | Health Checks          │
├──────────────────────────────────────────────────────────────┤
│                    Agent Runtime                              │
│  Plan-then-Execute                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐               │
│  │LLM Planner│→│  Plan    │→│Human Approval│               │
│  │(advisory) │  │Validator │  │    Gate      │               │
│  └──────────┘  └──────────┘  └──────┬───────┘               │
│                                     │ approved=true          │
├─────────────────────────────────────┼────────────────────────┤
│                    Pipeline Runtime ▼                        │
│  DAG Executor (Topological Sort)                             │
│  Scheduler (Subject-Level Parallel)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │Node Registry │  │ Tool Catalog │  │ GUI Agent    │       │
│  │(node→runner) │  │(permission)  │  │ Node         │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │ State Store  │  │ Hook System  │                         │
│  │(FS-based)    │  │(pre/post/app)│                         │
│  └──────────────┘  └──────────────┘                         │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │Error Diagnoser│ │Retry Runtime │                         │
│  └──────────────┘  └──────────────┘                         │
├──────────────────────────────────────────────────────────────┤
│                    Tools Layer                                │
│  Python Processing | SPM Wrappers | DPABI Contracts         │
│  GPU Acceleration (CuPy) | QC Modules | Report Writers      │
└──────────────────────────────────────────────────────────────┘
```

## 2. 各层详解

### 2.1 Frontend（React 18 + TypeScript + Vite）

**位置**：`src/frontend/src/`

**职责**：
- 用户交互界面
- Pipeline Canvas：可视化展示 pipeline DAG 和执行进度
- QC Report Viewer：展示 QC 报告、图表（ECharts）、指标
- Approval Gate UI：审批界面（plan 级确认 + step 级确认）
- Insights Dashboard：数据集概览、异常检测
- Run History Timeline：运行历史时间线
- 各处理步骤的独立面板（Motion QC、ALFF/ReHo/FC 等）

**约束**：
- 只能通过 HTTP API（`api.ts`）与后端通信
- 不能直接操作本地文件系统
- 所有文件读写通过 `/api/files/read`、`/api/logs/read` 等代理端点

**关键文件**：
- `src/frontend/src/App.tsx` — 主应用组件
- `src/frontend/src/api.ts` — API 调用封装
- `src/frontend/src/components/` — 各功能面板（40+ 组件）

### 2.2 API Layer（FastAPI + Pydantic）

**位置**：`src/backend/app/api/`

**职责**：
- 提供 RESTful API 端点
- 请求参数验证（Pydantic models）
- SSE（Server-Sent Events）流式日志推送
- 路径安全防护：所有文件读取通过 `path_safety.py` 代理

**路由模块**：
| 文件 | 职责 |
|------|------|
| `routes.py` | 核心路由：pipeline、agent、SPM、DPABI、rs-fMRI、QC、报告、实验跟踪 |
| `dashboard_routes.py` | Dashboard 数据聚合端点 |
| `planner_routes.py` | LLM Planner API（advisory） |
| `gui_agent_routes.py` | GUI Agent 会话管理 |
| `desktop_routes.py` | Electron 桌面配置 |
| `external_smoke_routes.py` | 外部工具冒烟测试 |
| `models.py` | 所有请求/响应 Pydantic 模型 |

**安全约束**：
- 所有文件读取通过 `read_safe_text_file()` 代理（`path_safety.py`）
- 只允许读取白名单目录：`examples/`、`work/`、`logs/`、`reports/`、`memory/`、`specs/`
- 只允许 `.json`、`.yaml`、`.yml`、`.md`、`.txt`、`.csv`、`.html`、`.log` 后缀

### 2.3 Agent Runtime（Plan-then-Execute）

**位置**：`src/backend/app/runtime/agent_runtime.py`

**职责**：
- 接收用户目标 → 生成 pipeline plan
- 通过 Approval Gate 控制执行
- 协调 LLM Planner（advisory）和 Pipeline Executor

**执行流程**：

```
1. 用户提交目标
2. run_orchestrator_plan() → 创建 plan（create_agent_plan）
3. Plan 返回给用户审批
4. 用户确认 approved=true
5. run_orchestrator_execute() →
   a. assert_tool_allowed("pipeline.execute", approved=true)
   b. run_before_execute() → 执行前 Hook
   c. run_pipeline() → 调用 Pipeline Executor
   d. run_after_execute() → 执行后 Hook
6. 返回 agent_summary
```

**关键函数**：
- `run_orchestrator_plan()` — 生成执行计划
- `run_orchestrator_execute()` — 审批后执行（必须 `approved=true`）

### 2.4 LLM Planner（规划顾问，非执行者）

**位置**：`src/backend/app/advisor/`

**职责**：
- 接收自然语言目标，生成结构化 pipeline plan 建议
- 提供参数建议、协议建议、QC 建议、错误诊断建议、文档问答
- **所有输出是建议性的（advisory）**，必须经过 Plan Validator 和 Approval Gate

**约束**：
- LLM 输出不能直接驱动 Pipeline Executor
- LLM 不能直接调用任何工具（tool）
- LLM 不能直接修改文件

**模块**：
| 文件 | 职责 |
|------|------|
| `parameter_advisor.py` | 参数建议 |
| `protocol_advisor.py` | 协议/流程建议 |
| `qc_report_advisor.py` | QC 报告解读建议 |
| `error_advisor.py` | 错误诊断建议 |
| `docs_qa_advisor.py` | 文档问答 |
| `advisor_safety.py` | Advisor 安全边界控制 |
| `advisor_router.py` | Advisor 路由分发 |
| `advisor_models.py` | Advisor 数据模型 |

### 2.5 Plan Validator

**当前状态**：Schema 验证已实现（`pipeline_schema.py`），Safety 验证计划在 M3 实现。

**位置**：`src/backend/app/schemas/pipeline_schema.py`

**职责**（当前 + 目标）：
- 校验 pipeline YAML 的 schema 完整性（已实现）
- 校验节点 ID 唯一性和依赖引用完整性（已实现）
- 校验参数合法性（计划 M3）
- 校验安全边界：不允许 pipeline 写入 rawdata（计划 M3）
- 校验 backend 可用性（计划 M3）
- 校验 GPU 需求与实际硬件匹配（计划 M3）

### 2.6 Pipeline Runtime（确定性执行引擎）

**位置**：`src/backend/app/runtime/pipeline_executor.py`

**职责**：
- 按 DAG 拓扑排序执行 pipeline 节点
- Subject 级并行调度（ThreadPoolExecutor）
- 状态持久化（文件系统，`work/states/<run_id>/`）
- 失败处理（`stop_on_failure`）

**执行模式**：

| 模式 | 说明 |
|------|------|
| `sequential` | 单线程顺序执行 |
| `local_parallel` | Subject 级并行（可配置 worker 数） |

**调度配置**：
```yaml
execution:
  mode: local_parallel
  max_workers: 4
  matlab_max_workers: 2
  gpu_max_workers: 4
  gpu_mode: prefer  # prefer / require / off
```

**关键模块**：
| 文件 | 职责 |
|------|------|
| `pipeline_executor.py` | DAG 执行引擎主逻辑 |
| `scheduler.py` | 并行调度配置和计划生成 |
| `state_store.py` | 文件系统状态持久化 |
| `hook_manager.py` | 前置/后置/审批 Hook |
| `error_diagnoser.py` | 错误分类和诊断 |
| `retry_runtime.py` | 失败重试机制 |
| `run_inspector.py` | 运行状态检查 |

### 2.7 Node Registry

**位置**：`src/backend/app/runtime/node_registry.py`

**职责**：
- 维护 `NODE_REGISTRY` 字典：`node_id → runner_function`
- 每个 runner 接受 `NodeExecutionContext` + `PipelineNode`（可选 `subject_record`、`subject_id`）
- 支持三种节点类型：
  - **Project-level**：不需要 subject 上下文（如数据检查、报告生成）
  - **Subject-level**：需要 `subject_record` 和 `subject_id`（如 SPM Realign、Motion QC）
  - **GPU-accelerated**：subject-level + GPU 后端（位于 `src/backend/app/nodes/`）

**当前注册的节点**（42 个）涵盖：
- 环境检查（`environment_check`、`spm_smoke_test`）
- 数据处理（`create_synthetic_bids`、`data_inspection`）
- SPM 预处理（`spm_realign_subject`、`spm_slice_timing_subject`、`spm_coregister_subject`、`spm_segment_subject`、`spm_normalize_subject`、`spm_smooth_subject`）
- QC（`motion_qc_subject`、`slice_timing_qc_dataset_report`、`registration_qc_dataset_report` 等）
- Python 处理（`nuisance_regression_subject`、`temporal_filtering_subject`、`alff_falff_subject`、`reho_subject`、`functional_connectivity_subject`）
- GPU 加速（`gpu_alff_subject`、`gpu_reho_subject` 等）
- DPABI 接口（`dpabi_capability_inspection`、`dpabi_preflight` 等）
- 报告和导出（`group_dataset_summary`、`rsfmri_report_exporter`、`rsfmri_report_package_validator`）
- 发布就绪检查（`project_release_readiness`、`docs_inventory`）

### 2.8 Tool Catalog（工具权限分级）

**位置**：`src/backend/app/runtime/tool_registry.py`

**职责**：
- 维护 `TOOL_REGISTRY`：每个工具声明权限等级
- 阻止未授权的工具执行

**权限等级**：
```python
ToolSpec(
    name="pipeline.execute",
    read_only=False,
    writes_files=True,
    destructive=False,
    requires_confirmation=True,    # ← 需要 approved=true
    parallel_safe=False,
    allowed_read_paths=[...],
    allowed_write_paths=[...],
)
```

**当前注册的工具**：
| 工具 | requires_confirmation | 说明 |
|------|----------------------|------|
| `pipeline.plan` | false | 生成 plan（只写 plan 文件） |
| `pipeline.execute` | true | 执行 pipeline（需要审批） |

### 2.9 GUI Agent Node

**位置**：`src/backend/app/api/gui_agent_routes.py`

**职责**（当前 + 目标）：
- 作为特殊的 pipeline node runner，处理需要人工定位或交互确认的步骤
- 典型场景：AC-PC 定位、特殊配准检查、人工 QC 确认

**约束**：
- GUI Agent 只能作为 pipeline node 被 Pipeline Executor 调用
- 不能接管整个系统的控制流
- 不能绕过 approval gate
- 当前默认 provider 只记录 mock SPM/DPABI GUI 步骤

**执行流程**：
```
Pipeline Executor 遇到 GUI Agent Node
  → 暂停 pipeline 执行
  → 在独立 GUI 沙箱中展示图像
  → 等待人工操作
  → 人工操作完成，结果写回 pipeline state
  → Pipeline 继续执行后续节点
```

### 2.10 QC / Report / Export 层

**位置**：`src/backend/app/tools/`

**职责**：
- 每个处理步骤后自动触发配套 QC
- 生成 Markdown + HTML 双格式报告
- 生成可复现性捆绑包（环境快照 + 文件校验和 + git 状态）

**关键模块**：
| 文件 | 职责 |
|------|------|
| `motion_qc.py` | 头动 QC（FD、DVARS） |
| `dataset_evaluator.py` | 数据集完整性评估 |
| `report_writer.py` | 报告生成 |
| `report_exporter.py` | 报告导出包 |
| `report_package_validator.py` | 报告完整性校验 |
| `reproducibility_bundle.py` | 可复现性捆绑包 |
| `release_readiness.py` | 发布就绪检查 |
| `group_dataset_summary.py` | 组水平汇总 |

### 2.11 Safety Boundary（安全边界）

详见 [`docs/SAFETY_BOUNDARIES.md`](SAFETY_BOUNDARIES.md)。核心要点：

| 边界 | 机制 | 位置 |
|------|------|------|
| rawdata 只读 | 策略约束 | `AGENTS.md`、`CLAUDE.md` |
| approval gate | `tool_registry.py` requires_confirmation | `src/backend/app/runtime/tool_registry.py` |
| 路径安全 | `path_safety.py` 目录白名单 | `src/backend/app/runtime/path_safety.py` |
| 允许写入目录 | `outputs/work/`、`outputs/logs/`、`outputs/derivatives/`、`outputs/reports/`、`outputs/exports/` | — |
| LLM 只建议 | 架构约束 | `AGENTS.md`、CLAUDE.md |
| GUI Agent 隔离 | 只能作为 node runner | `AGENTS.md` |

## 3. 数据流

```
Rawdata (只读)
  ↓ 读取 BIDS 数据
Pipeline Executor
  ↓ 调用 SPM/Python/GPU 节点处理
Derivatives (outputs/derivatives/)
  ↓ QC 模块读取
QC Reports (outputs/reports/)
  ↓ Report Exporter 导出
Exports (outputs/exports/)
```

中间状态写入 `outputs/work/states/<run_id>/`，日志写入 `outputs/logs/`。

## 4. 控制流

```
User Goal
  → Agent Runtime (run_orchestrator_plan)
  → Plan 生成
  → Human Approval Gate (approved=true)
  → Agent Runtime (run_orchestrator_execute)
  → Pipeline Executor (run_pipeline)
  → Node Registry (get_node_runner)
  → Tool Runner (SPM / Python / GPU / GUI Agent)
  → QC / Report / Export
```

## 5. 当前状态 vs 目标状态

| 组件 | 当前状态 | 目标状态 |
|------|---------|---------|
| Pipeline Runtime | ✅ 完整实现 | 稳定迭代 |
| Node Registry | ✅ 42 个节点 | M2：拆分为独立 tool catalog |
| Plan Schema Validator | ✅ 基础 schema 校验 | M3：完整 safety 校验 |
| LLM Planner | 🔄 Advisor 模块已实现 | M4：端到端自然语言→plan |
| GUI Agent Node | 🔄 基础端点已实现 | M5：真实 GUI 沙箱 |
| Plan Review Console | ❌ 未开始 | M6：前端可视化审批 |
| 真实数据沙箱 | ❌ 未开始 | M7：安全沙箱 + 报告闭环 |
| Audit Logger | ❌ 未实现（文档引用但文件不存在） | M2/M3 |

---

*最后更新：2025-07-18*
