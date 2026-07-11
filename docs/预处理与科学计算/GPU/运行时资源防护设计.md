# GPU Runtime Resource Guard Design

> M8-GPU-T002 | GPU 运行时资源安全防护设计

**状态**: 设计阶段。不开放 GPU execution。

---

## 一、Design Goals

1. Prevent unsafe GPU allocation from reviewed execution
2. Define safe device, memory, runtime, and concurrency bounds
3. Enable CI-safe testing without real GPU
4. Enable future synthetic GPU smoke without opening subject-level execution

## 二、Non-Goals

- Not opening GPU subject execution
- Not enabling training/finetuning
- Not enabling arbitrary model inference
- Not enabling arbitrary device selection

---

## 三、Device Selection Policy

| Allowed | Blocked |
|---------|---------|
| `"auto"` (guard auto-selects first available CUDA device or CPU) | Arbitrary strings |
| `"cpu"` (metadata/dry capability check only) | Path-like strings (`/dev/...`) |
| `"cuda:0"` only if guard confirms available | Shell metacharacters |
| | Multi-device uncontrolled selection |

### CUDA Unavailable Behavior

| Scenario | Behavior |
|----------|----------|
| CUDA not installed | `GPU_UNAVAILABLE` — no error for contract nodes; error for execution |
| `torch.cuda.device_count() == 0` | `GPU_UNAVAILABLE` |
| Device string invalid | `GPU_DEVICE_NOT_ALLOWED` |

---

## 四、Memory / VRAM Guard

### Budget limits (synthetic smoke only)

| Parameter | Max |
|-----------|-----|
| Tensor elements | 1e6 (e.g. 100×100×100) |
| Estimated bytes (float32) | 256 MB |
| Batch size | 1 |
| Model loading | ❌ |
| Training | ❌ |

### OOM Handling

```python
try:
    torch.cuda.empty_cache()
    # bounded GPU operation
except torch.cuda.OutOfMemoryError:
    return {"ok": False, "error": "GPU_OOM"}
finally:
    del tensor_refs
    torch.cuda.empty_cache()
```

### Subject-level GPU execution: blocked until independent contract

---

## 五、Runtime / Timeout Guard

| Node Type | Max Timeout |
|-----------|:---:|
| Contract/metadata | N/A (no compute) |
| Synthetic smoke | 30s |
| Subject-level execution | ❌ blocked |

### Failure codes

```text
GPU_UNAVAILABLE
GPU_DEVICE_NOT_ALLOWED
GPU_MEMORY_BUDGET_EXCEEDED
GPU_OOM
GPU_TIMEOUT
GPU_CONCURRENCY_BLOCKED
GPU_GUARD_FAILED
```

---

## 六、Concurrency Guard

- Only one GPU execution per process/device
- Metadata nodes may run without GPU lock (no VRAM)
- Future: `GPU_RESOURCE_LOCK` per device

---

## 七、CI / Mock Strategy

| Test Type | GPU Required |
|-----------|:---:|
| Device string validation | ❌ |
| Memory budget estimation | ❌ |
| OOM exception via monkeypatch | ❌ |
| Lock acquisition/release | ❌ |
| Timeout policy config | ❌ |
| Real GPU smoke | ✅ manual only |

---

## 八、Output Scope

| Allowed | Blocked |
|---------|---------|
| JSON-serializable dict (contract/metadata) | rawdata |
| `outputs/reports/gpu/smoke/<run_id>/` | data/rawdata |
| `outputs/work/gpu/smoke/<run_id>/` | derivatives (unless future contract) |

---

## 九、Approval Recommendations

| Rule | Value |
|------|-------|
| GPU backend | High-risk |
| `approved_nodes=["*"]` | ❌ must not cover GPU execution |
| `approved_backends` | Must include `"gpu"` |
| Contract/metadata nodes | Explicit node approval recommended |

---

## 十、M8 Roadmap (Updated)

| Task | Content |
|------|---------|
| M8-T001 ✅ | GPU safety review |
| M8-T002 ✅ | GPU runtime guard design |
| M8-T003 | Implement `gpu_safety.py` guard + tests |
| M8-T004 | Register/harden GPU contract nodes |
| M8-T005 | Allowlist GPU metadata/contract only |
| M8-T006 | Synthetic GPU smoke design |
