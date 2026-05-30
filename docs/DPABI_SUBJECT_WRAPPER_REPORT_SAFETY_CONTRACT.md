# DPABI Subject Wrapper Report — Safety Contract

> M7-DPABI-T007a | dpabi_subject_wrapper_report 安全契约

**状态**: 审计 & 设计阶段。**dpabi_subject_wrapper_report NOT in reviewed execution allowlist.**
**代码位置**: `src/backend/app/tools/dpabi_subject_wrapper_report.py`

---

## 一、Runner Contract

```python
def write_dpabi_subject_wrapper_report(
    derivatives_dir: str,    # from project_config
    report_dir: str,         # from project_config
) -> dict:
```

### Key characteristics

| Characteristic | Value |
|---------------|-------|
| Backend | `python` (report aggregation) |
| Calls MATLAB | ❌ |
| Calls DPABI | ❌ |
| `subprocess.run` | ❌ |
| Python-only | ✅ |

---

## 二、Report Input/Read Contract

- **Reads**: `derivatives_dir/dpabi_single_function/*/func/dpabi_subject_wrapper_result.json`
- **Does NOT read**: rawdata, arbitrary paths
- **Sandbox rule**: only reads from configured `derivatives_dir`; no rawdata, no path traversal

---

## 三、Report Output/Write Contract

| Output | Location |
|--------|----------|
| Summary JSON | `report_dir/dpabi/dpabi_subject_wrapper_summary.json` |
| Report MD | `report_dir/dpabi/dpabi_subject_wrapper_report.md` |

| Risk | Status |
|------|:---:|
| Rawdata write | ✅ safe |
| Derivatives write | ✅ safe |
| Report overwrite | ⚠️ may overwrite |

---

## 四、MATLAB/DPABI Runtime

Not applicable — Python-only report aggregation. No MATLAB/DPABI/subprocess.

---

## 五、Current Policy

| Layer | Status |
|-------|:---:|
| NODE_REGISTRY | ✅ registered |
| plan_adapter | ❌ blocked (`blocked_dpabi_execution_nodes`) |
| execute_reviewed | ❌ blocked |

---

## 六、Rollout

| Phase | Task |
|-------|------|
| T007a | Safety contract ✅ |
| T007b | Report output hardening (no-overwrite, atomic) |
| T007c | Sandbox contract tests |
| T007d | Reviewed execution allowlist |

> `dpabi_subject_wrapper_report` is lower risk than `subject_smooth` — Python-only, no MATLAB/DPABI.
