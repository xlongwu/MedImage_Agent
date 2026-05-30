# SPM Slice Timing Subject — Safety Contract

> M6-T006a | spm_slice_timing_subject 执行前安全契约

**状态**: 审计 & 设计阶段。**spm_slice_timing_subject 未开放 reviewed execution。**
**代码位置**: `src/backend/app/tools/spm_slice_timing_runner.py`

---

## 一、Runner Contract

### 函数签名

```python
def run_spm_slice_timing_subject(
    matlab_command: str,
    spm_dir: str,
    subject_id: str,
    input_bold: str,
    derivatives_dir: str,
    work_dir: str,
    log_dir: str,
    approved: bool = False,
    tr: float | None = None,
    slice_order: list[int] | None = None,
    reference_slice: int | None = None,
    matlab_script_dir: str = "./matlab",
) -> dict[str, Any]:
```

### 参数来源

| 参数 | 来源 | 说明 |
|------|------|------|
| `matlab_command` | project_config | 需通过 `validate_matlab_command()` |
| `spm_dir` | project_config | 需通过 `validate_third_party_dir()` |
| `subject_id` | pipeline context / node params | BIDS subject ID |
| `input_bold` | node params / subject record | **仅 synthetic BIDS rawdata** |
| `derivatives_dir` | project_config | 受控输出根 |
| `tr` | node params or BIDS JSON | Repetition Time (秒) |
| `slice_order` | node params or BIDS JSON | 采集顺序 |
| `reference_slice` | node params | reference slice index |
| `approved` | approval gate | 必须 True |

### 返回值

```json
{
  "ok": true,
  "node_id": "spm_slice_timing_subject",
  "backend": "matlab-spm",
  "subject_id": "sub-001",
  "corrected_file": "/derivatives/.../asub-001_bold.nii",
  "slice_timing_parameters": {"tr": 2.0, "nslices": 33, "slice_order": [...]},
  "slice_timing_qc": {"outputs": [...]},
  "outputs": [...]
}
```

---

## 二、Slice Timing 参数契约

### 参数来源

`build_slice_timing_parameters()` (in `tools/slice_timing_qc.py`) derives from:

| Param | Required | Default | Notes |
|-------|:---:|---------|-------|
| `tr` | ✅ | None | From BIDS JSON or node params |
| `slice_order` | ⚠️ | sequential ascending | Can be derived from nslices |
| `reference_slice` | ⚠️ | middle slice | Default if not specified |
| `nslices` | auto | from NIfTI dim[3] | Detected from BOLD image |
| `ta` | auto | tr - tr/nslices | Acquisition time, derived |

### 参数安全性

| 检查 | 状态 |
|------|:---:|
| TR ≤ 0 | ⚠️ 应拒绝 (由 build_slice_timing_parameters 处理) |
| slice_order 长度 ≠ nslices | ⚠️ 应拒绝 |
| reference_slice 越界 | ⚠️ 应拒绝或 clamp |
| 参数缺失 | ⚠️ 当前使用默认值，sandbox 应要求显式提供 |

---

## 三、Input/Output Path Contract

### 输入限制

| 来源 | 允许 | 说明 |
|------|:---:|------|
| synthetic BIDS rawdata | ✅ | `examples/synthetic_bids/rawdata` |
| realign derivatives | ❌ | **不支持** (不同于 realign) |
| arbitrary path | ❌ | 拒绝 |
| rawdata (`data/`) | ❌ | 拒绝 |

**关键发现**: Slice timing runner 的输入安全检查比 realign **更严** — 只接受 synthetic BIDS path。没有 `allow_derivative_input` 选项。

### 输出目录

```
{derivatives_dir}/rsfmri_preproc/{subject_id}/func/
  ├── {subject_id}_bold.nii              # 复制的输入
  ├── a{subject_id}_bold.nii             # slice-time corrected BOLD
  ├── spm_slice_timing_result.json       # result JSON
  ├── {subject_id}_slice_timing_qc.json  # QC parameters
```

### 日志目录

```
{log_dir}/
  ├── {subject_id}_spm_slice_timing_stdout.log
  ├── {subject_id}_spm_slice_timing_stderr.log
```

### Path Safety

| 风险 | 状态 |
|------|:---:|
| 写 rawdata | ✅ 安全 (仅 accept synthetic BIDS) |
| 覆盖 rawdata | ✅ 安全 (output 在 derivatives/) |
| 覆盖 derivatives | ⚠️ 会覆盖 `{sub}_bold.nii` (复制的输入) |

---

## 四、MATLAB/SPM Safety Contract

### 当前状态

| 检查 | 状态 |
|------|:---:|
| `subprocess.run(list)` | ✅ |
| `_matlab_quote()` | ✅ |
| `validate_matlab_command()` | ❌ 未接入 |
| `validate_spm_runtime_config()` | ❌ 未接入 |
| `timeout=600` | ✅ |
| safety error before MATLAB | ❌ 未接入 |

### pipeline 位置

```
spm_realign_subject → spm_slice_timing_subject
(slice timing depends on realigned BOLD in SPM preprocessing pipeline)
```

**在 sandbox 中**: slice timing 的 input 是 realign 的输出 (`derivatives/rsfmri_preproc/{sub}/func/r{sub}_bold.nii`)。但当前 runner 只接受 synthetic input，**需要新增 `allow_derivative_input` 参数**（类似 realign runner）。

---

## 五、Approval Contract

| 条件 | 要求 |
|------|------|
| `approved_nodes` | 必须包含 `"spm_slice_timing_subject"` |
| `approved_backends` | 必须包含 `"matlab-spm"` |
| wildcard `["*"]` | 不允许 |
| `approved` | 必须 True |

---

## 六、Sandbox-Only Rollout Plan

### Phase 1: Safety contract (当前 M6-T006a) ✅

- ✅ Runner 审计
- ✅ Path safety audit
- ✅ Slice timing 参数 audit
- ✅ MATLAB safety audit

### Phase 2: Runner hardening (M6-T006b)

- 接入 `validate_spm_runtime_config()` preflight
- 新增 `allow_derivative_input` 参数（接受 realign derivatives）
- 新增 `spm_slice_timing_sandbox_preflight()`

### Phase 3: Sandbox contract tests (M6-T006c)

- Fake MATLAB success/missing-output/failure
- Synthetic input + derivative input paths
- Slice timing parameter validation

### Phase 4: Reviewed execution allowlist (M6-T006d)

- 新增 `allowed_spm_slice_timing_sandbox_nodes`
- `sandbox_mode=true` + explicit node + backend approval

---

## 七、Forbidden Cases

| 场景 | 处理 |
|------|------|
| 非 synthetic 输入 | runner 已拒绝 |
| 无 approval | runner 返回 error |
| wildcard approval | M6-T003 阻断 |
| 缺少 `approved_backends` | M6-T003 阻断 |

---

## 八、当前 Allowlist 状态

| 节点 | 状态 |
|------|:---:|
| Python-only | ✅ |
| `spm_smoke_test` | ✅ |
| `spm_realign_subject` (sandbox) | ✅ |
| `spm_slice_timing_subject` | ❌ **阻断** |
| `spm_coregister_subject` | ❌ |
| `spm_segment_subject` | ❌ |
| `spm_normalize_subject` | ❌ |
| `spm_smooth_subject` | ❌ |
| DPABI/GPU/GUI | ❌ |

---

## 九、相关文档

- `docs/SPM_REALIGN_SAFETY_CONTRACT.md` — realign contract (参考模板)
- `docs/SPM_DPABI_SAFETY_REVIEW.md` — 完整 SPM/DPABI 审计
- `docs/MATLAB_COMMAND_SAFETY.md` — MATLAB command safety guard
