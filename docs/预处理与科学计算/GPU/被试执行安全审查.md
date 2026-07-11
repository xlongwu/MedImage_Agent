# GPU Subject-Level Execution Safety Review

> M8-GPU-T007a | 5 GPU subject execution nodes

**状态**: 审计完成。All 5 nodes blocked. No runners registered. No CUDA/GPU call.

---

## 一、5 Subject-Level GPU Nodes

| Node ID | Backend | Registered | Risk | Tags |
|---------|---------|:---:|:---:|------|
| `gpu_alff_subject` | gpu | ❌ | medium | rsfmri, metric, alff, gpu |
| `gpu_functional_connectivity_subject` | gpu | ❌ | medium | rsfmri, gpu, connectivity |
| `gpu_nuisance_regression_subject` | gpu | ❌ | medium | rsfmri, gpu, denoising |
| `gpu_reho_subject` | gpu | ❌ | medium | rsfmri, metric, reho, gpu |
| `gpu_temporal_filtering_subject` | gpu | ❌ | medium | rsfmri, gpu, filtering |

### All 5: catalog-only. No runners. No NODE_REGISTRY entries.

---

## 二、Per-Node Risk Assessment

| Node | Key Risk |
|------|----------|
| `gpu_alff_subject` | Tensor allocation per voxel/timepoint; unbounded volume |
| `gpu_reho_subject` | Neighborhood computation; large volume memory footprint |
| `gpu_functional_connectivity_subject` | ROI×ROI matrix; unbounded atlas/ROI count |
| `gpu_nuisance_regression_subject` | May overwrite derivatives; confounds file input |
| `gpu_temporal_filtering_subject` | Bandpass filter; temporal axis computation |

---

## 三、Common Subject-Level Safety Contract (future)

| Field | Required |
|-------|:---:|
| `sandbox_mode` | true |
| `subject_level` | true |
| `subject_source` | synthetic_sandbox / scoped_derivatives |
| `device_policy` | guarded_auto_cpu_cuda0 |
| `memory_policy` | bounded_subject_gpu |
| `timeout_policy` | max_30s (or per-node bound) |
| `output_policy` | derivatives_dir_scoped |
| `allow_rawdata_read` | false |
| `allow_rawdata_write` | false |
| `allow_arbitrary_input_path` | false |
| `allow_arbitrary_output_path` | false |
| `allow_model_loading` | false |
| `allow_training` | false |
| `allow_inference` | false |

---

## 四、Current Policy

| Layer | Behavior |
|-------|----------|
| NODE_REGISTRY | All 5 NOT registered |
| plan_adapter | All 5 blocked (`blocked_gpu_nodes` / `blocked_unknown`) |
| execute_reviewed | All 5 blocked |
| executor_called | false for all 5 |

---

## 五、Future Rollout

| Phase | Content |
|-------|---------|
| T007a ✅ | Subject-level safety review |
| T007b | Common subject GPU contract design |
| T007c-f | Per-node safety contracts (one per node) |
| T007g | Runner hardening (only if safe) |
| T007h | Sandbox contract tests |
| T007i | Allowlist (only after independent review) |

**Do NOT open all 5 at once. One node per contract cycle.**
