# GPU ALFF Subject — Safety Contract

> M8-GPU-T007c | gpu_alff_subject 安全契约

**状态**: 审计 & 设计阶段。**NOT registered. NOT in allowlist.**

---

## 一、Current Status

| Field | Value |
|-------|-------|
| Node ID | `gpu_alff_subject` |
| Backend | `gpu` |
| Registered | ❌ |
| Runner | none (catalog-only) |
| Risk | medium |
| Tags | rsfmri, metric, alff, gpu |

---

## 二、Proposed Runner

```python
def run_gpu_alff_subject(
    *,
    subject_id: str,
    input_functional: str,         # scoped derivatives path
    derivatives_dir: str,           # project config
    run_id: str,
    tr: float,
    frequency_band: tuple[float, float] = (0.01, 0.08),
    compute_falff: bool = True,
    device: str = "auto",
    timeout_seconds: int = 60,
    approved: bool = True,
) -> dict:
```

File: `src/backend/app/tools/gpu_alff_runner.py` (proposed)

---

## 三、Input Contract

| Allowed | Blocked |
|---------|---------|
| Scoped preprocessed functional derivative | Rawdata |
| Under configured `derivatives_dir` | Arbitrary absolute path |
| | Path traversal |

---

## 四、Parameter Contract

### TR

- Must be numeric, finite, > 0, 0.1 ≤ TR ≤ 10.0

### Frequency band

- Two values [low, high]
- 0 < low < high
- high < Nyquist = 1/(2×TR)
- Default: [0.01, 0.08]

### compute_falff

- Boolean; if true, denominator band must be bounded

---

## 五、Device / Resource Policy

| Guard | Value |
|-------|-------|
| Device | auto/cpu/cuda:0 via `validate_gpu_device()` |
| Memory | ≤ 512MB estimated |
| Timeout | ≤ 60s (120s hard max) |
| Concurrency | Per-device lock, max 1 |

---

## 六、Output Contract

- `derivatives_dir/gpu/gpu_alff_subject/<run_id>/<subject_id>/`
- Possible outputs: ALFF map, fALFF map, QC JSON, provenance JSON
- No rawdata, no arbitrary paths, no overwrite without run_id scope

---

## 七、Approval

- `approved_nodes` must include `gpu_alff_subject`
- `approved_backends=["gpu"]`
- Wildcard `["*"]` blocked

---

## 八、Current Policy: blocked. No code changes.
