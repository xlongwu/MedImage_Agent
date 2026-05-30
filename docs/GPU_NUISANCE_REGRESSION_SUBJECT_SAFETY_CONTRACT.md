# GPU Nuisance Regression Subject — Safety Contract

> M8-GPU-T011a | gpu_nuisance_regression_subject 安全契约

**状态**: 审计 & 设计阶段。**NOT registered. NOT in allowlist.**
**Risk**: high (confounds, design matrix, cleaned derivatives)

---

## 一、Current Status

| Field | Value |
|-------|-------|
| Node ID | `gpu_nuisance_regression_subject` |
| Backend | `gpu` |
| Registered | ❌ |
| Runner | none (catalog-only) |
| Risk | high |

---

## 二、Proposed Runner

```python
def run_gpu_nuisance_regression_subject(
    *, subject_id: str,
    input_functional: str,           # scoped derivatives
    confounds_path: str,             # scoped derivatives
    derivatives_dir: str, run_id: str,
    confound_columns: list[str] | None = None,
    regression_mode: str = "ols",
    include_intercept: bool = True,
    allow_global_signal: bool = False,
    allow_scrubbing: bool = False,
    device: str = "auto",
    timepoints: int | None = None,
    n_confounds: int | None = None,  # 1–64
    timeout_seconds: int = 60,
    approved: bool = True,
) -> dict:
```

File: `src/backend/app/tools/gpu_nuisance_regression_runner.py` (proposed)

---

## 三、Input / Confounds Contract

| Allowed | Blocked |
|---------|---------|
| Scoped functional derivative | Rawdata |
| Scoped confounds derivative | Arbitrary confounds path |
| n_confounds 1–64 | Remote URL confounds |
| regression_mode=ols only | Ridge/lasso/robust/custom |

---

## 四、Key Policies

| Parameter | Limit/Block |
|-----------|------------|
| `allow_global_signal` | false (blocked first rollout) |
| `allow_scrubbing` | false (blocked first rollout) |
| Design matrix | n_regressors < timepoints |
| Timepoints | must match functional time dimension |
| Confound values | finite numeric only; no NaN/inf |

---

## 五、Device / Resource

| Guard | Value |
|-------|-------|
| Device | auto/cpu/cuda:0 |
| Memory | ≤ 512MB |
| Timeout | ≤ 60s (120s hard max) |
| Concurrency | Per-device lock, max 1 |

---

## 六、Output

- `derivatives_dir/gpu/gpu_nuisance_regression_subject/<run>/<sub>/`
- Cleaned functional, design matrix summary, QC JSON, provenance JSON
- Must NOT overwrite input functional

---

## 七、Approval

- `approved_nodes` must include `gpu_nuisance_regression_subject`
- `approved_backends=["gpu"]`
- Wildcard `["*"]` blocked

---

## 八、Current Policy: blocked. No code changes.
