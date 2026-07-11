# SPM Normalize Subject — Safety Contract

> M6-T009a | spm_normalize_subject 执行前安全契约

**状态**: 审计 & 设计阶段。**spm_normalize_subject 未开放 reviewed execution。**
**代码位置**: `src/backend/app/tools/spm_normalize_runner.py`

---

## 一、Runner Contract

```python
def run_spm_normalize_subject(
    matlab_command, spm_dir, subject_id, derivatives_dir, work_dir, log_dir,
    approved=False, voxel_size=None, bounding_box=None, normalize_mean=True,
    matlab_script_dir="./matlab",
) -> dict:
```

### Auto-discovery

| Input | Source | Check |
|-------|--------|-------|
| Deformation field | `derivatives/rsfmri_preproc/{sub}/anat/y_coreg_{sub}_T1w.nii` | must exist |
| Functional | `ra{sub}_bold.nii` or first `r*.nii` | `_is_safe_functional_input()` |
| Mean | `mean*.nii` | optional |

### Parameters

| Param | Default | Notes |
|-------|---------|-------|
| `voxel_size` | [3,3,3] | MNI default |
| `bounding_box` | MNI standard | |
| `normalize_mean` | True | |

---

## 二、Deformation Field Contract

- **Source**: segment output (`y_coreg_{sub}_T1w.nii`)
- **Must exist**: error if missing
- **Sandbox rule**: disallow custom path; only auto-discovered

---

## 三、Input Image Contract

- **Functional**: auto-discovered from `derivatives/rsfmri_preproc/{sub}/func/r*.nii`
- **Safety**: `_is_safe_functional_input()` — path under func dir, name starts with `r`, not `rp_`/`mean`/`wr`
- **No rawdata, no arbitrary path**

---

## 四、Output Contract

| Output | Location |
|--------|----------|
| `normalized_file` (w*.nii) | `derivatives/rsfmri_preproc/{sub}/func/` |
| `normalized_mean_file` | same |
| QC | same |

---

## 五、MATLAB/SPM Safety

| Check | Status |
|-------|:---:|
| `subprocess.run(list)` | ✅ |
| `_matlab_quote()` | ✅ |
| `validate_spm_runtime_config()` | ❌ |
| `timeout=600` | ✅ |

---

## 六、Approval

| Condition | Required |
|-----------|:---:|
| `approved_nodes` includes "spm_normalize_subject" | ✅ |
| `approved_backends` includes "matlab-spm" | ✅ |
| wildcard `["*"]` | ❌ |

---

## 七、Sandbox Rollout

| Phase | Task |
|-------|------|
| T009a | Safety contract ✅ |
| T009b | Runner hardening (preflight) |
| T009c | Sandbox contract tests |
| T009d | Reviewed execution allowlist |

---

## 八、Current Allowlist

| Node | Status |
|------|:---:|
| smoke / realign / slice_timing / coregister / segment (sandbox) | ✅ |
| `spm_normalize_subject` | ❌ |
| `spm_smooth_subject` | ❌ |
| DPABI/GPU/GUI | ❌ |
