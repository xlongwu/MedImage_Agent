# GPU Temporal Filtering Subject — Safety Contract

> M8-GPU-T009a | gpu_temporal_filtering_subject 安全契约

**状态**: 审计 & 设计阶段。**NOT registered. NOT in allowlist.**

---

## 一、Current Status

| Field | Value |
|-------|-------|
| Node ID | `gpu_temporal_filtering_subject` |
| Backend | `gpu` |
| Registered | ❌ |
| Runner | none (catalog-only) |
| Risk | medium |

---

## 二、Proposed Runner

```python
def run_gpu_temporal_filtering_subject(
    *,
    subject_id: str,
    input_functional: str,         # scoped derivatives path
    derivatives_dir: str,           # project config
    run_id: str,
    tr: float,
    frequency_band: tuple[float, float] = (0.01, 0.08),
    filter_mode: str = "bandpass",
    filter_method: str = "butterworth",
    filter_order: int = 2,          # 1–4
    device: str = "auto",
    timeout_seconds: int = 60,
    approved: bool = True,
) -> dict:
```

File: `src/backend/app/tools/gpu_temporal_filtering_runner.py` (proposed)

---

## 三、Input Contract

| Allowed | Blocked |
|---------|---------|
| Scoped functional derivative | Rawdata |
| Under `derivatives_dir` | Arbitrary path |

---

## 四、Parameter Contract

### TR: 0.1–10.0s

### Frequency band: [low, high], 0 < low < high < Nyquist

### Filter mode: `"bandpass"` only

### Filter method: `"butterworth"` only

### Filter order: 1–4, default 2

### No mixed processing (no ALFF/ReHo/nuisance/smoothing)

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

- `derivatives_dir/gpu/gpu_temporal_filtering_subject/<run>/<sub>/`
- Possible outputs: filtered functional, QC JSON, provenance JSON

---

## 七、Approval

- `approved_nodes` must include `gpu_temporal_filtering_subject`
- `approved_backends=["gpu"]`
- Wildcard `["*"]` blocked

---

## 八、Current Policy: blocked. No code changes.
