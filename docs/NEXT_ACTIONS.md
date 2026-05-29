# 下一步行动 (NEXT_ACTIONS)

> 最后更新：2026-05-29

## M1 已完成 ✅

M1 "稳定当前基础设施" 全部交付物已完成。详见 `docs/CURRENT_STATE.md`。

## M2：Tool Catalog MVP（当前里程碑）

### M2-T001：Tool Catalog schema 设计

设计 `tool_registry.py` 的完整 schema，为所有处理工具（30+）定义权限等级。

**步骤**：
1. 列出所有处理工具（从 node_registry.py 提取）
2. 为每个工具定义 read_only / writes_files / destructive / requires_confirmation / parallel_safe
3. 创建 `specs/tool_catalog_spec.md`
4. 更新 `docs/ARCHITECTURE.md` Tool Catalog 部分

### M2-T002：Plan Validator 准备

在 M2 Tool Catalog 就绪后，设计 Plan Validator 的校验规则和接口。

**前置条件**：M2-T001 完成。

### audit_logger

**状态**：non-blocking / planned for M2
**说明**：当前不阻塞 Tool Catalog MVP。在 M2 中作为辅助任务实现。

## 持续执行

### T-0050：更新 ROADMAP.md 状态

每个里程碑完成后更新 ROADMAP.md 和 TASK_BACKLOG.md。

### T-0051：记录新架构决策

重要架构决策记录到 `docs/DECISIONS/`，编号递增。
