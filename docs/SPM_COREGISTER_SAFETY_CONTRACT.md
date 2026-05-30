# SPM Coregister Subject — Safety Contract

> M6-T007a | spm_coregister_subject 执行前安全契约

**状态**: 审计 & 设计阶段。**spm_coregister_subject 未开放 reviewed execution。**
**代码位置**: `src/backend/app/tools/spm_coregister_runner.py`

---

## 一、Runner Contract

### 函数签名

```python
def run_spm_coregister_subject(
    matlab_command: str,
    spm_dir: str,
    subject_id: str,
    subject_record: dict[str, Any],   # ← 与其他 SPM runners 不同
    derivatives_dir: str,
    work_dir: str,
    log_dir: str,
    approved: bool = False,
    matlab_script_dir: str = "./matlab",
) -> dict[str, Any]:
```

### 参数来源

| 参数 | 来源 | 说明 |
|------|------|------|
| `matlab_command` | project_config | 需 validate_matlab_command() |
| `spm_dir` | project_config | 需 validate_third_party_dir() |
| `subject_id` | pipeline context | BIDS subject ID |
| `subject_record` | pipeline context | **包含 sessions/ anatomy paths** |
| `derivatives_dir` | project_config | 受控输出根 |
| `approved` | approval gate | 必须 True |

### 关键差异

与其他 SPM runners 不同，coregister 使用 **auto-discovery** 而非 `input_bold` param：

| Discovered | Source | Function |
|-----------|--------|----------|
| T1w (source) | `subject_record.sessions[].anat.t1w` | `_find_subject_t1w()` |
| mean functional (reference) | `derivatives/rsfmri_preproc/{sub}/func/mean*.nii` | `_find_mean_functional()` |

---

## 二、Image Contract

### Reference image (mean functional)

- **来源**: auto-discovered from `derivatives/rsfmri_preproc/{subject_id}/func/mean*.nii`
- **生产者**: spm_realign_subject (after realignment creates mean image)
- **约束**: 必须存在，否则返回 error
- **只读**: ✅ (不修改原文件)

### Source image (T1w)

- **来源**: auto-discovered from `subject_record.sessions[].anat.t1w`
- **约束**: 必须通过 `_is_safe_synthetic_t1w()` — 路径必须包含 `examples/synthetic_bids/rawdata`
- **只读**: ✅ (复制到 derivatives, 不写回 rawdata)

### Other images

- 当前不支持 other images

---

## 三、Path Contract

### 输入限制

| 输入 | 允许来源 | 安全检查 |
|------|---------|------|
| T1w | synthetic BIDS rawdata only | `_is_safe_synthetic_t1w()` |
| mean functional | auto-discovered from derivatives | implicit (from derivatives dir) |

### 输出

```
{derivatives_dir}/rsfmri_preproc/{subject_id}/anat/
  ├── {subject_id}_T1w.nii              # 复制的 T1w
  ├── coreg_{subject_id}_T1w.nii        # coregistered T1w
  ├── spm_coregistration_result.json
  ├── {subject_id}_coregistration_qc.json
```

### Path Safety

| 风险 | 状态 |
|------|:---:|
| T1w → rawdata write | ✅ 安全 (read-only, copy to derivatives) |
| mean functional → modified | ✅ 安全 (read-only) |
| derivatives overwrite | ⚠️ 会覆盖 `{sub}_T1w.nii` |

---

## 四、MATLAB/SPM Safety

| 检查 | 状态 |
|------|:---:|
| `subprocess.run(list)` | ✅ |
| `_matlab_quote()` | ✅ |
| `validate_spm_runtime_config()` | ❌ 未接入 |
| `timeout=600` | ✅ |

---

## 五、Approval Contract

| 条件 | 要求 |
|------|------|
| `approved_nodes` | 必须包含 "spm_coregister_subject" |
| `approved_backends` | 必须包含 "matlab-spm" |
| wildcard `["*"]` | 不允许 |

---

## 六、Sandbox Rollout (4-phase)

| Phase | 内容 | 状态 |
|-------|------|:---:|
| T007a | Safety contract | ✅ |
| T007b | Runner hardening (preflight + allow_derivative_input) | ⏳ |
| T007c | Sandbox contract tests | ⏳ |
| T007d | Reviewed execution allowlist | ⏳ |

### T007b runner hardening needs

- 接入 `validate_spm_runtime_config()`
- 新增 `allow_derivative_t1w: bool = False` 参数 (允许 derivatives T1w)
- 新增 `_is_safe_derivative_t1w()` 检查

---

## 七、Allowlist

| 节点 | 状态 |
|------|:---:|
| `spm_smoke_test` | ✅ |
| `spm_realign_subject` (sandbox) | ✅ |
| `spm_slice_timing_subject` (sandbox) | ✅ |
| `spm_coregister_subject` | ❌ **阻断** |
| segment/normalize/smooth | ❌ |
| DPABI/GPU/GUI | ❌ |
