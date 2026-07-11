# SPM Smooth Subject — Safety Contract

> M6-T010a | spm_smooth_subject — 最后一个 SPM preprocessing 节点

**状态**: 审计 & 设计阶段。**spm_smooth_subject 未开放 reviewed execution。**
**代码位置**: `src/backend/app/tools/spm_smooth_runner.py`

---

## 一、Runner Contract

```python
def run_spm_smooth_subject(
    matlab_command, spm_dir, subject_id, derivatives_dir, work_dir, log_dir,
    approved=False, fwhm=None, matlab_script_dir="./matlab",
) -> dict:
```

### Auto-discovery

| Input | Source | Check |
|-------|--------|-------|
| Normalized functional | `derivatives/rsfmri_preproc/{sub}/func/wr*.nii` | `_is_safe_normalized_input()` |

### Parameters

| Param | Default | Notes |
|-------|---------|-------|
| `fwhm` | `[6.0, 6.0, 6.0]` | ⚠️ No range validation |

---

## 二、Input Contract

- **Source**: auto-discovered normalized functional (`wr*.nii`)
- **Safety**: `_is_safe_normalized_input()` — under func dir, name starts with `wr`, not `wmean`/`swr`/`rp_`
- **Sandbox rule**: only normalized functional from derivatives; no rawdata, no arbitrary path

---

## 三、FWHM Contract

| Check | Status |
|-------|:---:|
| Default | `[6, 6, 6]` |
| Range validation | ❌ None — allows 0, negative, extreme |
| Sandbox rule | must be 3-element list, each in [2, 12] |

---

## 四、Output

| Output | Location |
|--------|----------|
| `smoothed_file` (swr*.nii) | `derivatives/rsfmri_preproc/{sub}/func/` |
| QC | same |

---

## 五、Safety Gaps

| Gap | Severity |
|-----|:---:|
| No `validate_spm_runtime_config()` | high |
| No FWHM range validation | medium |

---

## 六、Approval

- `approved_nodes` must include `"spm_smooth_subject"`
- `approved_backends` must include `"matlab-spm"`
- wildcard `["*"]` not allowed

---

## 七、Rollout

| Phase | Task |
|-------|------|
| T010a | Safety contract ✅ |
| T010b | Runner hardening (preflight + FWHM check) |
| T010c | Sandbox contract tests |
| T010d | Reviewed execution allowlist |
