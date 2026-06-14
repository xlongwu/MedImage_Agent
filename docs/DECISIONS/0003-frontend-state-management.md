# ADR-003: 前端状态管理策略

## Status
Proposed (2026-06-14)

## Context
当前前端（75+ 组件）使用 React 本地 state + props 传递状态。随着功能增加：
- `App.tsx` 承载过多状态逻辑
- 多个面板需要共享项目上下文、运行状态、配置信息
- 跨组件通信依赖 props drilling，深层嵌套难以维护
- 缺少统一的 loading/error/empty 状态管理模式

三选一：

1. **保持现状 + 组件重构** — 提取 hooks + React Context，不引入新依赖
2. **Zustand** — 轻量客户端状态管理库
3. **TanStack Query (React Query)** — 专注服务端状态管理

## Decision
**分阶段采用：Phase 1 用 Option 1（立即），Phase 2 引入 TanStack Query（v0.7+），暂不采用 Zustand。**

理由：
1. 当前最高优先级是不破坏功能的前提下改善代码结构，Option 1 风险最低
2. 大部分痛点来自服务端状态管理（API 调用、缓存、刷新），React Query 是最佳匹配
3. Zustand 解决客户端状态管理，当前客户端状态复杂度尚未达到需要额外库的程度

## Consequences

### 正面
- `App.tsx` 大幅精简，每个 feature 独立可测试
- React Query 自动处理缓存失效、后台刷新、乐观更新
- 前端性能提升（减少不必要的 API 重复请求）

### 负面
- 新增 React Query 依赖（约 12KB gzipped）
- 需要团队学习 React Query 模式
- 迁移过程中需保持向后兼容

## 相关文档
- `docs/architecture.md` — 当前前端架构
- `PROJECT_STATE.md` — 下一阶段任务

---
*创建于：2026-06-14*
