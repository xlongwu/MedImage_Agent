# 开发路线图 (ROADMAP)

## 总览

| 里程碑 | 目标 | 预计状态 | 依赖 |
|--------|------|---------|------|
| M1 | 稳定当前基础设施 | 当前进行中 | — |
| M2 | 拆分 Node Registry，建立 Tool Catalog | 计划中 | M1 |
| M3 | 实现 Plan Validator | 计划中 | M2 |
| M4 | 实现 LLM Planner MVP | 计划中 | M3 |
| M5 | 接入 GUI Manual Node | 计划中 | M4 |
| M6 | 前端 Plan Review Console | 计划中 | M5 |
| M7 | 真实数据安全沙箱和报告闭环 | 计划中 | M6 |

---

## M1：稳定当前基础设施

**目标**：确保现有代码库可以被 Code Agent 安全、可控地迭代。

### 交付物

1. ✅ AGENTS.md（Code Agent 开发指南）
2. ✅ CLAUDE.md（Claude Code 专属指南，含工作流规则）
3. ✅ docs/PROJECT_GOAL.md（项目长期目标）
4. ✅ docs/ARCHITECTURE.md（完整架构文档）
5. ✅ docs/ROADMAP.md（本文档）
6. ✅ docs/TASK_BACKLOG.md（可执行任务池）
7. ✅ docs/SAFETY_BOUNDARIES.md（安全边界文档）
8. ✅ docs/DEVELOPMENT_WORKFLOW.md（开发工作流文档）
9. ✅ docs/DECISIONS/0001-agent-runtime-boundary.md（ADR-001）
10. ✅ docs/DECISIONS/0002-rawdata-readonly.md（ADR-002）
11. 🔄 修正 README.md 和现有文档中的路径不一致
12. 🔄 确认所有测试通过，修复失败的测试

### 验收标准

- 所有文档中的路径与实际文件结构一致
- `pytest` 全量通过
- 后端和前端能正常启动
- Agent 可根据 AGENTS.md 和 CLAUDE.md 安全地修改代码

---

## M2：拆分 Node Registry，建立 Tool Catalog

**目标**：从单体 `node_registry.py` 和隐式工具权限转变为清晰的 Tool Catalog + Node Registry 双层结构。

### 背景

当前 `node_registry.py` 有 42 个节点，全部在一个文件中注册，`tool_registry.py` 只有 2 个工具定义（`pipeline.plan`、`pipeline.execute`）。实际执行时，每个 node runner 内部的权限检查不统一。需要：

1. 将每个处理工具显式注册到 `tool_registry.py`，声明权限等级
2. `node_registry.py` 只做 node→runner 映射
3. `pipeline_executor.py` 在调用 runner 前检查 `tool_registry` 权限

### 交付物

- `tool_registry.py` 包含所有工具（30+）的权限定义
- 每个工具声明 `read_only`、`writes_files`、`destructive`、`requires_confirmation`、`parallel_safe`
- `pipeline_executor.py` 在 `get_node_runner` 前调用 `assert_tool_allowed`
- 所有节点无需修改 runner 内部逻辑（权限检查集中在 executor 层）
- 更新 `docs/ARCHITECTURE.md` 的 Tool Catalog 部分
- 单元测试覆盖所有工具权限检查

### 验收标准

- 所有工具在 `tool_registry.py` 中注册
- 未授权的工具调用被安全拒绝
- 已有 pipeline 执行行为不变
- `pytest` 全量通过

---

## M3：实现 Plan Validator

**目标**：在 pipeline 执行前对 plan 进行完整的安全和合法性校验。

### 背景

当前 `pipeline_schema.py` 只做基础 schema 校验（字段存在性、节点 ID 唯一性、依赖引用完整性）。缺少：

- 安全边界校验（是否尝试写入 rawdata）
- 参数合法性校验（数值范围、类型）
- Backend 可用性校验（MATLAB 是否已安装、GPU 是否可用）
- 输入文件存在性校验
- 跨节点输出/输入匹配校验

### 交付物

- `src/backend/app/schemas/plan_validator.py`（新增）
- 集成到 `agent_runtime.py` 的 `run_orchestrator_execute` 流程中（在 `run_pipeline` 前调用）
- 校验失败返回结构化错误列表（非异常抛出，便于前端展示）
- 单元测试覆盖所有校验规则
- 更新 `docs/ARCHITECTURE.md`

### 验收标准

- 不合法的 plan 在 Approval Gate 前就被拦截
- 校验错误信息清晰，包含具体节点、字段、原因
- 已有合法 pipeline 执行行为不变
- `pytest tests/unit/test_pipeline_schema.py` 扩展覆盖

---

## M4：实现 LLM Planner MVP

**目标**：用户用自然语言描述分析目标，LLM 自动生成结构化 pipeline plan。

### 背景

当前 Advisor 模块（`src/backend/app/advisor/`）已实现各类建议功能，但没有统一的 "自然语言 → pipeline YAML" 能力。需要：

1. LLM 理解用户目标（如"对 sub-001 到 sub-010 做完整的 rs-fMRI 预处理和 ALFF 分析"）
2. 从 tool catalog 中选择合适的节点
3. 生成完整的 pipeline YAML
4. 生成的 plan 经过 Plan Validator 校验
5. 用户确认后执行

### 交付物

- `src/backend/app/advisor/planner_llm.py`（新增）
- LLM prompt 模板和 tool catalog 注入机制
- 生成的 pipeline YAML 写入 `outputs/work/agent_runs/<id>/plan.yaml`
- 前端 Planner 面板展示生成的 plan（已有 `RsfmriPreprocessingPlanPanel.tsx`）
- API 端点：`POST /api/planner/generate-plan`
- 集成测试覆盖 3 种典型场景

### 验收标准

- 自然语言输入 → 结构化 pipeline YAML
- 生成的 YAML 通过 Plan Validator
- LLM 不能直接执行（必须经过 Approval Gate）
- 常见场景（全流程预处理、单项分析、参数对比）生成正确

---

## M5：接入 GUI Manual Node

**目标**：实现真正可用的 GUI Agent Node，支持人工定位和交互确认。

### 背景

当前 GUI Agent 路由（`gui_agent_routes.py`）已实现基础会话管理，但只有 mock provider。需要：

1. 真实的 GUI 沙箱环境（浏览器内嵌或独立窗口）
2. 图像展示（NIfTI 渲染）
3. 人工标注工具（点选、画框）
4. 标注结果写回 pipeline state

### 交付物

- GUI Agent Provider（真实实现，替换 mock）
- NIfTI 图像渲染组件（前端）
- 标注工具（AC-PC 定位、ROI 画框）
- 与 Pipeline Executor 的集成（暂停/继续机制）
- 安全约束：GUI Agent 不能访问 rawdata 以外的文件
- 单元测试 + 集成测试

### 验收标准

- Pipeline 执行到 GUI Agent Node 后暂停
- 人工在 GUI 中完成标注
- 标注结果正确写回 pipeline state
- Pipeline 继续执行后续节点
- 不会因为超时或网络问题丢失标注数据

---

## M6：前端 Plan Review Console

**目标**：提供完整的可视化 plan 审批界面。

### 背景

当前前端有 Approval Gate UI 的基础设施，但没有独立的 "Plan Review Console"。需要：

1. 展示生成的 pipeline plan（DAG 图）
2. 每个节点的详情（inputs、outputs、params、backend、风险等级）
3. 审批操作（批准 / 拒绝 / 修改参数后批准）
4. 审批历史记录

### 交付物

- `src/frontend/src/components/PlanReviewConsole.tsx`（新增）
- DAG 可视化（基于 ECharts 或自定义 Canvas）
- 节点详情面板
- 审批工作流（批准/拒绝/修改）
- 审批历史查看
- 与 Agent Runtime 的 `/api/agent/plan` 和 `/api/agent/execute` 对接

### 验收标准

- 生成的 plan 以 DAG 图展示
- 每个节点可展开查看详情
- 审批操作正确触发后端
- 拒绝的 plan 不会被意外执行

---

## M7：真实数据安全沙箱和报告闭环

**目标**：在保证安全的前提下支持真实 rs-fMRI 数据处理，并形成完整的报告闭环。

### 背景

当前系统默认使用合成 BIDS 数据，`safety_and_limitations.md` 中提到 "synthetic data only"。M7 的目标是：

1. 建立真实数据的安全沙箱（隔离环境、网络限制）
2. 确保 `rawdata readonly` 在真实数据场景下严格执行
3. 完整的报告生成 → 校验 → 导出 → 归档闭环
4. 真实数据验证和出版物级别的图表输出

### 交付物

- 真实数据安全沙箱配置（Docker / 文件系统权限 / 网络隔离）
- `MEDIMAGE_REAL_DATA_MODE` 环境变量和对应安全策略
- 出版物级别的报告模板（LaTeX 风格图表、统计表格）
- 报告闭环：生成 → 校验 → 导出 → 归档
- 真实数据验证案例（至少 3 个公开数据集）
- 安全审计报告

### 验收标准

- 真实数据在只读沙箱中处理
- 任何写 rawdata 的尝试被安全拒绝
- 报告符合出版物标准
- 完整的可复现性捆绑包（环境、参数、版本、校验和）

---

*最后更新：2025-07-18*
