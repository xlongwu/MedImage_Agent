# DPABI Wrapper Validation Matrix — Safety Contract

> M7-DPABI-T008a | dpabi_wrapper_validation_matrix 安全契约

**状态**: 审计 & 设计阶段。**NOT in reviewed execution allowlist.**
**代码位置**: `src/backend/app/tools/dpabi_wrapper_validation.py`

---

## 一、Runner Contract

```python
def write_dpabi_wrapper_validation_matrix(
    report_dir: str,             # from project_config
    contracts_path: str,         # path to dpabi_wrapper_contracts.json
    signatures_path: str,        # path to dpabi_signatures.json
    sandbox_results_dir: str,    # path to single_function sandbox results
    subject_summary_path: str,   # path to wrapper report summary
    output_dir: str,             # matrix output dir
) -> dict:
```

### Key characteristics

| Characteristic | Value |
|---------------|-------|
| Backend | `dpabi` (catalog; Python-only runner) |
| Calls MATLAB | ❌ |
| Calls DPABI | ❌ |
| `subprocess.run` | ❌ |
| Python-only | ✅ |

---

## 二、Input/Read Contract

- **Reads**: contract files, signature metadata, sandbox results, report summaries
- **Blocked**: rawdata, arbitrary paths, path traversal, full-project recursive scan
- **Sandbox rule**: scoped to configured contract/report result paths only

---

## 三、Output/Write Contract

| Output | Format |
|--------|--------|
| Matrix JSON | `output_dir/dpabi_wrapper_validation_matrix.json` |
| Matrix CSV | `output_dir/dpabi_wrapper_validation_matrix.csv` |

| Risk | Status |
|------|:---:|
| Rawdata write | ✅ safe |
| Derivatives write | ✅ safe |
| Overwrite | ⚠️ may overwrite |

---

## 四、Runtime

Not applicable — Python-only matrix generation. No MATLAB/DPABI/subprocess.

---

## 五、Current Policy

| Layer | Status |
|-------|:---:|
| NODE_REGISTRY | ✅ registered |
| plan_adapter | ❌ blocked |
| execute_reviewed | ❌ blocked |

---

## 六、Rollout

| Phase | Task |
|-------|------|
| T008a | Safety contract ✅ |
| T008b | Read/write scope hardening |
| T008c | Sandbox contract tests |
| T008d | Reviewed execution allowlist |

> This is the last DPABI catalog node. After T008d, M7 DPABI is complete.
