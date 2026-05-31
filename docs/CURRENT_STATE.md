# 当前状态 (CURRENT_STATE)

> 最后更新：2026-07-11 (M9-GUI-GUARD-CLOSEOUT)

## 里程碑进度

| 里程碑 | 状态 | 完成日期 |
|--------|------|---------|
| M1：稳定当前基础设施 | ✅ 已完成 | 2026-05-29 |
| M2：Tool Catalog MVP | ✅ 已完成 | 2026-05-29 |
| M3：LLM Planner MVP | ✅ 已完成 | 2026-05-29 |
| M5：Reviewed Execution Pipeline | ✅ 已完成 | 2026-05-29 |
| M9-GUI-T001：GUI/manual threat model and inventory | ✅ 已完成 | 2026-07-11 |
| M9-GUI-T002：GUI approval and HITL design | ✅ 已完成 | 2026-07-11 |
| M9-GUI-T003：GUI action taxonomy and sandbox contract | ✅ 已完成 | 2026-07-11 |
| M9-GUI-T004：plan_adapter GUI blocklist tests | ✅ 已完成 | 2026-07-11 |
| M9-GUI-T005：Read-only GUI observation contract | ✅ 已完成 | 2026-07-11 |
| M9-GUI-T006：Manual-only GUI smoke guide | ✅ 已完成 | 2026-07-11 |
| **M9-GUI-CLOSEOUT：GUI/manual phase closeout** | ✅ 已完成 | 2026-07-11 |

**M9 GUI/manual Agent Phase: COMPLETE 🎉**  
Reviewed execution allowlist total: **36** (M6 SPM: 7 / M7 DPABI: 20 / M8 GPU: 9 / **M9 GUI: 0**)  
GUI/manual reviewed execution nodes: **0** — all blocked by design.  
Real desktop control (PyWinAuto): **disabled** — mock provider safe default.  
`/api/gui-agent/*` bypass: **known gap** — documented, not fixed.  
**M6–M9 Safety Architecture Review: COMPLETE** — `docs/M6_M9_SAFETY_ARCHITECTURE_REVIEW.md`.  
**M9-GUI-GUARD-T001: API Guard Design COMPLETE** — `docs/GUI_AGENT_API_GUARD_DESIGN.md`.  
**M9-GUI-GUARD-T002: Provider Policy Gate IMPLEMENTED** — `src/backend/app/runtime/gui_agent_guard.py` + route/runtime integration.  
**M9-GUI-GUARD-T003: Session Declaration Validator IMPLEMENTED** — `validate_gui_session_declaration()` + model + route integration.  
**M9-GUI-GUARD-T004: Action Validator + Tier Classifier IMPLEMENTED** — `classify_gui_action_tier()` + `validate_gui_action_declaration()` + route integration.  
**M9-GUI-GUARD-T005: Audit Log + Stop-Condition Checker IMPLEMENTED** — `GuiAuditRecord` + `create_gui_audit_record()` + `validate_gui_stop_conditions()` + session state + route integration.  
**M9-GUI-GUARD-T006: Guarded API Integration Tests COMPLETE** — 62 end-to-end integration tests.  
**M9 GUI Agent API Guard Phase: COMPLETE 🎉** — `/api/gui-agent/*` transformed to mock-only guarded API.  
**M10-GUI-AGENT-T001: Action Adapter Design COMPLETE** — `docs/FINE_TUNED_GUI_AGENT_ACTION_ADAPTER_DESIGN.md`.  
**M10-GUI-AGENT-T002: Normalized Action Schema COMPLETE** — `docs/NORMALIZED_GUI_ACTION_SCHEMA.md` (41-action count corrected).  
**M10-GUI-AGENT-T003: Model-Output Validator IMPLEMENTED** — `gui_agent_model_adapter.py` + 58 tests.  
**M10-GUI-AGENT-T004: Adapter/Guard Compatibility Tests COMPLETE** — 79 compatibility tests.  
**M10 Fine-Tuned GUI Agent Adapter Phase: COMPLETE 🎉** — adapter + schema + validator + compatibility tests.  
**M10-GUI-AGENT-MOCK-T001: Mock Adapter API Design COMPLETE** — `docs/MOCK_MODEL_ADAPTER_API_DESIGN.md`.  
**M10-GUI-AGENT-MOCK-T002: Mock Fixtures IMPLEMENTED** — `gui_agent_mock_model_fixtures.py` (45 fixtures, 32 tests).  
**M10-GUI-AGENT-MOCK-T003: Mock Adapter API Route IMPLEMENTED** — 2 new routes + 32 API tests.  
**M10-GUI-AGENT-MOCK-T004: Adapter-to-Guard E2E Tests COMPLETE** — 54 end-to-end tests.  
**M10 Mock-Only Model Integration Phase: COMPLETE 🎉** — fixture→adapter→guard→provider chain verified.  
**M10-GUI-AGENT-STABILIZE-T001: Error Code Audit COMPLETE** — 55 codes surveyed, 44 audit tests.  
**M10-GUI-AGENT-STABILIZE-T002: Schema Consistency Review COMPLETE** — 2 fixes + 32 tests.  
**M10-GUI-AGENT-STABILIZE-T003: Full Test Baseline Lock COMPLETE** — 1772 passed, 4 skipped, 25 invariants.  
**M11-GUI-MODEL-T001: Real Model Threat Model COMPLETE** — `docs/REAL_MODEL_INTEGRATION_THREAT_MODEL.md` (15 threat surfaces, 17 invariants).  
**M11-GUI-MODEL-T002: Runtime Isolation Design COMPLETE** — `docs/MODEL_RUNTIME_ISOLATION_DESIGN.md` (7-layer architecture, 20 test benchmarks).  
**M11-GUI-MODEL-T003: Model Provider Policy Gate Design COMPLETE** — `docs/MODEL_PROVIDER_POLICY_GATE_DESIGN.md` (8 provider types, 15 error codes).  
**M11-GUI-MODEL-T004: Input Minimization Design COMPLETE** — `docs/MODEL_INFERENCE_INPUT_REDACTION_DESIGN.md` (20 blocked classes, 14 error codes).  
**M11-GUI-MODEL-T005: Audit Metadata Persistence Design COMPLETE** — `docs/MODEL_OUTPUT_AUDIT_METADATA_PERSISTENCE_DESIGN.md` (15 events, unified schema, 19 forbidden fields).  
**M11-GUI-MODEL-T006: Mock-Real Boundary Tests Design COMPLETE** — `docs/MOCK_REAL_BOUNDARY_TESTS_DESIGN.md` (~120 tests, 10 categories, acceptance gate).  
**M11 Real Model Integration Design Phase: COMPLETE 🎉** — 7 design documents, 0 implementation. Real model not connected.  
**M11-GUI-MODEL-CONTRACT-T001: Provider Policy Gate IMPLEMENTED** — `gui_model_provider_policy.py` + 46 tests.  
**M11-GUI-MODEL-CONTRACT-T002: Runtime Isolation Contract IMPLEMENTED** — `gui_model_runtime_isolation.py` + 59 tests.  
**M11-GUI-MODEL-CONTRACT-T003: Model Source Policy IMPLEMENTED** — `gui_model_source_policy.py` + 69 tests.  
**M11-GUI-MODEL-CONTRACT-T004: Input Redaction Contract IMPLEMENTED** — `gui_model_input_redaction.py` + 63 tests.  
**M11-GUI-MODEL-CONTRACT-T005: Audit Metadata Contract IMPLEMENTED** — `gui_model_audit_contract.py` + 112 tests.  
**M11-GUI-MODEL-CONTRACT-T006: Mock-Real Boundary Tests IMPLEMENTED** — `test_gui_model_mock_real_boundary.py` + 98 tests. **2219 passed, 4 skipped.**  
**M11 Real Model Safety Contract Phase: COMPLETE 🎉** — 5 pure-function contracts + 447 tests. Real model not connected.  
**M11-GUI-MODEL-CONTRACT-STABILIZE-T001: Schema Consistency Review COMPLETE** — `docs/M11_CONTRACT_SCHEMA_CONSISTENCY_REVIEW.md` + 56 tests.  
**M11-GUI-MODEL-CONTRACT-STABILIZE-T002: Error Code Taxonomy Audit COMPLETE** — `docs/M11_CONTRACT_ERROR_CODE_TAXONOMY_AUDIT.md` + 53 tests.  
**M11-GUI-MODEL-CONTRACT-STABILIZE-T003: Test Baseline Lock COMPLETE** — `docs/M11_CONTRACT_TEST_BASELINE_LOCK.md`. **2328 passed, 4 skipped.**  
**M11-GUI-MODEL-RELEASE-CHECKPOINT: COMPLETE 🎉** — `docs/M11_FIXTURE_ONLY_GUI_MODEL_RELEASE_CHECKPOINT.md` (12 exit criteria, 24 invariants).  
**M12-RELEASE-T001: System Release Readiness Review COMPLETE** — `docs/M12_SYSTEM_RELEASE_READINESS_REVIEW.md` (module matrix, API inventory, risk register).  
**M12-RELEASE-T002: Backend API Surface Freeze COMPLETE** — `docs/M12_BACKEND_API_SURFACE_FREEZE.md` (7 API surfaces, capability flags, compatibility policy).  
**M12-RELEASE-T003: Frontend Capability Labeling Review COMPLETE** — `docs/M12_FRONTEND_CAPABILITY_LABELING_REVIEW.md` + 2 fixes in `DesktopSettingsPanel.tsx`.  
**M12-RELEASE-T004: Documentation Consistency Pass COMPLETE** — `docs/M12_DOCUMENTATION_CONSISTENCY_PASS.md` (14 docs reviewed, 4 fixes).  
**M12-RELEASE-T005: Release Smoke Checklist COMPLETE** — `docs/M12_RELEASE_SMOKE_CHECKLIST.md` (23 blocked-capability items, 12-point readiness checklist).  
**M12-RELEASE-CHECKPOINT: Project Release Checkpoint COMPLETE 🎉** — `docs/M12_PROJECT_RELEASE_CHECKPOINT.md` (final frozen baseline, post-release change policy).

### M2 任务

| 任务 | 状态 | 完成日期 |
|------|:---:|---------|
| M2-T001a：Tool Catalog 只读 MVP | ✅ | 2026-05-29 |
| M2-T001b：Tool Catalog API endpoint | ✅ | 2026-05-29 |
| M2-T002a：Plan Validator Python 模块 | ✅ | 2026-05-29 |
| M2-T002b：Plan Validator API endpoint | ✅ | 2026-05-29 |

### M3 任务

| 任务 | 状态 | 完成日期 |
|------|:---:|---------|
| M3-T001a：LLM Planner MVP（mock/rule-based） | ✅ | 2026-05-29 |
| M3-T001b：LLM Planner API endpoint | ✅ | 2026-05-29 |
| M3-T002a：OpenAI-compatible Provider Adapter | ✅ | 2026-05-29 |
| M3-T002b：Planner API openai_compatible 测试与文档 | ✅ | 2026-05-29 |
| M3-T003：真实 LLM Provider smoke test 文档 | ✅ | 2026-05-29 |

### M5 任务（Reviewed Execution Pipeline）

| 任务 | 状态 | 完成日期 |
|------|:---:|---------|
| M5-T001：Approval Gate schema + 纯函数校验 | ✅ | 2026-05-29 |
| M5-T002：Approval Gate API endpoint | ✅ | 2026-05-29 |
| M5-T003：前端 Plan Review Console Approval Gate 展示 | ✅ | 2026-05-29 |
| M5-T004：Execution Integration Design 文档 | ✅ | 2026-05-29 |
| M5-T005：execute-reviewed dry-run API | ✅ | 2026-05-29 |
| M5-T006：前端 dry-run execution readiness 展示 | ✅ | 2026-05-29 |
| M5-T007：Audit Record 模块（hash + builder + writer） | ✅ | 2026-05-29 |
| M5-T008：dry-run 可选写 audit record | ✅ | 2026-05-29 |
| M5-T009：Audit Record Read-only API | ✅ | 2026-05-29 |
| M5-T010：前端 audit record detail 展示 | ✅ | 2026-05-29 |
| M5-T011：Gated Execution Safety Review 文档 | ✅ | 2026-05-29 |
| M5-T012a：plan_adapter.py（reviewed plan → executor pipeline dict） | ✅ | 2026-05-29 |
| M5-T012b：dry-run 集成 plan_adapter（+ policy 阻断） | ✅ | 2026-05-29 |
| M5-T012c：Safe Reviewed Execution Design 文档 | ✅ | 2026-05-29 |
| M5-T013：pipeline_writer.py（reviewed pipeline YAML writer） | ✅ | 2026-05-29 |
| M5-T013-fix：pipeline_writer 路径安全收口 | ✅ | 2026-05-29 |
| **M5-T014：pipeline_writer 集成到 dry-run API** | ✅ | 2026-05-29 |
| **M5-T015：safe reviewed execution preflight** | ✅ | 2026-05-29 |
| **M5-T016：gated execution 最小实现** | ✅ | 2026-05-29 |
| **M5-T017：backend safety regression + smoke** | ✅ | 2026-05-29 |
| **M5-T018b：synthetic-only smoke doc + example config** | ✅ | 2026-05-29 |
| **M5-T018c：CI-safe integration smoke (mocked executor)** | ✅ | 2026-05-29 |
| **M5-T019：frontend safe execution button** | ✅ | 2026-05-29 |
| **M5-T020：frontend smoke + final closeout** | ✅ | 2026-05-29 |

### M6 任务（SPM/DPABI Execution Safety）— Partial Complete

**状态**: M6 Phase 1-3 完成。SPM smoke + realign sandbox + slice timing sandbox 已开放。
Full SPM pipeline (coregister/segment/normalize/smooth) 仍阻断。DPABI/GPU/GUI 仍阻断。

| 任务 | 状态 | 完成日期 |
|------|:---:|---------|
| M6-T001：SPM/DPABI execution safety review | ✅ | 2026-05-29 |
| M6-T002a：MATLAB command / third-party path safety guard | ✅ | 2026-05-29 |
| M6-T003：node-level + backend-level approval | ✅ | 2026-05-29 |
| M6-T004a：SPM smoke safety preflight | ✅ | 2026-05-29 |
| M6-T004b：spm_smoke_test reviewed execution allowlist | ✅ | 2026-05-29 |
| M6-T004c：SPM smoke manual validation guide | ✅ | 2026-05-29 |
| M6-T005a：spm realign safety contract | ✅ | 2026-05-29 |
| M6-T005b：spm realign MATLAB safety preflight | ✅ | 2026-05-29 |
| M6-T005b-fix：SPM-only validator | ✅ | 2026-05-29 |
| M6-T005c：spm realign sandbox contract tests | ✅ | 2026-05-29 |
| M6-T005d：spm_realign sandbox-only reviewed execution | ✅ | 2026-05-29 |
| M6-T006a：spm slice timing safety contract | ✅ | 2026-05-29 |
| M6-T006b：spm slice timing runner hardening | ✅ | 2026-05-29 |
| M6-T006c：spm slice timing sandbox contract tests | ✅ | 2026-05-29 |
| M6-T006d：spm_slice_timing sandbox-only reviewed execution | ✅ | 2026-05-29 |
| M6-T006d-fix：tighten slice timing sandbox input validation | ✅ | 2026-05-29 |
| M6-T007a：spm coregister safety contract | ✅ | 2026-05-29 |
| M6-T007b：spm coregister runner hardening | ✅ | 2026-05-29 |
| M6-T007c：spm coregister sandbox contract tests | ✅ | 2026-05-29 |
| M6-T007d：spm_coregister sandbox-only reviewed execution | ✅ | 2026-05-29 |
| **M6 early sandbox closeout** | ✅ | 2026-05-29 |

### M6 Reviewed Execution Allowlist (Full SPM Sandbox Pipeline — COMPLETE)

| 节点 | 条件 | 状态 |
|------|------|:---:|
| Python-only safe nodes | — | ✅ |
| `spm_smoke_test` | — | ✅ |
| `spm_realign_subject` | sandbox_mode=true | ✅ |
| `spm_slice_timing_subject` | sandbox_mode=true + safe input | ✅ |
| `spm_coregister_subject` | sandbox declaration | ✅ |
| `spm_segment_subject` | sandbox declaration | ✅ |
| `spm_normalize_subject` | sandbox declaration | ✅ |
| `spm_smooth_subject` | sandbox declaration | ✅ |

### M7 任务（DPABI Reviewed Execution）— **COMPLETE** 🎉

**Phase**: M7-DPABI-T001 → M7-DPABI-T008d (28 tasks + fixes). All 20 DPABI catalog nodes sandbox-gated.

| Task | Status |
|------|:---:|
| 28 M7 tasks (audit, register, harden, test, allowlist) | ✅ |
| **M7 DPABI full closeout** | ✅ |

### M7 Allowlisted DPABI Nodes (20)

| Category | Count | Condition |
|----------|:---:|---------|
| metadata/contract/capability | 15 | Python-only |
| `dpabi_sandbox_smoke_run` | 1 | sandbox-gated |
| `dpabi_single_function_sandbox` | 1 | sandbox + allowlisted functions |
| `dpabi_subject_smooth` | 1 | sandbox + synthetic + bounded FWHM |
| `dpabi_subject_wrapper_report` | 1 | sandbox + report-only |
| `dpabi_wrapper_validation_matrix` | 1 | sandbox + validation-matrix-only |

### Still Blocked

| Scope | Status |
|-------|:---:|
| GPU execution | ❌ M8 |
| GUI/manual | ❌ M9 |
| Unrestricted DPABI | ❌ |
| Unrestricted SPM | ❌ |
| GPU | — | ❌ |
| GUI/manual | — | ❌ |

> M6 Full SPM Sandbox Pipeline COMPLETE (7 SPM nodes, all sandbox-gated). Manual smoke guide added. Unrestricted SPM NOT open. DPABI/GPU/GUI blocked.

### M8 任务（GPU Reviewed Execution）— Contract Metadata Phase COMPLETE

| Task | Status |
|------|:---:|
| M8-GPU-T001：GPU safety review | ✅ |
| M8-GPU-T002：GPU runtime guard design | ✅ |
| M8-GPU-T003：gpu_safety.py guard + 35 tests | ✅ |
| M8-GPU-T004：GPU contract metadata runner hardening | ✅ |
| M8-GPU-T005：GPU contract metadata allowlist | ✅ |
| **M8 GPU contract metadata closeout** | ✅ |

### M8 Allowed GPU Nodes (3)

| Node | Condition |
|------|---------|
| `alff_falff_gpu_candidate_contract` | Python-only |
| `functional_connectivity_gpu_candidate_contract` | Python-only |
| `reho_gpu_candidate_contract` | Python-only |

### M8 Blocked GPU Nodes (5)

gpu_alff_subject, gpu_functional_connectivity_subject, gpu_nuisance_regression_subject, gpu_reho_subject, gpu_temporal_filtering_subject

| M8-GPU-T006a：synthetic GPU smoke safety contract | ✅ |
| M8-GPU-T006b：synthetic GPU smoke runner + registration | ✅ |
| M8-GPU-T006c：synthetic GPU smoke contract tests | ✅ |
| M8-GPU-T006d：synthetic GPU smoke sandbox-only allowlist | ✅ |
| **M8 GPU full closeout** | ✅ |

> 4 GPU nodes allowlisted (3 contract + 1 synthetic smoke). 5 subject-level GPU nodes blocked. No CUDA/GPU call by any allowlisted runner.

### Summary: 36 reviewed execution nodes (7 SPM + 20 DPABI + 9 GPU) — COMPLETE 🎉

| Phase | Nodes | Status |
|-------|:---:|:---:|
| M6 SPM | 7 | ✅ |
| M7 DPABI | 20 | ✅ |
| M8 GPU | 9 | ✅ |
| **Total** | **36** | ✅ |

### GPU Allowlist (9)

| Category | Nodes |
|----------|-------|
| Contract metadata | 3 |
| Synthetic smoke | 1 |
| Subject-level sandbox scaffold | 5 |

### Still Blocked

| Scope | Status |
|-------|:---:|
| GPU subject execution | 0 — all 5 allowlisted |
| GUI/manual | ❌ M9 |
| Real CUDA computation | ❌ |
| Unrestricted SPM/DPABI/GPU | ❌ |

## M1 交付物状态

| 交付物 | 状态 | 备注 |
|--------|------|------|
| AGENTS.md | ✅ 已完成 | 2025-07-18 |
| CLAUDE.md（含工作流规则） | ✅ 已完成 | 2025-07-18 |
| docs/PROJECT_GOAL.md | ✅ 已完成 | 2025-07-18 |
| docs/ARCHITECTURE.md | ✅ 已完成 | 2025-07-18 |
| docs/ROADMAP.md | ✅ 已完成 | 2025-07-18 |
| docs/TASK_BACKLOG.md | ✅ 已完成 | 2025-07-18 |
| docs/SAFETY_BOUNDARIES.md | ✅ 已完成 | 2025-07-18 |
| docs/DEVELOPMENT_WORKFLOW.md | ✅ 已完成 | 2025-07-18 |
| docs/DECISIONS/0001-agent-runtime-boundary.md | ✅ 已完成 | 2025-07-18 |
| docs/DECISIONS/0002-rawdata-readonly.md | ✅ 已完成 | 2025-07-18 |
| docs/CURRENT_STATE.md | ✅ 已完成 | 2026-05-29 |
| docs/NEXT_ACTIONS.md | ✅ 已完成 | 2026-05-29 |
| docs/DEV_LOG/ | ✅ 已完成 | 2026-05-29 |
| T-0001：修复 README.md 路径不一致 | ✅ 已完成 | 2025-07-18 |
| T-0002：修复 release_readiness 路径一致性 | ✅ 已完成 | 2026-05-29 |
| T-0003：新增 ProjectSettings 统一配置层 | ✅ 已完成 | 2026-05-29 |
| T-0004：验证并统一前后端启动方式 | ✅ 已完成 | 2026-05-29 |
| T-0005a：agent_plan 接入 ProjectSettings | ✅ 已完成 | 2026-05-29 |
| T-0005b：pipeline_executor 接入 ProjectSettings | ✅ 已完成 | 2026-05-29 |
| T-0005c：routes API 层接入 ProjectSettings | ✅ 已完成 | 2026-05-29 |
| T-0006：新增 CI / smoke tests | ✅ 已完成 | 2026-05-29 |
| T-0005：实现 audit_logger 或移除引用 | ⏳ 待决策 | — |

## release_readiness 状态

| 指标 | 当前值 |
|------|--------|
| 状态 | PASS |
| 总检查数 | 78 |
| PASS | 78 |
| FAIL | 0 |
| WARNING | 0 |

## 测试状态

| 指标 | 当前值 |
|------|--------|
| pytest 全量（本地） | **820 passed, 4 skipped** |
| pytest CI（Linux） | ✅ 全绿 |
| CI frontend build | ✅ 通过 |
| frontend build（本地） | ✅ 已验证 |

### M5 新增测试模块

| 测试文件 | 测试数 | 说明 |
|------|:---:|------|
| test_approval_gate.py | 17 | Approval Gate schema + 校验 |
| test_approval_gate_api.py | 14 | POST /api/approval/check |
| test_audit_record.py | 15 | hash + builder + writer |
| test_audit_record_api.py | 12 | GET /api/audit/records |
| test_execute_reviewed_api.py | 100 | POST /api/plans/execute-reviewed（M5-T014/15/16/17） |
| test_plan_adapter.py | 19 | reviewed_plan_to_pipeline_dict + classify + adapt |
| test_pipeline_writer.py | 14 | write_reviewed_pipeline_yaml |

### 已有测试模块（部分）

| 测试文件 | 测试数 |
|------|:---:|
| test_tool_catalog.py | 13 |
| test_tool_catalog_api.py | 12 |
| test_plan_validator.py | 24 |
| test_llm_planner.py | 17 |
| test_release_readiness.py | 24 |
| test_project_settings.py | 14 |

## 新增模块

| 模块 | 说明 |
|------|------|
| `src/backend/app/config/` | ProjectSettings 统一配置读取层 |
| `src/backend/app/planner/approval_gate.py` | Approval Gate schema + 纯函数校验 |
| `src/backend/app/planner/audit_record.py` | Audit Record hash + builder + atomic writer |
| `src/backend/app/planner/plan_adapter.py` | reviewed plan → executor pipeline dict 转换 |
| `src/backend/app/planner/pipeline_writer.py` | reviewed pipeline YAML atomic writer |
| `src/backend/app/api/execute_reviewed_routes.py` | POST /api/plans/execute-reviewed（dry-run only） |
| `src/backend/app/api/audit_record_routes.py` | GET /api/audit/records（只读） |
| `.github/workflows/ci.yml` | GitHub Actions CI（backend pytest + frontend build） |

## M5 安全边界

M5 Reviewed Execution Backend MVP 完成，但仅限于 safe Python-only allowlist。

| 边界 | 状态 |
|------|:---:|
| rawdata 永远 readonly | ✅ 强制 |
| 真实 pipeline 执行 | ✅ **已开放**（safe allowlist only） |
| dry_run=false 12-gate gated execution | ✅ 已实现（env + confirm + audit + config + validation + approval + adapter + policy + allowlist + yaml + audit + executor） |
| 前端 Execute Reviewed Plan 按钮 | ✅ **已实现** (disabled-by-default, 二次确认) |
| LLM 只能生成 candidate plan | ✅ 强制 |
| Plan Validator 后端必须重跑 | ✅ 强制 |
| Approval Gate 后端必须重跑 | ✅ 强制 |
| plan_adapter / execution policy | ✅ 强制（SPM/DPABI/GUI/unknown 阻断） |
| safe allowlist | ✅ 强制（Python-only; GPU/contract 阻断） |
| pipeline_writer 只写受控目录 | ✅ 强制（`outputs/work/reviewed_pipelines/`） |
| audit record 必须先于 executor | ✅ 强制 |
| pipeline YAML 必须先于 executor | ✅ 强制 |
| ProjectSettings 校验 | ✅ 强制 |
| MEDIMAGE_ENABLE_REVIEWED_EXECUTION=1 | ✅ 环境变量门控 |
| SPM 执行 | ❌ 阻断 |
| DPABI execution | ❌ 阻断 |
| GUI / manual | ❌ 阻断 |
| GPU | ❌ 阻断 |
| unknown / uncataloged | ❌ 阻断 |
| 前端执行按钮 | ❌ 未实现 |

## ProjectSettings 闭环

三条主要配置入口全部接入 ProjectSettings 结构校验：

| 入口 | 阶段 | 文件 | 状态 |
|------|------|------|:---:|
| `_load_project_config()` | PLAN | `agent_plan.py` | ✅ |
| `load_project_config()` | EXECUTE | `pipeline_executor.py` | ✅ |
| `_load_project_config()` | API | `routes.py` | ✅ |

## CI

GitHub Actions 在每次 push/PR 时自动运行：
- **backend**：Python 3.11 + `pytest --tb=short`
- **frontend**：Node 20 + `npm ci` + `npm run build`
- 不依赖 MATLAB/SPM/DPABI/GPU

## M5 收口状态

M5 Reviewed Execution Pipeline **全部完成**（M5-T001 至 M5-T020）。

- **20 tasks + 2 fixes (T013-fix + 安全收口) 全部完成**
- **100 unit tests** + **3 integration tests** (28-item safety checklist 全覆盖)
- **550 passed, 4 skipped** (全量 pytest)
- **frontend build 已验证通过** ✅
- **CI 全绿** ✅
- **前端执行按钮已实现** ✅ (disabled-by-default, 二次确认)
- **safe allowlist 限制**: Python-only nodes; SPM/DPABI/GUI/GPU/contract/manual/unknown 全部阻断
- **12-gate gated execution**: env var → confirm → audit → config → validation → approval → adapter → policy → allowlist → yaml → audit → executor

## M9 GUI/manual Agent

### M9-GUI-T001：威胁模型与盘点 — ✅ 已完成 (2026-07-11)

- 完整盘点：0 个 GUI/manual 节点在 NODE_REGISTRY / reviewed execution allowlist 中
- GUI Agent 子系统独立存在（`gui_agent.py`），但**不在 reviewed execution pipeline 内**
- 确定了 5 类威胁：无监督控制、敏感数据泄露、外部应用控制、注入攻击、截图泄露
- 制定了 4 级操作风险分类（只读观察 > 低风险导航 > 中风险交互 > 高风险/默认阻断）
- 存档位置：`docs/GUI_MANUAL_AGENT_THREAT_MODEL.md`

### M9-GUI-T002：Approval and HITL Design — ✅ 已完成 (2026-07-11)

- 完整的三层 Approval 模型（Session → Action-Plan → Per-Action）
- GUI Action Approval Schema 提案（8 个必填字段 + 13 个 Session Safety 字段）
- Provider Policy：mock 安全默认 / pywinauto 须 disabled-by-default + feature flag
- `/api/gui-agent/*` 安全集成路线比较（Option A vs B），推荐 Option B Phase 1
- Human-in-the-Loop UI 需求：语义确认、结构化 Action Plan 展示、紧急中止按钮
- 截图 / 剪贴板 / 敏感数据策略
- Audit 日志结构（13 字段 + 敏感字段脱敏）
- Emergency Abort 方案（7 条自动停止条件 + 3 层执行）
- Prompt Injection / UI Injection 防御
- 存档位置：`docs/GUI_MANUAL_APPROVAL_HITL_DESIGN.md`

### M9-GUI-T003：Action Taxonomy and Sandbox Contract — ✅ 已完成 (2026-07-11)

- 定义了完整的 GUI Action Taxonomy（29 个 action，4 个 tier）
- 每个 action 映射了当前 `gui_agent.py` 的 `PyWinAutoGuiProvider.perform_step()` action 字符串
- 定义了 GUI Session Sandbox Declaration Schema（23 字段 + 验证规则）
- 定义了 GUI Action Declaration Schema（22 字段）
- 定义了 Provider Policy Contract（Mock vs PyWinAuto vs CI）
- 定义了 Screenshot / Clipboard / File-Path / Network / External-App 5 个独立政策合约
- 定义了 Blocked Action Contract（22 个永久阻断 action）
- 定义了 Policy Classification Rules（`classify_gui_action` + `validate_gui_session_declaration` 伪代码）
- 定义了 M9-GUI-T004 的 25 个测试基准
- 存档位置：`docs/GUI_ACTION_TAXONOMY_AND_SANDBOX_CONTRACT.md`

### M9-GUI-T004：plan_adapter GUI Blocklist Tests — ✅ 已完成 (2026-07-11)

- 新增 `tests/unit/test_gui_reviewed_execution_blocklist.py`（38 个测试）
- 覆盖 7 个测试类别：Plan Adapter (12) + Approval Gate (6) + Execute-Reviewed (11) + Tool Catalog (5) + Safety Gap (1) + Regression (3)
- 关键覆盖：gui_* prefix blocked, backend=gui-agent/manual/desktop/browser 全部 blocked, wildcard approval 不能覆盖, approved_backends=["gui"] 单独不能执行, executor_called=false, tool_catalog gui_* fallback metadata 校验
- SPM / DPABI / GPU allowlist regression 全部通过
- `/api/gui-agent/*` bypass 仍存在（T004 不修复）
- 总测试数：1192 passed, 4 skipped
- 未修改 production code

### M9-GUI-T005：Read-Only GUI Observation Contract — ✅ 已完成 (2026-07-11)

- 新增 `docs/GUI_READ_ONLY_OBSERVATION_CONTRACT.md`（~1,078 行）
- 明确 Tier 0 read-only observation action set（7 个动作）
- 定义 Mock provider observation policy（safe by default, CI-allowed, no real screenshot/desktop）
- 定义 Real provider observation policy（仍 blocked, design-only, 需 future guard）
- 定义 Screenshot policy（4 个级别：disabled → ephemeral_only → persist_redacted → persist_raw=blocked）
- 定义 Window/Control/Visible text sensitive data policy（untrusted, 须脱敏, 禁止跟随 UI 指令）
- 定义 Session Declaration schema（24 字段 + 13 条必须阻断条件）
- 定义 Action Declaration schema（22 字段 + 9 条必须阻断条件）
- 定义 Blocked actions（16 个 Tier 1/2/3 动作在此 contract 中禁止）
- 定义 Audit requirements（17 个必须记录字段 + 5 个不得记录字段）
- 定义 Stop conditions（11 条自动停止条件）
- 明确 `/api/gui-agent/*` bypass 仍存在
- 定义 Future guard 设计（7-gate pipeline）和测试策略（16 个测试基准）
- 存档位置：`docs/GUI_READ_ONLY_OBSERVATION_CONTRACT.md`

### M9-GUI-T006：Manual-Only GUI Smoke Guide — ✅ 已完成 (2026-07-11)

- 新增 `docs/GUI_MANUAL_SMOKE_GUIDE.md`（~624 行）
- 完整的人工 smoke 检查清单，覆盖 36 个检查项
- 7 个自动化验证步骤（pytest 运行所有 GUI blocklist 相关测试）
- 5 个人工代码审查步骤（MockGuiProvider, PyWinAuto, tool_catalog, approval_gate, bypass）
- 明确的 Failure Diagnostics：7 种异常场景和处理建议
- Cleanup 指南和环境变量清理
- 完整的 Manual Smoke Checklist（可打印/可复制）
- `/api/gui-agent/*` bypass 记录（T006 不修复）
- 存档位置：`docs/GUI_MANUAL_SMOKE_GUIDE.md`

### M9-GUI-CLOSEOUT：Phase Closeout — ✅ 已完成 (2026-07-11)

- 新增 `docs/M9_GUI_MANUAL_PHASE_CLOSEOUT.md`（阶段收口文档）
- M9 阶段完成：7 个任务全部标记 ✅
- reviewed execution allowlist: 36 total, **M9 GUI: 0**
- 安全边界：PyWinAuto 禁用, mock 默认, reviewed execution 侧完全阻断
- 已知缺口：`/api/gui-agent/*` bypass — 已记录，未修复
- 后续推荐：Route A (GUI Guard Implementation Planning) 或 Route B (Pause and Stabilize)
- 20 条未来 real-provider 验收标准已定义
- 存档位置：`docs/M9_GUI_MANUAL_PHASE_CLOSEOUT.md`

### M9 后续阶段

| 任务 | 状态 | 说明 |
|------|:---:|------|
| M9-GUI-T001 | ✅ 已完成 | 威胁模型与盘点 |
| M9-GUI-T002 | ✅ 已完成 | GUI/manual approval 与人机交互设计 |
| M9-GUI-T003 | ✅ 已完成 | GUI 操作分类与沙箱声明合约 |
| M9-GUI-T004 | ✅ 已完成 | plan_adapter GUI 阻断列表测试 |
| M9-GUI-T005 | ✅ 已完成 | 只读 GUI 观察合约 |
| M9-GUI-T006 | ✅ 已完成 | 仅手动 smoke 指南（无自动化） |
| M9-GUI-CLOSEOUT | ✅ 已完成 | GUI/manual 阶段收尾 |

> **GUI/manual execution 仍 blocked。M9 从威胁建模开始，不实现 GUI 自动化。**

## 已知问题

1. **audit_logger.py 不存在**：已被 M5-T007（audit_record.py）取代。
2. **Python-only 项目兼容性**：ProjectSettings 要求 `third_party.spm_dir/dpabi_dir` 为关键字段。
3. **前端执行按钮已实现**：M5-T019 已完成（文档尾部旧版残留已清理）。
4. **GUI Agent 子系统未接入 reviewed execution**：`gui_agent.py` 独立于 12-gate 安全管线运行，见 `docs/GUI_MANUAL_AGENT_THREAT_MODEL.md`。
4. **SPM/DPABI 仍阻断**：需 M6 safety review 后逐步开放。
