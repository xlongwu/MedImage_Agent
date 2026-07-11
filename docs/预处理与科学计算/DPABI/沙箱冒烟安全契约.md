# DPABI Sandbox Smoke Run — Safety Contract

> M7-DPABI-T004a | dpabi_sandbox_smoke_run 执行前安全契约

**状态**: 审计 & 设计阶段。**dpabi_sandbox_smoke_run 未开放 reviewed execution。**
**代码位置**: `src/backend/app/tools/dpabi_sandbox_runner.py`

---

## 一、Runner Contract

```python
def run_dpabi_sandbox_smoke(
    matlab_command: str,      # from project_config
    dpabi_dir: str,           # from project_config
    work_dir: str,            # from project_config
    log_dir: str,             # from project_config
    approved: bool,           # from approval gate
    approved_by: str = "local-user",
    matlab_script_dir: str = "./matlab",
) -> dict:
```

### Key characteristics

| Characteristic | Value |
|---------------|-------|
| Backend | `matlab-dpabi` |
| Calls MATLAB | ✅ |
| Calls DPABI | ✅ (via MATLAB wrapper) |
| Uses SPM | ❌ |
| `subprocess.run(list)` | ✅ |
| `_matlab_quote()` | ✅ |
| `validate_*_runtime_config()` | ❌ |

---

## 二、MATLAB / DPABI Runtime Contract

### Command construction

```python
dpabi_abs = str(Path(dpabi_dir).resolve())
matlab_code = (
    "try, "
    f"addpath('{_matlab_quote(...)}'); "
    f"dpabi_sandbox_smoke_run('{_matlab_quote(dpabi_abs)}', "
    f"'{_matlab_quote(str(output_dir.resolve()))}', "
    f"'{_matlab_quote(str(result_json.resolve()))}'); "
    "catch ME, disp(getReport(ME)); exit(1); end; exit(0);"
)
cmd = [matlab_command, "-nodisplay", "-nosplash", "-batch", matlab_code]
subprocess.run(cmd, ...)
```

### Safety gaps

| Gap | Severity |
|-----|:---:|
| No `validate_matlab_runtime_config()` | high |
| No `validate_dpabi_runtime_config()` | high |
| No `validate_third_party_dir(dpabi_dir)` | high |

### Needed hardening

- `validate_matlab_command(matlab_command)`
- `validate_third_party_dir(dpabi_dir, name="dpabi_dir")`
- `validate_third_party_dir` for matlab_script_dir

---

## 三、Input Sandbox Contract

| Input | Source | Constraint |
|-------|--------|-----------|
| `matlab_command` | project_config | must pass `validate_matlab_command()` |
| `dpabi_dir` | project_config | must pass `validate_third_party_dir()` |
| `work_dir` | project_config | sandbox work dir |
| No BIDS data | — | smoke uses synthetic MATLAB-generated data |

### Sandbox rules

- ✅ smoke is self-contained (no external data)
- ✅ no rawdata read
- ✅ no derivatives read
- ⚠️ no DPABI path validation yet

---

## 四、Output Contract

| Output | Location |
|--------|----------|
| `dpabi_sandbox_smoke_result.json` | `work/dpabi/sandbox/` |
| `dpabi_sandbox_smoke_stdout.log` | `logs/` |
| `dpabi_sandbox_smoke_stderr.log` | `logs/` |
| `dpabi_sandbox_smoke_approval.json` | `work/dpabi/` |
| `dpabi_sandbox_execution_audit.json` | `outputs/reports/` |

### Path Safety

| Risk | Status |
|------|:---:|
| rawdata write | ✅ safe (sandbox work dir) |
| derivatives write | ✅ safe |
| reports write | ✅ safe |

---

## 五、Approval Contract

| Condition | Required |
|-----------|:---:|
| `approved_nodes` includes `dpabi_sandbox_smoke_run` | ✅ |
| `approved_backends` includes `matlab-dpabi` | ✅ |
| wildcard `["*"]` | ❌ blocked |

---

## 六、Current Policy Status

| Layer | Status |
|-------|:---:|
| NODE_REGISTRY | ❌ NOT registered |
| plan_adapter | ❌ blocked (`blocked_dpabi_execution_nodes`) |
| execute_reviewed | ❌ blocked by safe allowlist |

---

## 七、Rollout Plan

| Phase | Task |
|-------|------|
| T004a | Safety contract ✅ |
| T004b | Register runner + DPABI runtime preflight |
| T004c | Sandbox smoke contract tests |
| T004d | Reviewed execution allowlist |

### T004b hardening needs

- Register `run_dpabi_sandbox_smoke_node` in NODE_REGISTRY
- Add `validate_dpabi_runtime_config()` or reuse `validate_matlab_runtime_config()`
- Safety preflight before MATLAB subprocess call

---

## 八、Forbidden Cases

| Case | Handling |
|------|---------|
| No approval | runner returns error |
| Unsafe matlab_command | preflight blocks |
| dpabi_dir → rawdata | preflight blocks |
| dpabi_dir → derivatives | preflight blocks |
| Path traversal | preflight blocks |
