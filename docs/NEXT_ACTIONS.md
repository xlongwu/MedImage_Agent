# 下一步行动 (NEXT_ACTIONS)

> 最后更新：2026-05-29

## M1 已完全闭环 ✅

- 13 个文档交付物
- ProjectSettings 三入口闭环（PLAN / EXECUTE / API）
- GitHub Actions CI 全绿（backend + frontend）
- 启动命令 / 端口统一
- release_readiness: 78 PASS, 0 FAIL

## M2：Tool Catalog MVP（当前里程碑）

### M2-T001a：Tool Catalog read-only MVP

设计 `tool_registry.py` 完整 schema，为所有处理工具（30+）定义权限等级。

**步骤**：
1. 列出所有处理工具（从 `node_registry.py` 提取）
2. 为每个工具定义 `read_only` / `writes_files` / `destructive` / `requires_confirmation` / `parallel_safe`
3. 创建 `specs/tool_catalog_spec.md`
4. 更新 `docs/ARCHITECTURE.md`

### M2-T002：Plan Validator 准备

前置条件：M2-T001a 完成。

### audit_logger

non-blocking / planned for M2。
