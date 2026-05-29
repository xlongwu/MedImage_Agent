# Execution Integration Design

本文档描述从 reviewed plan 到 pipeline execution 的安全集成路径。

**状态**: 设计阶段 (M5-T004)，尚未实现。

## 一、当前状态

### 已具备

| 能力 | 状态 |
|------|:---:|
| Tool Catalog | ✅ |
| Plan Validator | ✅ |
| LLM Planner (mock/rule-based) | ✅ |
| Frontend Plan Review Console | ✅ |
| Approval Gate schema + API | ✅ |
| Approval Gate frontend preview | ✅ |
| frontend build + CI | ✅ |

### 尚未实现

| 能力 | 说明 |
|------|------|
| execution endpoint | 尚无受控执行 API |
| persistent approval record | approval 未持久化 |
| controlled execution button | 前端无执行入口 |
| audit log | 无执行审计记录 |
| GUI Agent integration | manual_required 节点暂阻断 |

## 二、未来执行链路

```text
Plan Review Console
  → Edit candidate plan
  → Re-validate
  → Fill approval form
  → Approval Gate Check
  → Export review draft
  → Execute Reviewed Plan (future)
    → POST /api/plans/execute-reviewed
    → Backend re-validates plan
    → Backend re-checks approval gate
    → Maps plan to execution contract
    → Pipeline Executor
```

## 三、未来 Endpoint 设计

### `POST /api/plans/execute-reviewed`

请求：

```json
{
  "plan": {
    "pipeline_id": "planned_motion_qc",
    "nodes": [...]
  },
  "validation": { ... },
  "approval": {
    "approved": true,
    "approved_by": "user",
    "approved_nodes": ["spm_realign_subject"],
    "rejected_nodes": []
  },
  "project_config_path": "examples/project_config_dataset.yaml",
  "dry_run": true
}
```

响应（dry_run=true）：

```json
{
  "ok": true,
  "status": "DRY_RUN_OK",
  "execution_allowed": true,
  "validation": { ... },
  "approval_gate": { ... },
  "mapped_pipeline_info": {
    "nodes_total": 4,
    "approval_required_count": 1,
    "high_risk_count": 1
  },
  "run_id": null,
  "blocked_reasons": []
}
```

响应（execution_allowed=false）：

```json
{
  "ok": false,
  "status": "EXECUTION_BLOCKED",
  "execution_allowed": false,
  "validation": { ... },
  "approval_gate": {
    "ok": false,
    "execution_allowed": false,
    "errors": [...]
  },
  "blocked_reasons": ["APPROVAL_NODE_MISSING: spm_realign_subject"]
}
```

## 四、后端必须二次校验

**前端提交的 validation 和 approval 结果不可信任。** 后端执行入口必须独立重做：

```python
validation = validate_plan(plan)
gate_result = check_approval_gate(plan, validation.to_dict(), approval)
if not gate_result.execution_allowed:
    return {"status": "EXECUTION_BLOCKED", ...}
```

## 五、dry_run 优先级

第一版执行集成必须只支持 `dry_run=true`：

- 不调用 Pipeline Executor
- 只返回 validation + approval gate + 是否可执行
- 前端可据此展示 "Ready for execution" 或 "Blocked"

真实的 `dry_run=false` 执行放到后续，且必须经过额外的人机交互确认。

## 六、前端执行按钮策略

未来前端执行按钮必须满足：

| 规则 | 说明 |
|------|------|
| 默认隐藏/disabled | 无 reviewed plan 时不可点击 |
| 只在验证通过时可用 | `validation.ok=true` + `execution_allowed=true` |
| 危险动作文案 | "Execute Reviewed Plan"（明确告知风险） |
| 二次确认 | 点击后弹出确认对话框 |
| 风险提示 | SPM/DPABI 节点列出；manual_required 节点阻断 |

## 七、manual_required 节点策略

- MVP：`manual_required_nodes` 非空 → `execution_allowed=false`
- 未来 GUI Agent 接入后，manual_required 节点进入 GUI path
- 不跳过、不静默执行

## 八、rawdata readonly

- `data/` 永远只读
- 所有输出写入 `outputs/derivatives/`, `outputs/work/`, `outputs/reports/`, `outputs/exports/`
- 执行入口必须遵守 `ProjectSettings.safety.rawdata_readonly`
- SPM/DPABI 节点只能在 writable sandbox 中执行

## 九、audit log 策略

未来需要记录：

- who approved (approved_by)
- when approved (approved_at)
- plan hash (sha256)
- validation hash
- approval record snapshot
- execution request
- run_id
- status (DRY_RUN / SUBMITTED / COMPLETED / FAILED)

当前 audit_logger 尚未实现（planned for M2/M5）。

## 十、分阶段路线

```text
M5-T004: Execution integration design doc ← 本任务
M5-T005: execute-reviewed dry-run API
M5-T006: frontend displays dry-run execution readiness
M5-T007: persistent approval/audit record
M5-T008: gated execution API (dry_run=false)
M5-T009: disabled-by-default frontend execution button
```

## 十一、安全审计

详见 [`docs/GATED_EXECUTION_SAFETY_REVIEW.md`](GATED_EXECUTION_SAFETY_REVIEW.md)（M5-T011）。

Safe execution 设计详见 [`docs/SAFE_REVIEWED_EXECUTION_DESIGN.md`](SAFE_REVIEWED_EXECUTION_DESIGN.md)（M5-T012c）。

## 十二、安全原则

1. 前端不能绕过 approval gate
2. 后端必须独立重做 validation + approval check
3. `execution_allowed=false` 绝不调用 executor
4. rawdata 永远只读
5. SPM/DPABI 需要显式 approval
6. GUI/manual 节点暂阻断
7. LLM 不能直接执行工具
