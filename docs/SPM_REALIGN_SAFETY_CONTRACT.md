# SPM Realign Subject — Safety Contract

> M6-T005a | spm_realign_subject 执行前安全契约

**状态**: 审计 & 设计阶段。**spm_realign_subject 未开放 reviewed execution。**
**代码位置**: `src/backend/app/tools/spm_realign_runner.py`

---

## 一、Runner Contract

### 函数签名

```python
def run_spm_realign_subject(
    matlab_command: str,
    spm_dir: str,
    subject_id: str,
    input_bold: str,
    derivatives_dir: str,
    work_dir: str,
    log_dir: str,
    approved: bool = False,
    matlab_script_dir: str = "./matlab",
    allow_derivative_input: bool = False,
) -> dict[str, Any]:
```

### 参数来源

| 参数 | 来源 | 说明 |
|------|------|------|
| `matlab_command` | project_config | 必须通过 `matlab_safety.validate_matlab_command()` |
| `spm_dir` | project_config | 必须通过 `matlab_safety.validate_third_party_dir()` |
| `subject_id` | pipeline context / node params | BIDS subject ID |
| `input_bold` | node params / subject record | BOLD NIfTI path |
| `derivatives_dir` | project_config | 受控输出根目录 |
| `work_dir` | project_config | 工作目录 (未直接使用) |
| `log_dir` | project_config | 日志目录 |
| `approved` | approval gate (M6-T003) | 必须 `True` |
| `allow_derivative_input` | node params | 允许从 derivatives pipeline 接收输入 |

### 返回值

```json
{
  "ok": true,
  "node_id": "spm_realign_subject",
  "backend": "matlab-spm",
  "subject_id": "sub-001",
  "returncode": 0,
  "realigned_files": ["/derivatives/.../rsub-001_bold.nii"],
  "mean_file": "/derivatives/.../meansub-001_bold.nii",
  "motion_parameter_file": "/derivatives/.../rp_sub-001_bold.txt",
  "outputs": [...],
  "external_tool_result": {...}
}
```

---

## 二、Input/Output Path Contract

### 输入限制

runner 已内置输入安全检查：

| 检查 | 函数 | 规则 |
|------|------|------|
| Synthetic 输入 | `_is_safe_synthetic_input()` | 路径必须包含 `examples/synthetic_bids/rawdata` |
| Derivatives 输入 | `_is_safe_slice_timing_derivative()` | 精确匹配 `derivatives/rsfmri_preproc/{sub}/func/a{sub}_bold.nii` |

**同时拒绝两者** → 返回 error，不调用 MATLAB。

### 输出目录

```
{derivatives_dir}/rsfmri_preproc/{subject_id}/func/
  ├── {subject_id}_bold.nii          # 复制的输入 (synthetic 路径时)
  ├── r{subject_id}_bold.nii         # realigned BOLD
  ├── mean{sub_id}_bold.nii          # 均值图像
  ├── rp_{subject_id}_bold.txt       # motion 参数
  ├── spm_realign_result.json        # 结果 JSON
```

### 日志目录

```
{log_dir}/
  ├── {subject_id}_spm_realign_stdout.log
  ├── {subject_id}_spm_realign_stderr.log
```

### Path Safety 评估

| 风险 | 状态 | 说明 |
|------|:---:|------|
| 写 rawdata | ✅ 安全 | 输入安全检查拒绝非 synthetic/derivatives 路径 |
| 覆盖 rawdata | ✅ 安全 | 不写入 `data/` 目录 |
| Path traversal | ✅ 安全 | `Path().resolve()` 规范化 |
| 绝对路径注入 | ✅ 安全 | `subprocess.run(list)` + `_matlab_quote()` |
| 输出目录泄露 | ✅ 安全 | 输出固定在 `derivatives_dir/rsfmri_preproc/` |
| Sandbox 限制 | ⚠️ 待加强 | 建议增加 synthetic-only sandbox flag |

---

## 三、MATLAB/SPM Safety Contract

### 当前状态

| 检查 | 状态 |
|------|:---:|
| `subprocess.run(list)` | ✅ |
| `_matlab_quote()` 转义 | ✅ |
| `Path.resolve()` 规范化 | ✅ |
| `timeout=600` | ✅ |
| `validate_matlab_command()` | ❌ **未接入** |
| `validate_third_party_dir()` | ❌ **未接入** |
| `validate_matlab_runtime_config()` | ❌ **未接入** |
| `spm_smoke_preflight()` 类似 | ❌ **未接入** |

### 建议接入

在 `run_spm_realign_subject()` 调用 MATLAB 前增加：

```python
from src.backend.app.safety.matlab_safety import validate_matlab_runtime_config

safety = validate_matlab_runtime_config(
    matlab_command=matlab_command,
    spm_dir=spm_dir,
    dpabi_dir="./third_party/DPABI",
)
if not safety.ok:
    return {
        "ok": False,
        "errors": [e.to_dict() for e in safety.errors],
        "safety_blocked": True,
    }
```

---

## 四、Approval Contract

### 必须满足 (M6-T003)

| 条件 | 要求 |
|------|------|
| `approved_nodes` | 必须显式包含 `"spm_realign_subject"` |
| `approved_backends` | 必须包含 `"matlab-spm"` |
| wildcard `["*"]` | **不允许** 覆盖 spm_realign_subject |
| `approved` | 必须 `true` |
| `rejected_nodes` | 必须为空 |

### 不需要

| 条件 | 说明 |
|------|------|
| subject-level approval | 当前不需要 (subject_id 来自 pipeline context) |
| dataset-level approval | 当前不需要 |
| `reason` 非空 | 建议但非必须 |

---

## 五、Sandbox-Only Rollout Plan

### Phase 1: Safety contract (当前 M6-T005a)

- ✅ 审计 runner contract
- ✅ 审计 path safety
- ✅ 审计 MATLAB/SPM safety
- ✅ 定义 approval requirements
- ✅ 文档化 sandbox 策略

### Phase 2: MATLAB safety preflight (M6-T005b)

- 在 `run_spm_realign_subject()` 前接入 `validate_matlab_runtime_config()`
- safety error → 返回错误，不调用 MATLAB
- 测试覆盖: monkeypatch, 不调用真实 MATLAB

### Phase 3: Sandbox execution (M6-T005c)

- 仅允许 synthetic BIDS 输入 (`examples/synthetic_bids/rawdata`)
- 仅允许 `spm_realign_subject` + explicit node + backend approval
- 所有输出在 `outputs/derivatives/` 下
- 写入前运行 `validate_matlab_runtime_config()`
- 每次执行有独立 `run_id` 目录

### Phase 4: Reviewed execution allowlist (M6-T005d)

- 将 `spm_realign_subject` 加入 `allowed_spm_subject_nodes` (类似 M6-T004b)
- 仍需 explicit node + backend approval
- 仍需 sandbox input 限制
- 测试: mocked executor, CI-safe

### 禁止在 Phase 2 前开放

```
spm_realign_subject ← M6-T005d
spm_slice_timing_subject ← 独立 M6-T006
spm_coregister_subject ← 独立 M6-T007
spm_segment_subject ← 独立 M6-T008
spm_normalize_subject ← 独立 M6-T009
spm_smooth_subject ← 独立 M6-T010
```

---

## 六、Forbidden Cases

| 场景 | 处理 |
|------|------|
| 真实 rawdata (`data/`) 输入 | runner 已拒绝 → `unsafe input` error |
| 无 approval 执行 | runner 返回 `approved=true required` |
| wildcard approval | M6-T003 approval gate 阻断 |
| 缺少 `approved_backends` | M6-T003 approval gate 阻断 |
| MATLAB command 含参数 | `matlab_safety` 阻断 |
| spm_dir 指向 rawdata | `matlab_safety` 阻断 |
| subject-level SPM 批量执行 | 当前每个 subject 独立调用，pipeline 控制并行度 |

---

## 七、Testing Strategy

### 已有测试

```bash
pytest tests/unit/test_spm_external_contract.py
pytest tests/unit/test_spm_fake_matlab_contract.py
```

### 需要新增 (M6-T005b)

| 测试 | 说明 |
|------|------|
| synthetic input → passes safety check | `_is_safe_synthetic_input("examples/synthetic_bids/rawdata/...")` |
| rawdata input → rejected | `data/sub-001/func/bold.nii` → error |
| derivatives input → passes (when allow_derivative_input=True) | exact path match |
| approved=false → error before MATLAB | runner returns early |
| matlab safety error → error before MATLAB | preflight check |
| matlab command forbidden → error | `matlab -r evil` |
| spm_dir rawdata → error | forbidden location |
| no subprocess call on safety error | monkeypatch subprocess.run |
| no MATLAB on safety error | monkeypatch |

---

## 八、当前 Allowlist 状态

| 节点 | 状态 |
|------|:---:|
| Python-only (`data_inspection`, ...) | ✅ 允许 |
| `spm_smoke_test` | ✅ 允许 (M6-T004b) |
| `spm_realign_subject` | ❌ **阻断 (sandbox only)** |
| `spm_slice_timing_subject` | ❌ 阻断 |
| `spm_coregister_subject` | ❌ 阻断 |
| `spm_segment_subject` | ❌ 阻断 |
| `spm_normalize_subject` | ❌ 阻断 |
| `spm_smooth_subject` | ❌ 阻断 |
| DPABI execution | ❌ 阻断 |
| GPU | ❌ 阻断 |
| GUI/manual | ❌ 阻断 |

---

## 九、相关文档

- `docs/SPM_DPABI_SAFETY_REVIEW.md` — 完整 SPM/DPABI 审计
- `docs/SPM_SMOKE_MANUAL_TEST.md` — spm_smoke_test 手动验证
- `docs/MATLAB_COMMAND_SAFETY.md` — MATLAB command safety guard
- `docs/SAFE_REVIEWED_EXECUTION_DESIGN.md` — reviewed execution 设计
