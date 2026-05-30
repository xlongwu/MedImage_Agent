# GPU Functional Connectivity Subject — Safety Contract

> M8-GPU-T010a | gpu_functional_connectivity_subject 安全契约

**状态**: 审计 & 设计阶段。**NOT registered. NOT in allowlist.**
**Risk**: medium-high (ROI matrix, atlas input)

---

## 一、Current Status

| Field | Value |
|-------|-------|
| Node ID | `gpu_functional_connectivity_subject` |
| Backend | `gpu` |
| Registered | ❌ |
| Runner | none (catalog-only) |
| Risk | medium-high |

---

## 二、Proposed Runner

```python
def run_gpu_functional_connectivity_subject(
    *, subject_id: str,
    input_functional: str | None = None,    # scoped derivatives or timeseries
    atlas_path: str | None = None,          # approved builtin or scoped only
    derivatives_dir: str, run_id: str,
    roi_count: int | None = None,           # 2–512
    correlation_method: str = "pearson",
    fisher_z: bool = True,
    device: str = "auto",
    timeout_seconds: int = 60,
    approved: bool = True,
) -> dict:
```

File: `src/backend/app/tools/gpu_functional_connectivity_runner.py` (proposed)

---

## 三、Input / Atlas Contract

| Allowed | Blocked |
|---------|---------|
| Scoped functional derivative | Rawdata |
| Approved builtin atlas | Arbitrary atlas path |
| Scoped derivatives atlas | Remote URL atlas |
| | Path traversal, symlink escape |

---

## 四、ROI / Matrix Contract

| Parameter | Limit |
|-----------|:---:|
| roi_count | 2 ≤ n ≤ 512 |
| Matrix size | roi_count × roi_count |
| Memory | ≤ 512MB total |
| Correlation | pearson only |
| Partial corr | ❌ blocked |
| Fisher z | boolean, default true |

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

- `derivatives_dir/gpu/gpu_functional_connectivity_subject/<run>/<sub>/`
- FC matrix (JSON/CSV), QC JSON, provenance JSON

---

## 七、Approval

- `approved_nodes` must include `gpu_functional_connectivity_subject`
- `approved_backends=["gpu"]`
- Wildcard `["*"]` blocked

---

## 八、Current Policy: blocked. No code changes.
