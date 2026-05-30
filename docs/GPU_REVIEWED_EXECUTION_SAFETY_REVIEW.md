# GPU Reviewed Execution Safety Review

> M8-GPU-T001 | GPU 节点安全审计与分阶段路线

**状态**: 审计完成。GPU 执行节点全部阻断。contract 候选节点已识别。

---

## 一、GPU 节点分类

### Category 1: Contract/metadata (Python-only, allowlist candidates)

| Node ID | Backend | Registered | Risk | Tags |
|---------|---------|:---:|:---:|------|
| `alff_falff_gpu_candidate_contract` | unknown | ✅ | low | contract |
| `functional_connectivity_gpu_candidate_contract` | unknown | ✅ | low | contract |
| `reho_gpu_candidate_contract` | unknown | ✅ | low | contract |

> 3 nodes: Python-only contract inspection, no GPU allocation. **M8-T003 candidates.**

### Category 2: GPU subject execution (must remain blocked)

| Node ID | Backend | Registered | Risk | Tags |
|---------|---------|:---:|:---:|------|
| `gpu_alff_subject` | gpu | ❌ | medium | rsfmri, gpu, alff |
| `gpu_functional_connectivity_subject` | gpu | ❌ | medium | rsfmri, gpu, connectivity |
| `gpu_nuisance_regression_subject` | gpu | ❌ | medium | rsfmri, gpu, denoising |
| `gpu_reho_subject` | gpu | ❌ | medium | rsfmri, gpu, reho |
| `gpu_temporal_filtering_subject` | gpu | ❌ | medium | rsfmri, gpu, filtering |

> 5 nodes: NOT registered, NOT in allowlist. Would access CUDA/GPU runtime. **Must remain blocked.**

---

## 二、Current Policy Behavior

| Layer | Contract nodes | Execution nodes |
|-------|:---:|:---:|
| NODE_REGISTRY | ✅ 3 registered | ❌ 0 registered |
| plan_adapter | `allowed_contract_nodes` → blocked by safe allowlist | `blocked_gpu_nodes` / `blocked_unknown_nodes` |
| execute_reviewed | `SAFE_EXECUTION_POLICY_BLOCKED` | `EXECUTION_POLICY_BLOCKED` |

---

## 三、GPU Resource Risks

| Risk | Analysis |
|------|----------|
| Device selection | Must validate `cuda:0`/`cuda:N`, require CPU fallback |
| Memory/OOM | Must bound tensor size, batch size, detect available VRAM |
| Runtime/timeout | Must have per-node time budget, watchdog |
| Concurrency | Must prevent overlapping GPU jobs, per-device lock |
| CI compatibility | Must skip/mock when GPU unavailable |

---

## 四、M8 Roadmap

| Task | Content |
|------|---------|
| **M8-T001** ✅ | GPU safety review |
| M8-T002 | GPU runtime guard design |
| M8-T003 | Register contract runners, contract allowlist |
| M8-T004 | GPU contract tests |
| M8-T005 | GPU sandbox allowlist (contract only) |
| M8-T006 | GPU CI/mock strategy |

**Do NOT open GPU execution in M8.**
