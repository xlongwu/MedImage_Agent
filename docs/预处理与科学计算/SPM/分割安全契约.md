# SPM Segment Subject — Safety Contract

> M6-T008a | spm_segment_subject 执行前安全契约

**状态**: 审计 & 设计阶段。**spm_segment_subject 未开放 reviewed execution。**
**代码位置**: `src/backend/app/tools/spm_segment_runner.py`

---

## 一、Runner Contract

### 函数签名

```python
def run_spm_segment_subject(
    matlab_command: str,
    spm_dir: str,
    subject_id: str,
    derivatives_dir: str,     # ← coregistered T1w auto-discovered
    work_dir: str,
    log_dir: str,
    approved: bool = False,
    matlab_script_dir: str = "./matlab",
) -> dict[str, Any]:
```

### Auto-discovery

| Input | Source | Function |
|-------|--------|----------|
| coregistered T1w | `derivatives/rsfmri_preproc/{sub}/anat/coreg_{sub}_T1w.nii` | `_expected_coreg_t1w()` |
| TPM | `spm_dir/tpm/TPM.nii` (inside MATLAB wrapper) | SPM internal |

### 关键特性

- **No user-supplied image path** — all inputs auto-discovered
- **Exact path match** — `_is_safe_coreg_t1w()` compares resolved paths
- **TPM from SPM** — not validated at Python level

---

## 二、Input Contract

### T1w

| 检查 | 值 |
|------|-----|
| 来源 | auto-discovered from coregister output |
| 允许 | exact path match only |
| 拒绝 | arbitrary path, rawdata, path traversal |
| 验证 | `_is_safe_coreg_t1w()` — resolved path equality |

### TPM

| 检查 | 值 |
|------|-----|
| 来源 | `spm_dir/tpm/TPM.nii` (SPM internal) |
| Python 层验证 | ❌ 未验证 — 在 MATLAB wrapper 中 |
| 自定义路径 | ❌ 不允许 |
| Sandbox 策略 | 禁止自定义 TPM；只使用 SPM default |

---

## 三、Output Contract

### Expected outputs

| Key | File | Location |
|-----|------|---------|
| `gm_file` | c1*.nii | `derivatives/rsfmri_preproc/{sub}/anat/` |
| `wm_file` | c2*.nii | same |
| `csf_file` | c3*.nii | same |
| `deformation_field` | y_*.nii | same |
| tissue QC | *_tissue_qc.json | same |

### Path Safety

| 风险 | 状态 |
|------|:---:|
| rawdata write | ✅ 安全 (output in derivatives) |
| derivatives overwrite | ⚠️ 会覆盖已存在文件 |

---

## 四、MATLAB/SPM Safety

| 检查 | 状态 |
|------|:---:|
| `subprocess.run(list)` | ✅ |
| `_matlab_quote()` | ✅ |
| `validate_spm_runtime_config()` | ❌ 未接入 |
| `timeout=600` | ✅ |
| TPM path safety | ❌ 未校验 |

---

## 五、Approval Contract

| 条件 | 要求 |
|------|------|
| `approved_nodes` | 必须包含 "spm_segment_subject" |
| `approved_backends` | 必须包含 "matlab-spm" |
| wildcard | 不允许 |
| risk level | **高于 realign/slice_timing/coregister** (produces deformation fields, tissue maps) |

---

## 六、Sandbox Rollout (4-phase)

| Phase | 内容 | 状态 |
|-------|------|:---:|
| T008a | Safety contract | ✅ |
| T008b | Runner hardening (preflight + TPM check) | ⏳ |
| T008c | Sandbox contract tests | ⏳ |
| T008d | Reviewed execution allowlist | ⏳ |

### T008b hardening needs

- 接入 `validate_spm_runtime_config()`
- 校验 `spm_dir/tpm/TPM.nii` 存在（warning if missing）
- 禁止自定义 TPM path

---

## 七、Current Allowlist

| 节点 | 状态 |
|------|:---:|
| smoke / realign / slice_timing / coregister (sandbox) | ✅ |
| `spm_segment_subject` | ❌ **阻断** |
| normalize / smooth | ❌ |
| DPABI/GPU/GUI | ❌ |
