# DPABI Subject Smooth — Safety Contract

> M7-DPABI-T006a | dpabi_subject_smooth 执行前安全契约

**状态**: 审计 & 设计阶段。**dpabi_subject_smooth NOT in reviewed execution allowlist.**
**代码位置**: `src/backend/app/tools/dpabi_subject_wrapper.py`

---

## 一、Runner Contract

```python
def run_dpabi_subject_smooth(
    matlab_command: str,       # from project_config
    dpabi_dir: str,            # from project_config
    subject_id: str,           # from pipeline context
    input_bold: str,           # from node params / discovery
    derivatives_dir: str,      # from project_config
    work_dir: str,             # from project_config
    log_dir: str,              # from project_config
    function_name: str = "y_Smooth",
    fwhm: list[float] | None = None,
    approved: bool = False,
    matlab_script_dir: str = "./matlab",
) -> dict:
```

### Built-in checks

| Check | Status |
|-------|:---:|
| Function allowlist | ✅ `ALLOWLISTED_SINGLE_FUNCTIONS` |
| Synthetic input only | ✅ `examples/synthetic_bids/rawdata` required |
| Contract validation | ✅ `dpabi_wrapper_contracts.json` |
| Runtime preflight | ❌ |
| FWHM validation | ❌ |
| `subprocess.run(list)` | ✅ |

---

## 二、Input Image Contract

- **Source**: `input_bold` parameter
- **Constraint**: must contain `examples/synthetic_bids/rawdata` (synthetic only)
- **Sandbox rule**: disallow real rawdata, arbitrary paths, path traversal

---

## 三、FWHM / Smoothing Kernel

| Aspect | Current |
|--------|---------|
| Default | `None` (no default validation) |
| Validation | ❌ no range check |
| Sandbox rule | 3 numbers, 0 < each ≤ 12 |

---

## 四、Output Contract

| Output | Location |
|--------|----------|
| Smoothed NIfTI | `derivatives_dir/rsfmri_preproc/{sub}/func/` or similar |
| Work files | `work/dpabi/subject_wrapper_workspace/{sub}/` |
| Logs | `logs/` |

| Risk | Status |
|------|:---:|
| Rawdata write | ✅ safe |
| Derivatives overwrite | ⚠️ may overwrite |

---

## 五、Safety Gaps

| Gap | Severity |
|-----|:---:|
| No runtime preflight | high |
| No FWHM validation | medium |
| No dpabi_dir validation | high |

---

## 六、Current Policy

| Layer | Status |
|-------|:---:|
| NODE_REGISTRY | ✅ registered |
| plan_adapter | ❌ blocked (`blocked_dpabi_execution_nodes`) |
| execute_reviewed | ❌ blocked |

---

## 七、Rollout

| Phase | Task |
|-------|------|
| T006a | Safety contract ✅ |
| T006b | Runtime hardening (preflight + FWHM) |
| T006c | Sandbox contract tests |
| T006d | Reviewed execution allowlist |
