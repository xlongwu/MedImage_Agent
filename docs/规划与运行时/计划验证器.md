# Plan Validator

## 目的

Plan Validator 是 LLM Planner 和 Pipeline Executor 之间的静态安全校验层。

流程：

```text
User Goal / LLM Planner
→ Candidate Pipeline Plan
→ Plan Validator
→ Human Approval Gate
→ Pipeline Executor
```

Plan Validator 只做**静态校验**，不执行任何工具。

## 校验规则

| 规则 | 类型 | 说明 |
|------|:---:|------|
| INVALID_PLAN_TYPE | error | plan 不是 dict |
| MISSING_PIPELINE_ID | error | 缺少 pipeline_id |
| MISSING_OR_EMPTY_NODES | error | nodes 缺失或为空 |
| INVALID_NODE_TYPE | error | node 不是 dict |
| MISSING_NODE_ID | error | node 缺少 id |
| DUPLICATE_NODE_ID | error | 重复 node id |
| UNKNOWN_NODE_ID | error | node id 不在 Tool Catalog 中 |
| UNKNOWN_DEPENDENCY | error | depends_on 指向不存在的 node |
| SELF_DEPENDENCY | error | node 依赖自己 |
| DEPENDENCY_CYCLE | error | DAG 中有环 |
| APPROVAL_REQUIRED | warning | requires_approval 但 params 中无 approved |
| BACKEND_MISMATCH | warning | plan 中 backend 与 Catalog 不一致 |
| UNCATALOGED_METADATA | warning | node 使用 fallback metadata |

## 与 Tool Catalog 的关系

Plan Validator 通过 `build_tool_catalog()` 获取所有合法 node id 和元数据，校验 plan 中的每个 node 是否合法。

## 当前限制

- 不执行参数合法性校验（数值范围、类型）
- 不执行路径安全校验
- 不执行 backend 可用性校验
- 不强制 `approved: true`
- 不替代 Pipeline Schema 的 YAML 结构校验
- 不替代 Approval Gate

## 代码位置

- `src/backend/app/planner/plan_validator.py` — 核心实现
- `tests/unit/test_plan_validator.py` — 24 个测试
