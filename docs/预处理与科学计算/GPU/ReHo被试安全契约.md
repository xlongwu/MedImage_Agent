# GPU ReHo Subject — Safety Contract

> M8-GPU-T008a | gpu_reho_subject 安全契约

**状态**: 审计 & 设计阶段。**NOT registered. NOT in allowlist.**

---

## 一、Current Status

| Field | Value |
|-------|-------|
| Node ID | `gpu_reho_subject` |
| Backend | `gpu` |
| Registered | ❌ |
| Runner | none (catalog-only) |
| Risk | medium |
| Tags | rsfmri, metric, reho, gpu |

---

## 二、Proposed Runner

```python
def run_gpu_reho_subject(
    *,
    subject_id: str,
    input_functional: str,         # scoped derivatives path
    derivatives_dir: str,           # project config
    run_id: str,
    neighborhood: int = 27,         # 7, 19, or 27
    mask_path: str | None = None,   # optional, scoped derivatives only
    device: str = "auto",
    timeout_seconds: int = 60,
    approved: bool = True,
) -> dict:
```

File: `src/backend/app/tools/gpu_reho_runner.py` (proposed)

---

## 三、Input Contract

| Allowed | Blocked |
|---------|---------|
| Scoped functional derivative | Rawdata |
| Under configured `derivatives_dir` | Arbitrary absolute path |
| Optional scoped mask | Arbitrary mask path |

---

## 四、ReHo Neighborhood Contract

| Allowed values | Blocked |
|---------------|---------|
| 7 (face-adjacent) | 0, negative, float, string |
| 19 (face + edge) | > 27 |
| 27 (full 3×3×3) | Arbitrary integers |

Default: 27

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

- `derivatives_dir/gpu/gpu_reho_subject/<run_id>/<subject_id>/`
- Possible outputs: ReHo map, QC JSON, provenance JSON
- No rawdata, no arbitrary paths

---

## 七、Approval

- `approved_nodes` must include `gpu_reho_subject`
- `approved_backends=["gpu"]`
- Wildcard `["*"]` blocked

---

## 八、Current Policy: blocked. No code changes.
