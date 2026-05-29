# Audit Record

## 目的

Audit Record 为 plan review / approval / dry-run 事件创建不可变的、可哈希验证的快照。未来所有真实执行都必须关联到一个可追踪的 audit record。

## ReviewAuditRecord

| 字段 | 说明 |
|------|------|
| `audit_id` | UUID 唯一标识 |
| `created_at` | ISO 时间戳 |
| `event_type` | `approval_checked` / `dry_run_checked` / `execution_blocked` 等 |
| `plan_hash` | plan 的 SHA256 哈希（sort_keys 稳定） |
| `validation_hash` | validation 的 SHA256 哈希 |
| `approval_hash` | approval 的 SHA256 哈希（无 approval 时为 None） |
| `safety` | `review_only=true`, `executes_pipeline=false`, `rawdata_readonly=true` |

## 写入策略

- 原子写入（`.tmp` + `replace`）
- 不覆盖已有记录（冲突时追加 suffix）
- 不写入 rawdata

## 代码位置

- `src/backend/app/planner/audit_record.py`
- `tests/unit/test_audit_record.py` — 15 个测试
