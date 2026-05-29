# Approval Gate

## 目的

Approval Gate 位于 Plan Validator 和 Pipeline Executor 之间，确保只有通过校验且经过审批的 plan 才能执行。

## 数据流

```text
Plan + Validation + Approval Record
→ check_approval_gate()
→ ApprovalGateResult { execution_allowed, errors, warnings }
```

## ApprovalRecord

| 字段 | 说明 |
|------|------|
| `approved` | 是否已审批 |
| `approved_by` | 审批人 |
| `approved_nodes` | 批准的节点列表（`["*"]` = 全量） |
| `rejected_nodes` | 拒绝的节点列表 |
| `review_draft_schema_version` | 关联的 review draft 版本 |

## 校验规则

| 规则 | 类型 | 说明 |
|------|:---:|------|
| VALIDATION_MISSING | error | validation 缺失 |
| VALIDATION_NOT_OK | error | validation 未通过 |
| APPROVAL_MISSING | error | 需要审批但无审批记录 |
| APPROVAL_NOT_GRANTED | error | approved != true |
| APPROVAL_NODE_MISSING | error | 审批未覆盖 required nodes |
| APPROVAL_REJECTED_NODE | error | 存在被拒绝的节点 |
| MANUAL_REQUIRED_NODE | error | GUI/人工节点暂不支持 |
| HIGH_RISK_APPROVED | warning | 高风险节点已审批 |

## 代码位置

- `src/backend/app/planner/approval_gate.py`
- `tests/unit/test_approval_gate.py` — 17 个测试
