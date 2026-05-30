# DPABI Single Function Sandbox — Safety Contract

> M7-DPABI-T005a | dpabi_single_function_sandbox 执行前安全契约

**状态**: 审计 & 设计阶段。**dpabi_single_function_sandbox NOT in reviewed execution allowlist.**
**代码位置**:
- Runner: `src/backend/app/tools/dpabi_single_function_runner.py`
- Safety: `src/backend/app/tools/dpabi_safety.py`
- Registered: `src/backend/app/runtime/node_registry.py` (line ~487)

---

## 一、Runner Contract

```python
def run_dpabi_single_function_sandbox(
    matlab_command: str,       # from project_config
    dpabi_dir: str,            # from project_config
    work_dir: str,             # from project_config
    log_dir: str,              # from project_config
    function_name: str = "y_Smooth",  # from node params, validated against allowlist
    approved: bool = False,    # from approval gate
    approved_by: str = "local-user",
    matlab_script_dir: str = "./matlab",
) -> dict:
```

### Key characteristics

| Characteristic | Value |
|---------------|-------|
| Backend | `matlab-dpabi` |
| Calls MATLAB | ✅ |
| Calls DPABI | ✅ (single function) |
| `subprocess.run(list)` | ✅ |
| `_matlab_quote()` | ✅ |
| Function allowlist | ✅ (9 functions) |
| Runtime preflight | ❌ |

---

## 二、Function Allowlist Contract

### Allowed (9 functions)

| Function | Category |
|----------|----------|
| `y_Smooth` | smoothing |
| `rest_Smooth` | smoothing |
| `y_Filter` | filtering |
| `rest_Filter` | filtering |
| `y_RegressOutImgCovariates` | nuisance |
| `y_alff_falff` | ALFF/fALFF |
| `y_Reho` | ReHo |
| `y_ROItseries` | ROI extraction |
| `y_FC` | functional connectivity |

### Forbidden

DPARSF_run, DPARSFA_run, DPABI_run, dpabi_gui, any pattern matching DPARSF/DPARSFA.

### Sandbox rule

- ✅ Only allowlisted functions via `dpabi_safety.ALLOWED_FUNCTIONS`
- ❌ No arbitrary function name
- ❌ No MATLAB code fragment
- ❌ No `eval`, `system`, `delete`, etc.

---

## 三、Parameter Schema

| Param | Required | Validation |
|-------|:---:|------|
| `function_name` | yes | must be in ALLOWED_FUNCTIONS |
| Wrapper contracts | yes | must exist at `work/dpabi/dpabi_wrapper_contracts.json` |
| Function contract | yes | via `get_dpabi_single_function_contract()` |

---

## 四、MATLAB/DPABI Runtime

| Check | Status |
|-------|:---:|
| `subprocess.run(list)` | ✅ |
| `_matlab_quote()` | ✅ |
| `validate_matlab_runtime_config()` | ❌ missing |
| `dpabi_dir` validation | ❌ missing |

---

## 五、Input/Output Contract

| Aspect | Current |
|--------|---------|
| Input | No rawdata (uses contract/manifest) |
| Output | `work/dpabi/single_function_sandbox/` |
| Logs | `logs/` |
| Reports | `outputs/reports/dpabi/` |
| Rawdata write | ❌ not allowed |
| Derivatives write | ❌ not allowed |

---

## 六、Current Policy Status

| Layer | Status |
|-------|:---:|
| NODE_REGISTRY | ✅ registered |
| Tool Catalog | ✅ present |
| plan_adapter | ❌ blocked (`blocked_dpabi_execution_nodes`) |
| execute_reviewed | ❌ blocked |

---

## 七、Rollout Plan

| Phase | Task |
|-------|------|
| T005a | Safety contract ✅ |
| T005b | Runtime hardening (add validate_matlab_runtime_config) |
| T005c | Sandbox contract tests |
| T005d | Reviewed execution allowlist |
