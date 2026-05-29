# 下一步行动 (NEXT_ACTIONS)

> 最后更新：2026-05-29

## 立即执行（P0）

（T-0003、T-0004、T-0005a、T-0005b 已完成；T-0005 为下一优先任务）

### T-0005：audit_logger 决策

```bash
# 后端
uvicorn src.backend.app.main:app --host 127.0.0.1 --port 8000
# 验证
curl http://127.0.0.1:8000/health

# 前端
cd src/frontend && npm run dev
# 验证
curl http://127.0.0.1:5173
```

## 短期执行（P1）

### T-0005：audit_logger 决策

**建议**：先选择方案 B（从文档中移除不存在的引用，标记为 planned），再在 M2 中实现。

**步骤**：
1. 搜索所有引用 `audit_logger` 的文档
2. 替换为 "planned for M2" 说明
3. 在 TASK_BACKLOG.md 中更新 T-0005 状态

### T-0010：设计 Tool Catalog schema

**前置条件**：T-0003 完成。

**步骤**：
1. 列出所有处理工具（30+）
2. 为每个工具定义权限等级
3. 创建 specs/tool_catalog_spec.md
4. 更新 docs/ARCHITECTURE.md

## 持续执行

### T-0050：更新 ROADMAP.md 状态

每个任务完成后更新 ROADMAP.md 和 TASK_BACKLOG.md。

### T-0051：记录新架构决策

重要架构决策记录到 docs/DECISIONS/，编号递增。
