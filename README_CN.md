# MedImage Agent

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61dafb)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0%2B-3178c6)](https://www.typescriptlang.org/)

MedImage Agent 是一个面向静息态 fMRI（rs-fMRI）研究的**确定性 Agentic Pipeline 工程平台**。它借鉴 Hermes Agent 的 Plan-then-Execute 架构思想，但摒弃了通用 LLM Agent 的开放式对话循环，构建了一个安全、可复现、可审计的医学影像分析工作流系统。

**核心定位**：医学影像 AI workflow / agentic pipeline / research engineering platform

---

## 目录

- [项目背景与问题](#项目背景与问题)
- [核心设计理念](#核心设计理念)
- [系统架构](#系统架构)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [核心功能模块](#核心功能模块)
- [安全机制](#安全机制)
- [当前状态与边界](#当前状态与边界)
- [开发计划](#开发计划)
- [文档](#文档)

---

## 项目背景与问题

在 rs-fMRI 研究领域，预处理流程高度依赖研究者的手动操作和经验判断。典型的流程需要使用 SPM（MATLAB）、DPABI 等工具，涉及十几个步骤，每个步骤都有大量参数需要配置。这带来了三个核心问题：

1. **易错性**：手动操作容易遗漏步骤或配置错误参数，导致结果不可靠
2. **不可复现**：研究者在论文中往往无法完整记录所有参数和软件版本，他人难以复现
3. **无审计性**：传统脚本式 pipeline 缺乏执行过程的完整记录，无法追溯"何时、何人、用何参数、生成了何结果"

同时，通用 LLM Agent（如 Claude Code）虽然智能，但直接控制医学数据存在安全风险——可能误删文件、修改原始数据，且 LLM 的随机性会破坏科学可复现性。

---

## 核心设计理念

### 为什么不是普通 Pipeline？

传统 pipeline 是静态脚本，缺乏智能规划能力。MedImage Agent 引入了 **Agent Runtime**，能够根据用户目标自动规划 pipeline 结构，但执行过程完全确定性。

### 为什么不是普通聊天机器人？

通用 LLM Agent 采用开放式对话循环，存在随机性和安全风险。MedImage Agent 采用 **Plan-then-Execute** 模式：
- **Agent 只规划**：将用户目标分解为 pipeline plan
- **引擎负责执行**：确定性 DAG 引擎严格执行，无随机性
- **人工确认关键步骤**：Approval Gate 确保研究者的专业判断始终在位

### 与 Hermes Agent 的关系

借鉴 Hermes Agent 的"规划-执行"架构思想，但进行了领域化重构：
- 保留 Plan-then-Execute 的核心范式
- 替换开放式对话为确定性 pipeline 执行
- 增加医学影像特有的安全机制（rawdata 保护、权限分级、审计日志）

---

## 系统架构

系统分为四层：

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend Layer                          │
│  React 18 + TypeScript + Vite + ECharts                     │
│  Pipeline Canvas | QC Report Viewer | Run History Timeline  │
│  Insights Dashboard | Approval Gate UI                      │
├─────────────────────────────────────────────────────────────┤
│                      API Layer                               │
│  FastAPI + Pydantic + asyncio + SSE (Server-Sent Events)    │
│  RESTful Endpoints | Streaming Logs | Health Checks         │
├─────────────────────────────────────────────────────────────┤
│                      Agent Runtime                           │
│  Plan-then-Execute | LLM Advisor | Approval Gate            │
│  Tool Registry (权限分级) | SessionDB | Audit Logger        │
├─────────────────────────────────────────────────────────────┤
│                      Pipeline Runtime                        │
│  DAG Executor (拓扑排序) | Scheduler (subject-level 并行)   │
│  Node Registry | State Store | Hook System                  │
│  Error Diagnoser | Retry Runtime | Reproducibility Bundle   │
└─────────────────────────────────────────────────────────────┘
```

### 数据流 / 控制流 / 审计流

**数据流**：
```
Rawdata (只读) → Pipeline Executor → Derivatives → QC → Reports
```

**控制流**：
```
User Goal → Agent Runtime (Plan) → Approval Gate → Pipeline Executor (Execute) → Results
```

**审计流**：
```
Every Operation → Audit Logger → SessionDB → Run History → Reproducibility Bundle
```

---

## 技术栈

### 前端
- **框架**：React 18 + TypeScript
- **构建工具**：Vite
- **可视化**：ECharts（QC 图表、运动参数曲线、ALFF/ReHo 分布图）
- **状态管理**：React Hooks
- **API 通信**：Fetch API + SSE 流式推送

### 后端
- **框架**：FastAPI（Python 3.10+）
- **异步**：asyncio + async/await
- **数据验证**：Pydantic
- **文件服务**：静态文件托管

### Pipeline Runtime
- **执行引擎**：自研 DAG 执行引擎（拓扑排序）
- **调度器**：自研 Scheduler（subject-level 并行）
- **状态管理**：文件系统 State Store（run_id 隔离）
- **Hook 系统**：pre / post / approval 三类 Hook
- **错误处理**：Error Diagnoser（错误分类）+ Retry Runtime（重试策略）

### Agent Runtime
- **架构模式**：Plan-then-Execute
- **规划器**：Agent Runtime（目标分解为 pipeline plan）
- **审批门**：Approval Gate（人工确认关键步骤）
- **工具注册表**：Tool Registry（readonly / write / destructive 三级权限）
- **LLM Advisor**：建议生成（非控制执行）
- **会话数据库**：SessionDB（SQLite，记录 plan/execution/history）

### 医学影像处理
- **核心算法**（Python 原生实现）：
  - ALFF / fALFF（基于 FFT 的功率谱计算）
  - ReHo（Kendall's W，27 邻域）
  - Functional Connectivity（ROI 时间序列相关）
  - Nuisance Regression（线性回归去噪）
  - Temporal Filtering（带通滤波）
  - Motion QC（FD、DVARS、逐帧位移）
- **数据格式**：BIDS（Brain Imaging Data Structure）

### MATLAB / SPM / DPABI 集成
- **集成模式**：Contract-only 设计（预留扩展）
- **SPM 工具**：Realign、Slice Timing、Smooth、Normalize、Coregister、Segment
- **DPABI**：插件式接入接口（预留扩展）

### GPU 加速
- **状态**：已实现（5 个模块）
- **后端**：CuPy（主） + 自动 NumPy CPU 回退
- **加速模块**：ALFF/fALFF、ReHo、Nuisance Regression、Temporal Filtering、Functional Connectivity
- **设计模式**：三后端（NumPy / CuPy / 调度器） + `prefer_gpu` / `require_gpu` 参数
- **内存安全**：大数组 z 切片分块处理、GPU 内存估算工具
- **调度**：独立 `gpu_max_workers`（上限 4） + `gpu_mode`（prefer / require / off）

### 安全与审计
- **路径安全**：Path Safety（规范化、防目录遍历、work_dir 隔离）
- **权限控制**：Tool Registry 权限分级
- **审计日志**：Audit Logger（操作日志、结果日志）
- **原始数据保护**：Rawdata 只读访问

---

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- MATLAB + SPM12（可选，用于 SPM 预处理步骤）
- CuPy（可选，用于 GPU 加速；`pip install cupy-cuda12x`）

### 安装依赖

```bash
# 后端依赖
pip install -r requirements.txt

# 前端依赖
cd frontend && npm install
```

### 启动服务

```bash
# 启动后端（开发模式）
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

# 启动前端（开发模式）
cd frontend && npm run dev
```

### Docker 演示模式

```bash
# 启动容器化演示（不含 MATLAB）
docker compose -f deploy/docker-compose.demo.yml up --build
```

### 运行示例

```bash
# 生成合成 BIDS 数据
python -m backend.app.tools.synthetic_bids

# 运行数据集评估
python -m backend.app.tools.run_dataset_evaluation_cli examples/project_config_dataset.yaml

# 运行 SPM 头动校正 + Motion QC（需审批）
python -m backend.app.tools.run_rsfmri_spm_realign_motion_qc_cli \
  examples/project_config_dataset.yaml \
  examples/pipeline_rsfmri_spm_realign_motion_qc.yaml \
  --approve

# 运行 GPU 加速 ALFF（含 CPU 对比基准测试）
python -m backend.app.tools.gpu_benchmark_cli

# 运行 GPU 加速 ReHo
python -c "
from src.backend.app.tools.gpu_reho_runner import run_reho_subject
result = run_reho_subject('sub-001', 'derivatives/spm_smooth/sub-001/func/sub-001_task-rest_bold_smooth.nii', './derivatives', prefer_gpu=True)
print(f'Backend: {result[\"gpu_backend\"]}, Runtime: {result[\"runtime_seconds\"]}s')
"
```

---

## 项目结构

```
MedImage_Agent/
├── src/
│   ├── backend/
│   │   └── app/
│   │       ├── api/                    # FastAPI 路由
│   │       │   └── routes.py
│   │       ├── core/                   # 核心配置与模型
│   │       │   ├── config.py
│   │       │   └── models.py
│   │       ├── runtime/                # Pipeline + Agent Runtime
│   │       │   ├── agent_runtime.py    # Agent 规划与执行
│   │       │   ├── pipeline_executor.py # DAG 执行引擎
│   │       │   ├── scheduler.py        # 并行调度器
│   │       │   ├── node_registry.py    # 节点注册表
│   │       │   ├── state_store.py      # 状态持久化
│   │       │   ├── hook_manager.py     # Hook 系统
│   │       │   ├── error_diagnoser.py  # 错误诊断
│   │       │   ├── retry_runtime.py    # 重试机制
│   │       │   └── run_inspector.py    # 运行检查器
│   │       ├── nodes/                  # Pipeline 节点处理函数
│   │       │   ├── gpu_alff_node.py    # GPU ALFF 节点
│   │       │   ├── gpu_reho_node.py    # GPU ReHo 节点
│   │       │   ├── gpu_nuisance_regression_node.py
│   │       │   ├── gpu_temporal_filtering_node.py
│   │       │   └── gpu_functional_connectivity_node.py
│   │       ├── tools/                  # 工具模块
│   │       │   ├── alff_falff.py       # ALFF/fALFF 计算
│   │       │   ├── alff_compute.py     # ALFF GPU 后端 (NumPy/CuPy/PyTorch)
│   │       │   ├── reho.py             # ReHo 计算
│   │       │   ├── reho_compute.py     # ReHo GPU 后端 (NumPy/CuPy)
│   │       │   ├── functional_connectivity.py  # 功能连接
│   │       │   ├── functional_connectivity_compute.py  # FC GPU 后端
│   │       │   ├── nuisance_regression.py      # 去噪回归
│   │       │   ├── nuisance_regression_compute.py  # NR GPU 后端
│   │       │   ├── temporal_filtering.py       # 时间滤波
│   │       │   ├── temporal_filtering_compute.py  # TF GPU 后端
│   │       │   ├── motion_qc.py        # 运动 QC
│   │       │   ├── data_inspector.py   # 数据检查
│   │       │   ├── dataset_evaluator.py        # 数据集评估
│   │       │   ├── report_writer.py    # 报告生成
│   │       │   ├── report_validator.py # 报告验证
│   │       │   ├── reproducibility_bundle.py   # 可复现包
│   │       │   ├── synthetic_bids.py   # 合成数据生成
│   │       │   ├── gpu_memory.py       # GPU 内存监控
│   │       │   ├── gpu_*.py            # GPU Runner 与 Contract
│   │       │   └── spm_*.py            # SPM 集成 Runner
│   │       ├── safety/                 # 安全模块
│   │       │   ├── path_safety.py      # 路径安全
│   │       │   ├── tool_registry.py    # 工具权限注册
│   │       │   └── audit_logger.py     # 审计日志
│   │       └── main.py                 # FastAPI 入口
│   └── frontend/
│       ├── src/
│       │   ├── App.tsx                 # 主应用组件
│       │   ├── components/             # UI 组件
│       │   ├── api.ts                  # API 封装
│       │   └── types.ts                # TypeScript 类型
│       └── package.json
├── docs/                               # 项目文档
│   ├── architecture.md                 # 架构设计文档
│   ├── agent_runtime_spec.md           # Agent Runtime 规范
│   └── pipeline_executor.md            # Pipeline Executor 规范
├── examples/                           # 示例配置
│   ├── project_config_dataset.yaml
│   └── pipeline_*.yaml
├── tests/                              # 测试
│   └── unit/                           # 单元测试
├── deploy/                             # 部署配置
│   ├── docker-compose.demo.yml
│   ├── backend.Dockerfile
│   └── frontend.Dockerfile
├── requirements.txt                    # Python 依赖
└── README.md                           # 本文件
```

---

## 核心功能模块

### 1. Pipeline Runtime（确定性执行引擎）

- **DAG 执行**：基于拓扑排序的依赖执行，确保步骤按正确顺序运行
- **并行调度**：subject-level 并行处理，提升多被试数据集处理效率
- **状态持久化**：每步完成后立即写入状态文件，支持断点续跑
- **Hook 系统**：pre-hook（参数校验）、post-hook（结果验证）、approval-hook（人工确认）

### 2. Agent Runtime（智能规划层）

- **Plan-then-Execute**：Agent 生成 pipeline plan，确定性引擎执行
- **Approval Gate**：plan 级审批（整体确认）+ step 级审批（destructive 操作确认）
- **Tool Registry**：工具注册时声明权限级别，实现最小权限原则
- **LLM Advisor**：自然语言描述转 pipeline 配置建议（非强制）

### 3. 医学影像处理

| 模块 | 功能 | 状态 |
|------|------|------|
| ALFF / fALFF | 低频振幅计算 | ✅ 已实现 |
| ReHo | 局部一致性计算 | ✅ 已实现 |
| Functional Connectivity | 功能连接矩阵 | ✅ 已实现 |
| Motion QC | 头动指标（FD/DVARS） | ✅ 已实现 |
| Nuisance Regression | 去噪回归 | ✅ 已实现 |
| Temporal Filtering | 带通滤波 | ✅ 已实现 |
| SPM Realign | 头动校正 | ✅ 已实现 |
| SPM Slice Timing | 层时间校正 | ✅ 已实现 |
| SPM Normalize | 空间标准化 | ✅ 已实现 |
| SPM Smooth | 空间平滑 | ✅ 已实现 |
| SPM Coregister | 配准 | ✅ 已实现 |
| SPM Segment | 分割 | ✅ 已实现 |
| GPU 加速 | CuPy 加速矩阵运算（5 个模块）| ✅ 已实现 |

### 4. QC 与报告

- **自动化 QC**：Motion QC、数据集完整性检查、异常值检测
- **报告生成**：Markdown + HTML 双格式，含 ECharts 可视化
- **报告验证**：Schema 校验、数据一致性检查
- **可复现包**：环境快照 + 文件 checksum + git 状态

### 5. 数据管理

- **BIDS 支持**：符合 Brain Imaging Data Structure 规范
- **合成数据**：synthetic_bids.py 生成测试数据，无需真实患者数据即可开发验证
- **数据集评估**：自动检查完整性、扫描参数一致性、异常值

---

## 安全机制

MedImage Agent 采用多层安全设计，确保研究数据不被误修改：

### 1. 路径安全（Path Safety）
- 所有路径强制规范化，禁止目录遍历攻击
- 操作强制限制在 work_dir 内，禁止访问系统敏感路径
- rawdata 目录标记为只读，任何写入操作被拒绝

### 2. 工具权限分级（Tool Registry）
- **readonly**：只读操作（如数据检查、报告生成）
- **write**：写入操作（如保存中间结果）
- **destructive**：破坏性操作（如删除、覆盖），自动触发 Approval Gate

### 3. 审批门（Approval Gate）
- **plan 级审批**：整体 pipeline 执行前需确认
- **step 级审批**：destructive 操作需二次确认
- 未审批的操作安全失败，不会执行

### 4. 审计日志（Audit Logger）
- 记录所有操作的时间、用户、工具、参数、结果
- 支持 Run History 全追溯
- 审计日志本身不可修改

### 5. 原始数据保护
- rawdata 以只读方式访问
- 所有输出写入隔离的 derivatives 目录
- 合成数据模式（synthetic_only）支持无风险演示

---

## 当前状态与边界

### 已实现
- ✅ 完整的 Pipeline Runtime（DAG 执行、并行调度、状态持久化）
- ✅ Agent Runtime（Plan-then-Execute、Approval Gate、Tool Registry）
- ✅ 核心影像算法（ALFF/fALFF、ReHo、Functional Connectivity）
- ✅ SPM 集成接口（Contract-only 设计，6 个核心模块）
- ✅ QC 自动化（Motion QC、数据集评估）
- ✅ 报告系统（Markdown/HTML 双格式、可复现包）
- ✅ 前端可视化（Pipeline Canvas、QC Viewer、Run History、Insights Dashboard）
- ✅ 安全机制（Path Safety、权限分级、审计日志）
- ✅ 错误诊断与重试系统

### 设计中 / 预留扩展
- ✅ GPU 加速（5 个模块：ALFF/fALFF、ReHo、Nuisance Regression、Temporal Filtering、Functional Connectivity；CuPy + CPU 回退）
- 🔄 DPABI 完整集成（接口设计完成，待实现）
- 🔄 分布式执行（多机并行，架构预留）
- 🔄 Docker 容器化一键部署（配置文件已创建）
- 🔄 真实临床数据验证（当前使用合成数据）

### 明确边界
- **非临床产品**：本项目定位为研究工程平台，不用于临床诊断或临床决策
- **合成数据演示**：当前默认使用合成 BIDS 数据，真实数据需额外配置
- **MATLAB 依赖可选**：SPM 步骤需要 MATLAB，核心算法不依赖

---

## 开发计划

| 阶段 | 目标 | 状态 |
|------|------|------|
| Phase 1 | Pipeline Runtime + 核心算法 | ✅ 完成 |
| Phase 2 | Agent Runtime + 安全机制 | ✅ 完成 |
| Phase 3 | SPM 集成 + QC 系统 | ✅ 完成 |
| Phase 4 | 前端可视化 + 报告系统 | ✅ 完成 |
| Phase 5 | GPU 加速 + 性能优化 | ✅ 完成 |
| Phase 6 | 真实数据验证 + 论文发表 | 📋 计划中 |

---

## 文档

- [架构设计文档](docs/architecture.md)
- [Agent Runtime 规范](docs/agent_runtime_spec.md)
- [Pipeline Executor 规范](docs/pipeline_executor.md)

---

## 许可证

本项目用于学术研究目的。

---

**注意**：MedImage Agent 是一个医学影像研究工作流平台 / agentic pipeline system / rs-fMRI preprocessing and analysis engineering platform，不用于临床诊断或医疗决策。
