# DPABI Reviewed Execution Safety Review

> M7-DPABI-T001 | DPABI contract/capability 节点安全审计

**状态**: 审计完成。DPABI 节点已分类。Execution 节点仍全部阻断。

---

## 一、DPABI 节点分类

### Category 1: Python-only metadata/contract (allowlist candidates)

| Node ID | Backend | Registered | Tags |
|---------|---------|:---:|------|
| `dpabi_capability_inspection` | python | ❌ | contract |
| `dpabi_input_manifest` | python | ❌ | contract |
| `dpabi_preflight` | python | ❌ | contract |
| `dpabi_run_plan` | python | ❌ | contract |
| `dpabi_signature_probe` | python | ❌ | contract |
| `dpabi_wrapper_contracts` | python | ❌ | contract |
| `dpabi_wrapper_scaffold` | python | ❌ | contract |
| `dpabi_alff_falff_contract` | python | ✅ | dpabi, contract |
| `dpabi_functional_connectivity_contract` | python | ✅ | dpabi, contract |
| `dpabi_nuisance_regression_contract` | python | ✅ | dpabi, contract |
| `dpabi_reho_contract` | python | ✅ | dpabi, contract |
| `dpabi_temporal_filtering_contract` | python | ✅ | dpabi, contract |
| `dpabi_template_library` | python | ✅ | dpabi, contract |
| `dpabi_template_instantiate` | python | ✅ | dpabi, contract |
| `dpabi_template_execute` | python | ✅ | dpabi, contract |

> All 15 nodes: Python-only, no MATLAB/DPABI call, risk=low. **Allowlist candidates for M7-T002.**

### Category 2: DPABI execution (must remain blocked)

| Node ID | Backend | Registered | Risk | Tags |
|---------|---------|:---:|:---:|------|
| `dpabi_sandbox_smoke_run` | matlab | ❌ | high | dpabi, matlab |
| `dpabi_single_function_sandbox` | matlab | ❌ | high | dpabi, matlab |
| `dpabi_subject_smooth` | dpabi | ✅ | high | dpabi, matlab |
| `dpabi_subject_wrapper_report` | dpabi | ✅ | high | dpabi, matlab |
| `dpabi_wrapper_validation_matrix` | dpabi | ✅ | high | dpabi, matlab |

> All 5 nodes: call MATLAB/DPABI, risk=high. **MUST remain blocked.**

### Category 3: GPU contracts (separate route)

| Node ID | Backend |
|---------|---------|
| `alff_falff_gpu_candidate_contract` | unknown |
| `functional_connectivity_gpu_candidate_contract` | unknown |
| `reho_gpu_candidate_contract` | unknown |

> GPU contracts — separate M8 review.

---

## 二、Registry Status

| Registered in NODE_REGISTRY | 14 DPABI-related nodes |
| Catalog-only (no runner) | 9 nodes |

Catalog-only nodes that appear in plans → `VALIDATION_FAILED` (UNKNOWN_NODE_ID). Need runner registration before any allowlist consideration.

---

## 三、Current policy behavior

### plan_adapter (classify_plan_nodes)

- `dpabi_*` nodes: classified as `blocked_dpabi_execution_nodes` unless they match contract/capability/preflight/scaffold/signature/template/manifest/run_plan pattern
- Contract/capability nodes: classified as `allowed_contract_nodes`

### execute_reviewed_routes (_check_safe_allowlist)

- `allowed_contract_nodes` + `allowed_gpu_nodes` → `SAFE_EXECUTION_POLICY_BLOCKED`
- **Result**: ALL DPABI contract/capability nodes are currently blocked by safe allowlist

---

## 四、Approval gate

- `HIGH_RISK_BACKENDS` includes `"dpabi"` and `"matlab-dpabi"`
- DPABI execution nodes require explicit `approved_nodes` + `approved_backends`
- Wildcard `["*"]` blocked for DPABI backends
- ✅ Already in place from M6-T003

---

## 五、M7 Roadmap

| Task | Content |
|------|---------|
| **M7-T001** ✅ | DPABI safety review |
| M7-T002 | Register catalog-only runners, add to safe allowlist |
| M7-T003 | DPABI contract/capability manual smoke guide |
| M7-T004 | DPABI sandbox runner safety contract |
| M7-T005 | DPABI sandbox runner hardening |
| M7-T006 | DPABI sandbox contract tests |
| M7-T007 | DPABI sandbox reviewed execution allowlist |

**Do NOT open DPABI execution in M7.**
