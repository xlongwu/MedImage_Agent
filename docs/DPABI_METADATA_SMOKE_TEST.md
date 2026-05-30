# DPABI Metadata Reviewed Execution Smoke Test

> M7-DPABI-T003 | 15 DPABI metadata nodes manual smoke

**状态**: Manual smoke — NO MATLAB/SPM/DPABI required. Python-only.

---

## 一、前置条件

| 条件 | 说明 |
|------|------|
| Backend | `uvicorn src.backend.app.main:app --host 127.0.0.1 --port 8000` |
| Env var | `export MEDIMAGE_ENABLE_REVIEWED_EXECUTION=1` |
| MATLAB | NOT required |
| SPM | NOT required |
| DPABI | NOT required |

---

## 二、representative smoke plan (5 nodes)

```json
{
  "pipeline_id": "dpabi_metadata_smoke",
  "nodes": [
    {"id": "dpabi_capability_inspection", "backend": "python", "depends_on": [], "params": {}},
    {"id": "dpabi_wrapper_contracts", "backend": "python", "depends_on": ["dpabi_capability_inspection"], "params": {}},
    {"id": "dpabi_run_plan", "backend": "python", "depends_on": ["dpabi_wrapper_contracts"], "params": {}},
    {"id": "dpabi_template_library", "backend": "python", "depends_on": ["dpabi_run_plan"], "params": {}},
    {"id": "dpabi_template_execute", "backend": "python", "depends_on": ["dpabi_template_library"], "params": {"metadata_only": true}}
  ]
}
```

> `dpabi_template_execute` is metadata-only template execution — NOT external DPABI execution.

---

## 三、Approval

```json
{
  "approved": true, "approved_by": "smoke-tester",
  "approved_nodes": ["dpabi_capability_inspection","dpabi_wrapper_contracts",
    "dpabi_run_plan","dpabi_template_library","dpabi_template_execute"],
  "approved_backends": [], "rejected_nodes": []
}
```

> `approved_backends` is empty — these are Python-only metadata nodes.

---

## 四、API call

```bash
curl -s -X POST http://127.0.0.1:8000/api/plans/execute-reviewed \
  -H "Content-Type: application/json" \
  -d '{"plan": {...}, "approval": {...},
       "project_config_path": "examples/project_config.yaml",
       "dry_run": false, "confirm_execution": true,
       "persist_audit": true, "write_pipeline_yaml": true,
       "actor": "dpabi-metadata-smoke"}' | python -m json.tool
```

---

## 五、Expected success

```json
{"ok": true, "status": "EXECUTION_SUBMITTED",
 "execution": {"executor_called": true, "submitted": true},
 "pipeline_yaml": {"written": true}, "audit": {"persisted": true}}
```

Runner results are metadata-only: no MATLAB, no DPABI, no subprocess.

---

## 六、Blocked execution verification

Plan with blocked DPABI execution nodes:

```json
{"pipeline_id": "should_be_blocked",
 "nodes": [{"id": "dpabi_subject_smooth", "depends_on": [], "params": {}}]}
```

Expected: `EXECUTION_POLICY_BLOCKED` or `SAFE_EXECUTION_POLICY_BLOCKED`, `executor_called=false`.

---

## 七、Failure diagnostics

| Status | Cause | MATLAB/DPABI called? |
|--------|-------|:---:|
| `REVIEWED_EXECUTION_DISABLED` | env var not set | ❌ |
| `CONFIRMATION_REQUIRED` | confirm_execution not true | ❌ |
| `VALIDATION_FAILED` | unknown node | ❌ |
| `APPROVAL_GATE_BLOCKED` | wildcard/missing approval | ❌ |
| `EXECUTION_POLICY_BLOCKED` | blocked execution node | ❌ |
| `SAFE_EXECUTION_POLICY_BLOCKED` | GPU/contract unsafe | ❌ |
| `EXECUTION_FAILED` | runner error | ❌ |

---

## 八、Side-effect checks

```bash
git diff -- data/          # must be empty
find outputs/derivatives/  # should be empty (metadata-only)
ls outputs/reports/audit_records/   # may have JSON
ls outputs/work/reviewed_pipelines/ # may have YAML
```

---

## 九、Cleanup

```bash
rm -rf outputs/work/reviewed_pipelines/*
rm -rf outputs/reports/audit_records/*
unset MEDIMAGE_ENABLE_REVIEWED_EXECUTION
```

---

## 十、Safety boundary

```
✅ 15 DPABI metadata nodes — Python-only
✅ no MATLAB / DPABI / subprocess
✅ no rawdata / derivatives writes
✅ metadata-only results
❌ DPABI execution nodes blocked
❌ MATLAB/DPABI not called
```
