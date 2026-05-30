# MedImage_Agent 项目交接总结

> 生成日期: 2026-05-29 | 对话完成阶段: M6/M7/M8 全量完成

---

## 1. 当前总状态

| 指标 | 值 |
|------|:---:|
| reviewed execution allowlist 总数 | **36 个节点** |
| M6 SPM Sandbox Pipeline | ✅ COMPLETE (7 节点) |
| M7 DPABI Phase | ✅ COMPLETE (20 节点) |
| M8 GPU Phase | ✅ COMPLETE (9 节点) |
| M9 GUI/manual Agent | ❌ 尚未开始 |
| 全局 blocked | unrestricted SPM/DPABI/GPU, real CUDA, model inference, training, GUI/manual, rawdata writes, arbitrary paths |

---

## 2. M6 SPM Sandbox Pipeline — COMPLETE

7 个 SPM 节点全部 sandbox-gated reviewed execution allowlisted:

| # | Node | Condition |
|---|------|---------|
| 1 | `spm_smoke_test` | — |
| 2 | `spm_realign_subject` | sandbox_mode=true |
| 3 | `spm_slice_timing_subject` | sandbox_mode + safe input |
| 4 | `spm_coregister_subject` | sandbox declaration |
| 5 | `spm_segment_subject` | sandbox declaration |
| 6 | `spm_normalize_subject` | sandbox declaration |
| 7 | `spm_smooth_subject` | sandbox declaration |

**安全边界**: MATLAB/SPM runtime preflight (`validate_spm_runtime_config()`), rawdata readonly, explicit node + backend approval, wildcard approval 不能覆盖 MATLAB/SPM。Unrestricted SPM execution 未开放。

---

## 3. M7 DPABI Phase — COMPLETE

20 个 DPABI 节点全部 reviewed execution allowlisted:

- **15 个 metadata/contract/capability 节点** — Python-only, no MATLAB, no DPABI
  - dpabi_capability_inspection, dpabi_input_manifest, dpabi_preflight, dpabi_run_plan, dpabi_signature_probe, dpabi_wrapper_contracts, dpabi_wrapper_scaffold, dpabi_alff_falff_contract, dpabi_functional_connectivity_contract, dpabi_nuisance_regression_contract, dpabi_reho_contract, dpabi_temporal_filtering_contract, dpabi_template_library, dpabi_template_instantiate, dpabi_template_execute

- **5 个 sandbox / report / validation execution 节点**:
  - `dpabi_sandbox_smoke_run` — sandbox-gated, MATLAB preflight
  - `dpabi_single_function_sandbox` — sandbox + 9 allowed functions + contract validation
  - `dpabi_subject_smooth` — sandbox + synthetic input + bounded FWHM + derivatives_dir_scoped
  - `dpabi_subject_wrapper_report` — sandbox + report-only + reports_dir_dpabi_only (Python-only)
  - `dpabi_wrapper_validation_matrix` — sandbox + validation-matrix-only + reports_dir_dpabi_validation_matrix_only (Python-only)

**安全边界**: Python-only metadata nodes 禁止 MATLAB/DPABI。Execution nodes 需要 sandbox declaration + explicit node + backend approval。Wildcard approval 不能覆盖 DPABI execution。DPARSF_run/DPARSFA_run/DPABI_run/dpabi_gui 全部 banned。

---

## 4. M8 GPU Phase — COMPLETE

9 个 GPU reviewed execution nodes 全部 allowlisted:

| Category | Count | Nodes |
|----------|:---:|------|
| Contract metadata | 3 | alff_falff_gpu_candidate_contract, functional_connectivity_gpu_candidate_contract, reho_gpu_candidate_contract |
| Synthetic smoke | 1 | gpu_synthetic_smoke |
| Subject-level sandbox scaffold | 5 | gpu_alff_subject, gpu_reho_subject, gpu_temporal_filtering_subject, gpu_functional_connectivity_subject, gpu_nuisance_regression_subject |

**5 个 GPU subject nodes 完成节奏**: safety contract → runner scaffold/registration/hardening → sandbox contract tests → sandbox-only reviewed execution allowlist。（每个节点均为独立 a/b/c/d 4 阶段。）

**重要**: 5 个 GPU subject nodes 是 **sandbox-gated scaffold/preflight/simulated-output nodes**。它们 **不** 执行真实的 CUDA 计算、不分配 tensor、不调用 torch.cuda、不生成真实的医学影像 derivatives。它们只做 validation、guard checks、path-scope checks 和 JSON metadata/provenance 输出。

---

## 5. M8 GPU Guard 与统一安全边界

核心 guard 模块: `src/backend/app/safety/gpu_safety.py` (35 tests)

| Guard | Policy |
|-------|--------|
| Device | auto/cpu/cuda:0 only; cuda:1/mps/arbitrary/路径/traversal blocked |
| Memory | ≤ 512MB estimated; batch_size=1; no unbounded tensor |
| Timeout | ≤ 60s (120s hard max) |
| Concurrency | Per-device lock, max 1 active job |
| OOM | catch + normalize → GPU_OOM code |
| CI | monkeypatch only; no real GPU required |

**全局 GPU 安全边界**: no CUDA call, no torch.cuda, no tensor allocation, no model loading, no training, no inference, no real medical-image GPU computation, no rawdata writes, no arbitrary input/output paths.

---

## 6. 5 个 GPU subject scaffold 节点逐项总结

### gpu_alff_subject
- 输入: scoped functional derivative
- 参数: TR 0.1–10.0s, frequency_band 0<low<high<Nyquist
- 输出: derivatives_dir/gpu/gpu_alff_subject/<run>/<sub>/
- allowlist: ✅ `allowed_gpu_alff_sandbox_nodes`
- 实现: scaffold only; `run_alff_subject` backward-compat alias

### gpu_reho_subject
- 输入: scoped functional derivative; optional scoped mask
- 参数: neighborhood ∈ {7, 19, 27}
- 输出: derivatives_dir/gpu/gpu_reho_subject/<run>/<sub>/
- allowlist: ✅ `allowed_gpu_reho_sandbox_nodes`
- 实现: scaffold only; `run_reho_subject` alias

### gpu_temporal_filtering_subject
- 输入: scoped functional derivative
- 参数: TR 0.1–10.0s, band 0<low<high<Nyquist, filter_mode=bandpass, filter_method=butterworth, filter_order=1–4
- 混合处理: runs_nuisance_regression/alff/reho/fc 全部 false
- 输出: derivatives_dir/gpu/gpu_temporal_filtering_subject/<run>/<sub>/
- allowlist: ✅ `allowed_gpu_temporal_filtering_sandbox_nodes`
- 实现: scaffold only; `run_temporal_filtering_subject` alias

### gpu_functional_connectivity_subject
- 输入: scoped functional or timeseries derivative
- 参数: atlas_source=approved_builtin_atlas or scoped_derivatives_atlas, roi_count 2–512, pearson only, fisher_z bool
- partial correlation blocked, arbitrary atlas blocked
- 输出: derivatives_dir/gpu/gpu_functional_connectivity_subject/<run>/<sub>/
- allowlist: ✅ `allowed_gpu_functional_connectivity_sandbox_nodes`
- 实现: scaffold only; `run_functional_connectivity_subject` alias

### gpu_nuisance_regression_subject
- 输入: scoped functional + scoped confounds derivative
- 参数: n_confounds 1–64, OLS only, include_intercept bool, standardize_confounds bool
- global signal blocked, scrubbing blocked, ridge/lasso/robust blocked
- 输出: derivatives_dir/gpu/gpu_nuisance_regression_subject/<run>/<sub>/
- allowlist: ✅ `allowed_gpu_nuisance_regression_sandbox_nodes`
- 实现: scaffold only; `run_nuisance_regression_subject` alias

---

## 7. 当前 reviewed execution allowlist 总表

| Phase | Nodes | Type | Status |
|-------|:---:|------|:---:|
| M6 SPM | 7 | Sandbox-gated | ✅ |
| M7 DPABI | 20 | Sandbox/metadata/report-gated | ✅ |
| M8 GPU | 9 | Sandbox-gated scaffold | ✅ |
| **Total** | **36** | | ✅ |

---

## 8. 必须保持的设计模式

后续所有高风险节点应遵循 **contract → harden → test → allowlist → closeout** 5 阶段：

1. **Safety contract** (docs only, no code)
2. **Runner scaffold / hardening** (register + preflight + guard)
3. **Sandbox contract tests** (guard behavior, inputs, outputs, no-CUDA/no-tensor)
4. **Reviewed execution allowlist** (policy layer sandbox declaration + safe allowlist integration)
5. **Closeout** (documentation update)

**铁律**:
- 不允许跳过 contract 直接 allowlist
- high-risk backend 必须有 explicit node + backend approval
- wildcard `approved_nodes=["*"]` 不可覆盖高风险节点
- blocked 状态必须 `executor_called=false`
- 每阶段都要有回归测试保护既有 allowlist

---

## 9. M9 状态与后续路线

| 状态 | M9 GUI/manual Agent design |
|------|:---:|
| 是否开始 | ❌ 尚未开始 |
| 是否会自动进入 | ❌ 否，等待用户明确要求 |
| 下一步任务 | M9-GUI-T001: GUI/manual node inventory and threat model |

M9 风险重点: GUI 自动化、鼠标键盘控制、截图/剪贴板、外部应用调用、浏览器 UI prompt injection、人类确认、审计与回滚、no-unattended-control。

---

## 10. 新对话启动提示词

将此段粘贴到新对话窗口即可:

```
你现在接手 MedImage_Agent 项目继续工作。

当前项目状态：
- M6 SPM Sandbox Pipeline: COMPLETE (7 SPM nodes sandbox-gated)
- M7 DPABI Phase: COMPLETE (20 DPABI nodes sandbox/metadata/report-gated)
- M8 GPU Phase: COMPLETE (9 GPU nodes sandbox-gated scaffold)
- Reviewed execution allowlist 总数: 36 个节点

M8 GPU 的 9 个节点构成:
- 3 GPU contract metadata (Python-only, no CUDA)
- 1 gpu_synthetic_smoke (sandbox synthetic smoke)
- 5 GPU subject scaffold nodes (sandbox-gated, scaffold only, no real CUDA)
  - gpu_alff_subject, gpu_reho_subject, gpu_temporal_filtering_subject,
    gpu_functional_connectivity_subject, gpu_nuisance_regression_subject

重要安全边界:
- 5 个 GPU subject nodes 是 scaffold/preflight/simulated-output 节点
- 它们不执行真实 CUDA 计算、不分配 tensor、不调用 torch.cuda
- 不允许 rawdata writes、不允许 arbitrary input/output paths
- 不允许 model loading / inference / training / finetuning

全局仍 blocked:
- M9 GUI/manual Agent execution
- unrestricted SPM / DPABI / GPU execution
- real CUDA medical-image processing
- model inference / training / finetuning
- unknown / uncataloged nodes

M9 GUI/manual Agent design 尚未开始。
请不要自动开始 M9，等待我明确下一步指令。
如果你需要确认当前状态，请先阅读 docs/CURRENT_STATE.md。
```
