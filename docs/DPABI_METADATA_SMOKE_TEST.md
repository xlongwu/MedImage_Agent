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

## 二、Representative smoke (5 nodes)

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

## 三、Full 15-node coverage plan

```json
{
  "pipeline_id": "dpabi_metadata_full_coverage",
  "nodes": [
    {"id": "dpabi_capability_inspection",  "backend": "python", "depends_on": [], "params": {}},
    {"id": "dpabi_input_manifest",         "backend": "python", "depends_on": ["dpabi_capability_inspection"], "params": {}},
    {"id": "dpabi_preflight",              "backend": "python", "depends_on": ["dpabi_input_manifest"], "params": {}},
    {"id": "dpabi_run_plan",               "backend": "python", "depends_on": ["dpabi_preflight"], "params": {}},
    {"id": "dpabi_signature_probe",        "backend": "python", "depends_on": ["dpabi_run_plan"], "params": {}},
    {"id": "dpabi_wrapper_contracts",      "backend": "python", "depends_on": ["dpabi_signature_probe"], "params": {}},
    {"id": "dpabi_wrapper_scaffold",       "backend": "python", "depends_on": ["dpabi_wrapper_contracts"], "params": {}},
    {"id": "dpabi_alff_falff_contract",    "backend": "python", "depends_on": ["dpabi_wrapper_scaffold"], "params": {}},
    {"id": "dpabi_nuisance_regression_contract", "backend": "python", "depends_on": ["dpabi_alff_falff_contract"], "params": {}},
    {"id": "dpabi_reho_contract",          "backend": "python", "depends_on": ["dpabi_nuisance_regression_contract"], "params": {}},
    {"id": "dpabi_temporal_filtering_contract",  "backend": "python", "depends_on": ["dpabi_reho_contract"], "params": {}},
    {"id": "dpabi_functional_connectivity_contract","backend":"python","depends_on":["dpabi_temporal_filtering_contract"],"params":{}},
    {"id": "dpabi_template_library",       "backend": "python", "depends_on": ["dpabi_functional_connectivity_contract"], "params": {}},
    {"id": "dpabi_template_instantiate",   "backend": "python", "depends_on": ["dpabi_template_library"], "params": {}},
    {"id": "dpabi_template_execute",       "backend": "python", "depends_on": ["dpabi_template_instantiate"], "params": {"metadata_only": true}}
  ]
}
```

> All 15 nodes are Python-only metadata/contract/capability runners.
> `dpabi_template_execute` remains metadata-only in this phase.

---

## 四、Approval

```json
{
  "approved": true, "approved_by": "smoke-tester",
  "approved_nodes": ["dpabi_capability_inspection","dpabi_input_manifest",
    "dpabi_preflight","dpabi_run_plan","dpabi_signature_probe",
    "dpabi_wrapper_contracts","dpabi_wrapper_scaffold",
    "dpabi_alff_falff_contract","dpabi_nuisance_regression_contract",
    "dpabi_reho_contract","dpabi_temporal_filtering_contract",
    "dpabi_functional_connectivity_contract","dpabi_template_library",
    "dpabi_template_instantiate","dpabi_template_execute"],
  "approved_backends": [], "rejected_nodes": []
}
```

> `approved_backends` is empty — these are Python-only metadata nodes.

---

## 五、API call

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

## 六、Expected success

```json
{"ok": true, "status": "EXECUTION_SUBMITTED",
 "execution": {"executor_called": true, "submitted": true},
 "pipeline_yaml": {"written": true}, "audit": {"persisted": true}}
```

Runner results are metadata-only: no MATLAB, no DPABI, no subprocess.

---

## 七、Blocked DPABI execution verification

All 5 DPABI execution nodes remain blocked:

| Blocked node | Expected status | executor_called |
|-------------|----------------|:---:|
| `dpabi_sandbox_smoke_run` | `EXECUTION_POLICY_BLOCKED` | false |
| `dpabi_single_function_sandbox` | `EXECUTION_POLICY_BLOCKED` | false |
| `dpabi_subject_smooth` | `EXECUTION_POLICY_BLOCKED` | false |
| `dpabi_subject_wrapper_report` | `EXECUTION_POLICY_BLOCKED` | false |
| `dpabi_wrapper_validation_matrix` | `EXECUTION_POLICY_BLOCKED` | false |

Example blocked plan:

```json
{"pipeline_id": "should_be_blocked",
 "nodes": [{"id": "dpabi_subject_smooth", "depends_on": [], "params": {}}]}
```

> Blocked results confirm: DPABI execution is NOT called.

---

## 八、Failure diagnostics (14 statuses)

| Status | Cause | Fix | MATLAB called? |
|--------|-------|-----|:---:|
| `REVIEWED_EXECUTION_DISABLED` | env var not set | `export MEDIMAGE_ENABLE_REVIEWED_EXECUTION=1` | ❌ |
| `CONFIRMATION_REQUIRED` | confirm_execution not true | Set `true` | ❌ |
| `AUDIT_REQUIRED` | persist_audit not true | Set `true` | ❌ |
| `PROJECT_CONFIG_REQUIRED` | missing config path | Provide path | ❌ |
| `PROJECT_CONFIG_INVALID` | bad YAML | Fix YAML | ❌ |
| `VALIDATION_FAILED` | unknown node id | Check node exists in catalog | ❌ |
| `APPROVAL_GATE_BLOCKED` | wildcard/missing approval | Use explicit node list | ❌ |
| `PLAN_ADAPTER_FAILED` | plan structure error | Fix plan | ❌ |
| `EXECUTION_POLICY_BLOCKED` | DPABI execution node | Remove blocked node | ❌ |
| `SAFE_EXECUTION_POLICY_BLOCKED` | GPU/contract unsafe | Use metadata nodes only | ❌ |
| `PIPELINE_YAML_REQUIRED` | write_pipeline_yaml not true | Set `true` | ❌ |
| `PIPELINE_WRITE_FAILED` | writer error | Check permissions | ❌ |
| `AUDIT_WRITE_FAILED` | audit write error | Check permissions | ❌ |
| `EXECUTION_FAILED` | runner error | Check logs | ❌ |

---

## 九、Side-effect checks

```bash
git diff -- data/          # must be empty
git diff -- rawdata/       # must be empty
find outputs/derivatives/  # should be empty (metadata-only)
ls outputs/reports/audit_records/   # may have JSON
ls outputs/work/reviewed_pipelines/ # may have YAML
```

---

## 十、Cleanup

```bash
rm -rf outputs/work/reviewed_pipelines/*
rm -rf outputs/reports/audit_records/*
unset MEDIMAGE_ENABLE_REVIEWED_EXECUTION
```

---

## 十一、Safety boundary

```
✅ 15 DPABI metadata nodes — Python-only
✅ no MATLAB / DPABI / subprocess
✅ no rawdata / derivatives writes
✅ metadata-only results
❌ 5 DPABI execution nodes blocked
❌ MATLAB/DPABI not called
```
