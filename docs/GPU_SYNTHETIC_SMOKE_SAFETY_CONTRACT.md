# GPU Synthetic Smoke — Safety Contract

> M8-GPU-T006a | gpu_synthetic_smoke 安全契约

**状态**: 审计 & 设计阶段。**No runner exists yet. Not in allowlist.**

---

## 一、Node Contract (proposed)

| Field | Value |
|-------|-------|
| node_id | `gpu_synthetic_smoke` (proposed) |
| backend | `gpu` |
| runner | to be created in M8-GPU-T006b |
| Category | synthetic_gpu_execution |

### Not built yet. No registered runner exists.

---

## 二、Synthetic-Only Input

| Allowed | Blocked |
|---------|---------|
| Tiny synthetic tensor metadata | Real subject data |
| Fixed/bounded shape ≤ 1e6 elements | Rawdata |
| batch_size = 1 | Derivatives |
| dtype_bytes = 4 (float32) | Arbitrary input path |
| | Path traversal |
| | Model weights loading |

---

## 三、Device Policy

| Allowed | Blocked |
|---------|---------|
| `auto` | `cuda:1`, `cuda:N` |
| `cpu` (CI fallback only) | `mps` |
| `cuda:0` (guard-gated) | Path-like device strings |
| | Shell metacharacters |

CUDA unavailable → controlled `GPU_UNAVAILABLE` (error if require_gpu, warning otherwise)

---

## 四、Memory / Tensor Budget

| Parameter | Limit |
|-----------|:---:|
| max elements | 1e6 |
| max bytes | 256 MB |
| batch_size | 1 |
| dtype | float32 |

Uses: `validate_gpu_memory_budget()` from `gpu_safety.py`

---

## 五、Timeout / Concurrency

| Policy | Limit |
|--------|:---:|
| timeout | ≤ 30s |
| concurrency | per-device lock, max 1 active job |

Uses: `validate_gpu_timeout()`, `validate_gpu_concurrency()`

---

## 六、OOM / Cleanup

- Catch: `torch.cuda.OutOfMemoryError` → `GPU_OOM`
- Normalize: `normalize_gpu_exception()`
- Cleanup: recommended via `torch.cuda.empty_cache()` (future runtime wrapper)

---

## 七、Output Scope

| Allowed | Blocked |
|---------|---------|
| `outputs/reports/gpu/smoke/<run_id>/` | rawdata |
| `outputs/work/gpu/smoke/<run_id>/` | derivatives |
| JSON-serializable report | Arbitrary paths |

---

## 八、Approval

| Condition | Required |
|-----------|:---:|
| `approved_nodes` includes `gpu_synthetic_smoke` | ✅ |
| `approved_backends` includes `gpu` | ✅ |
| wildcard `["*"]` | ❌ |

---

## 九、Current Policy

- No GPU smoke node exists → nothing to allowlist
- All GPU subject execution nodes remain blocked
- `gpu_safety.py` guard ready (M8-T003)

---

## 十、Rollout

| Phase | Task |
|-------|------|
| T006a | Safety contract ✅ |
| T006b | Runner creation + registration |
| T006c | Sandbox contract tests |
| T006d | Reviewed execution allowlist |
