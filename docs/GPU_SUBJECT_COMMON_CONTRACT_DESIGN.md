# GPU Subject-Level Common Contract Design

> M8-GPU-T007b | Subject-level GPU execution unified safety contract

**状态**: 设计阶段。No runners registered. All 5 nodes blocked.

---

## 一、Scope

Defines common safety contract for all 5 GPU subject nodes:

- `gpu_alff_subject`
- `gpu_reho_subject`
- `gpu_temporal_filtering_subject`
- `gpu_functional_connectivity_subject`
- `gpu_nuisance_regression_subject`

---

## 二、Common Sandbox Declaration

```json
{
  "sandbox_mode": true,
  "subject_level": true,
  "subject_source": "synthetic_sandbox",
  "input_source": "scoped_derivatives_only",
  "output_policy": "derivatives_dir_scoped",
  "device_policy": "guarded_auto_cpu_cuda0",
  "memory_policy": "bounded_subject_gpu",
  "timeout_policy": "bounded_subject_gpu",
  "concurrency_policy": "single_device_lock",
  "allow_rawdata_read": false,
  "allow_rawdata_write": false,
  "allow_arbitrary_input_path": false,
  "allow_arbitrary_output_path": false
}
```

---

## 三、Input Contract

| Allowed | Blocked |
|---------|---------|
| Scoped derivatives under `derivatives_dir` | Rawdata |
| | Arbitrary absolute path |
| | Path traversal |
| | Full-project recursive scan |

---

## 四、Output Contract

- Output: `derivatives_dir/gpu/<node_id>/<run_id>/<subject_id>/`
- No rawdata, no arbitrary path, no traversal
- No overwrite without explicit policy

---

## 五、Device / Memory / Timeout

| Guard | Value |
|-------|-------|
| Device | auto/cpu/cuda:0 only via `validate_gpu_device()` |
| Memory | ≤ 512MB estimated, batch_size=1, one subject per exec |
| Timeout | ≤ 60s default, ≤ 120s hard max |
| Concurrency | Per-device lock, max 1 active job |

---

## 六、CI / Mock

- No real GPU in CI
- Monkeypatch torch.cuda
- Pure guard validation only
- Manual smoke on GPU machine (optional)

---

## 七、Approval

- Explicit node approval required
- `approved_backends=["gpu"]` if backend=gpu
- Wildcard `["*"]` blocked

---

## 八、Rollout Order

1. `gpu_alff_subject` (simplest)
2. `gpu_reho_subject`
3. `gpu_temporal_filtering_subject`
4. `gpu_functional_connectivity_subject` (higher risk)
5. `gpu_nuisance_regression_subject` (higher risk)

One node per contract cycle. Do NOT open all 5 at once.
