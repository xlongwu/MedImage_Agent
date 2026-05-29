# AGENTS.md — MedImage Agent 开发者指南

本文档供 **Codex、Claude Code 等代码 Agent** 阅读，用于理解项目结构、遵守开发规则、安全地迭代此仓库。

---

## 1. 项目概述

MedImage Agent 是一个**确定性 Agentic Pipeline 工程平台**，面向静息态 fMRI (rs-fMRI) 研究。它采用 **Plan-then-Execute** 架构：Agent Runtime 根据用户目标生成结构化 pipeline plan，Pipeline Runtime 以 DAG 形式确定性执行。LLM 只做规划和建议，不直接控制执行。

**核心定位**：医学影像 AI 工作流 / Agentic Pipeline / 研究工程平台

**非临床产品**：本项目定位为研究工程平台，不用于临床诊断或临床决策。

---

## 2. 架构分层（自上而下）

```
Frontend (React 18 + TypeScript + Vite)
    ↓ 仅通过 HTTP API 通信，不直接操作文件系统
API Layer (FastAPI + Pydantic) — src/backend/app/api/
    ↓
Agent Runtime (Plan-then-Execute + Approval Gate) — src/backend/app/runtime/agent_runtime.py
    ↓
Pipeline Runtime (DAG Executor + Scheduler) — src/backend/app/runtime/pipeline_executor.py
    ↓
Node Registry (可插拔节点运行器) — src/backend/app/runtime/node_registry.py
    ↓
Tools (处理模块 / QC / SPM / MATLAB / GPU) — src/backend/app/tools/
```

### 各层职责

| 层 | 职责 | 关键文件 |
|---|---|---|
| Frontend | 用户交互、pipeline 可视化、QC 查看、审批界面 | `src/frontend/src/` |
| API Layer | RESTful 端点、SSE 流、请求验证 | `src/backend/app/api/routes.py` |
| Agent Runtime | 计划生成、审批门控、LLM 顾问调用 | `src/backend/app/runtime/agent_runtime.py` |
| Pipeline Runtime | DAG 拓扑排序执行、并行调度、状态持久化 | `src/backend/app/runtime/pipeline_executor.py` |
| Node Registry | 节点 ID → 运行器函数映射 | `src/backend/app/runtime/node_registry.py` |
| Tools | 所有处理算法、QC、报告、SPM/MATLAB/DPABI 封装 | `src/backend/app/tools/` |

---

## 3. 常用命令

### 安装依赖

```bash
pip install -r requirements.txt
cd src/frontend && npm install
```

### 启动服务

```bash
# 后端（端口 8000）
uvicorn src.backend.app.main:app --host 127.0.0.1 --port 8000

# 前端（端口 5173）
cd src/frontend && npm run dev

# 一键启动
./start.sh          # Linux/macOS
start.bat           # Windows
```

### Docker demo（不含 MATLAB）

```bash
docker compose -f deploy/docker-compose.demo.yml up --build
```

### 运行测试

```bash
# 全量测试
pytest

# 单个测试文件
pytest tests/unit/test_motion_qc.py

# 单个测试用例
pytest tests/unit/test_pipeline_schema.py -k test_validates_minimal_pipeline
```

### CI

GitHub Actions 在每次 push 和 PR 时自动运行：

- **backend job**：Python 3.11 + `pytest --tb=short`
- **frontend job**：Node 20 + `npm ci` + `npm run build`

CI 不依赖 MATLAB/SPM/DPABI/GPU。配置见 `.github/workflows/ci.yml`。

### CLI 工具

```bash
python -m src.backend.app.tools.run_pipeline_cli examples/project_config.yaml examples/pipeline_mvp.yaml

python -m src.backend.app.tools.run_rsfmri_spm_realign_motion_qc_cli \
  examples/project_config_dataset.yaml \
  examples/pipeline_rsfmri_spm_realign_motion_qc.yaml \
  --approve
```

### 构建前端

```bash
cd src/frontend && npm run build
```

---

## 4. 代码修改规则

### 4.1 先读后改

在修改任何文件之前，必须先用 `read_file` 等工具阅读其当前内容。不要基于记忆或猜测修改代码。

### 4.2 先计划再实现

对于多文件改动或架构调整，先向用户提交计划（plan），获得确认后再动手。对于单文件小修改，口头说明即可。

### 4.3 小步提交

每次修改聚焦一个目标。避免在一次 PR 中混杂多个不相关的变更。

### 4.4 修改后必须说明

每次代码修改完成后，必须在回复中说明：

1. **改了什么文件**（列出所有被修改的文件路径）
2. **运行了什么测试**（列出 pytest 命令及结果）
3. **还有什么风险**（已知的副作用、未覆盖的边界情况、需要的后续测试）

### 4.5 测试要求

- 修改已有功能 → 确保已有测试仍通过
- 新增功能 → 必须添加至少一个单元测试
- 新增 pipeline node → 必须添加对应的 pipeline YAML 和测试

---

## 5. 禁止事项（绝对不可违反）

### 5.1 不允许修改 rawdata

`data/` 目录和任何原始 BIDS 数据**永远只读**。所有衍生输出写入 `outputs/derivatives/`。

### 5.2 不允许绕过 approval gate

所有会写文件、运行 MATLAB/SPM/DPABI、修改 derivatives 的操作**必须经过 approval gate**。默认 `approved=false`，未经明确审批的操作必须安全失败。

### 5.3 不允许大规模无边界重构

不要在没有明确需求的情况下重写核心模块。局部改动优于全局重写。

### 5.4 不允许硬编码私密信息

不要把 API key、绝对私有路径、实验数据路径写死进代码或文档。使用环境变量或配置文件。

### 5.5 不允许前端直接操作本地文件系统

前端只能通过后端 API 访问数据。不允许前端代码直接读写文件。

### 5.6 不允许把 LLM 当作执行引擎

LLM 只能做**规划、建议、解释**，不能绕过 Pipeline Executor 直接调用工具或执行节点。执行必须通过 `pipeline_executor.py` → `node_registry.py` → 具体 runner。

### 5.7 不允许引入开放式 LLM 自主循环

保持 Plan-then-Execute 模式。不要引入 "LLM 在循环中自主决定下一步" 的控制流。

---

## 6. 每次任务的标准工作流程

```
1. 阅读相关文件（read_file / search_content / explore）
2. 制定计划（口头说明 或 submit_plan）
3. 用户确认
4. 实现（write_file / edit_file / multi_edit）
5. 运行测试（pytest）
6. 报告结果（改动文件列表 + 测试结果 + 风险）
```

---

## 7. PR / diff / 提交要求

1. **每个 PR 必须包含变更摘要**：说明改了什么、为什么改、影响范围
2. **diff 必须可审查**：避免单次超过 500 行的 PR；大任务拆分为多个小 PR
3. **测试必须通过**：`pytest` 全量通过后才提交
4. **新功能必须包含**：代码 + 测试 + 文档说明（至少更新相关 doc）
5. **不允许提交包含 API key、密码、私密路径的代码**

---

## 8. 如何添加新功能

按照 `docs/developer_guide.md` 的 7 步流程：

1. 在 `src/backend/app/tools/` 中创建处理/QC 模块
2. 在 `src/backend/app/runtime/node_registry.py` 中注册节点
3. 在 `examples/` 中创建 pipeline YAML
4. 在 `src/backend/app/tools/` 中创建 CLI runner
5. 在 `src/backend/app/api/routes.py` 和 `models.py` 中添加 API 端点和模型
6. 在 `src/frontend/src/components/` 中添加前端面板
7. 在 `tests/unit/` 中添加单元测试

---

## 9. 目录速查

| 目录 | 用途 |
|---|---|
| `src/backend/app/runtime/` | Pipeline executor、node registry、scheduler、state store、hooks、error diagnosis、retry |
| `src/backend/app/tools/` | 所有处理模块、QC、CLI runner、contract writer、SPM/MATLAB wrapper |
| `src/backend/app/api/` | FastAPI routes（`routes.py`）和 Pydantic models（`models.py`） |
| `src/backend/app/schemas/` | Pipeline YAML schema 验证（`pipeline_schema.py`） |
| `src/backend/app/preprocessing/` | rs-fMRI 步骤注册表和 plan builder |
| `src/backend/app/advisor/` | LLM advisor 模块（参数、协议、QC、错误、文档问答） |
| `src/frontend/src/components/` | React 面板，每个 pipeline stage 对应一个面板 |
| `examples/` | Pipeline YAML 文件（30+）和 project config YAML |
| `specs/` | 功能规格说明 markdown 文件（50+） |
| `docs/` | 架构文档、开发者指南、用户指南、roadmap |
| `tests/` | 单元测试、集成测试、API 测试、benchmark |
| `matlab/` | MATLAB SPM wrapper 脚本 |
| `deploy/` | Dockerfile 和 docker-compose |

---

## 10. 关键约定

- **Subject-level 节点**接受 `subject_record` 和 `subject_id` 参数；**Project-level 节点**不需要。
- 每个处理步骤都有配套的 QC 模块。
- 所有衍生输出写入 `outputs/derivatives/`——**绝不修改 data/（rawdata）**。
- 导入风格统一使用 `from __future__ import annotations`。
- Pipeline YAML 中每个节点包含：`id`、`backend`、`depends_on`、`inputs`、`outputs`、`params`、`parallel_level`、`gpu_supported`。

---

*最后更新：2025-07-18*
