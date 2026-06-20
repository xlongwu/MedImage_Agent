# ADR-001: Agent Runtime 边界 — LLM 不直接执行工具

## Status
Accepted (2025-07-18)

## 上下文

MedImage Agent 需要引入 LLM 的智能规划能力，但医疗影像处理场景对安全性和可复现性有严格要求。我们需要决定 LLM 在系统中的角色边界。

两种可选方案：

1. **开放式 LLM Agent**：LLM 在循环中自主决定调用哪些工具，类似 Claude Code 的 agentic loop
2. **Plan-then-Execute**：LLM 只生成结构化 plan，确定性引擎执行

## 决策

我们选择 **Plan-then-Execute** 模式，LLM 只做规划和建议。

具体决策：

1. **LLM 不直接执行工具**。LLM 输出的是 pipeline plan（结构化 YAML），不是工具调用序列。
2. **LLM 输出 plan**。plan 格式遵循 `pipeline_schema.py` 定义的 schema，包含节点列表、依赖关系、参数。
3. **Plan Validator 和 Human Approval Gate 决定能否执行**。LLM 生成的 plan 必须经过两层校验：
   - Plan Validator：检查 schema 合法性、安全边界、参数合法性、backend 可用性
   - Human Approval Gate：研究者审批 plan（plan 级）和危险操作（step 级）
4. **Pipeline Executor 是唯一执行入口**。所有真实执行（文件读写、MATLAB/SPM 调用、数据处理）必须经过 `pipeline_executor.py` → `node_registry.py` → 具体 runner。

## 后果

### 正面

- **安全性**：LLM 不可能意外删除文件或修改 rawdata，因为 LLM 不直接控制执行
- **可复现性**：同一个 plan YAML 在任何环境执行结果一致（确定性 DAG 引擎）
- **可审计性**：每个操作由 Pipeline Executor 记录，有完整的执行轨迹
- **可控性**：研究者可以通过修改 plan YAML 来调整流程，不需要重新和 LLM 对话

### 负面

- **灵活性降低**：LLM 不能在执行中途根据中间结果动态调整 plan（需要重新生成 plan）
- **开发成本**：需要维护 Plan Validator、Pipeline Schema、Node Registry 等基础设施
- **用户体验**：用户不能像使用 ChatGPT 一样自由对话式地操作

### 风险缓解

- 对于需要中途调整的场景，可以通过 "partial re-plan" 机制：Pipeline Executor 在某个节点失败后，LLM 根据错误信息生成修复 plan
- 对于简单的一次性操作，保留 CLI 工具直接调用（但 CLI 也需要 `--approve`）

## 相关文档

- `AGENTS.md` — 禁止事项 #6、#7
- `docs/SAFETY_BOUNDARIES.md` — LLM advice-only
- `docs/ARCHITECTURE.md` — Agent Runtime 和 LLM Planner 部分

---

*创建于：2025-07-18*
