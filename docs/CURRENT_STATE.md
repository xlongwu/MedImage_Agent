# 当前状态 (CURRENT_STATE)

> 最后更新：2026-05-29

## 里程碑进度

| 里程碑 | 状态 | 完成日期 |
|--------|------|---------|
| M1：稳定当前基础设施 | ✅ 已完成 | 2026-05-29 |
| M2：Tool Catalog MVP | ✅ 已完成 | 2026-05-29 |
| M3：LLM Planner MVP | ✅ 已完成 | 2026-05-29 |
| M5：Reviewed Execution Pipeline | ✅ 已完成 | 2026-05-29 |

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

### M7 任务（DPABI Contract/Capability）— Metadata Phase COMPLETE

| 任务 | 状态 |
|------|:---:|
| M7-DPABI-T001：DPABI safety review | ✅ |
| M7-DPABI-T002a：register safe DPABI metadata runners | ✅ |
| M7-DPABI-T002b：allowlist safe DPABI metadata contract nodes | ✅ |
| M7-DPABI-T003：DPABI metadata smoke guide | ✅ |
| M7-DPABI-T003-fix：complete DPABI metadata smoke coverage | ✅ |
| M7-DPABI-T004a：dpabi sandbox smoke safety contract | ✅ |
| M7-DPABI-T004b：register and harden DPABI sandbox smoke runner | ✅ |
| M7-DPABI-T004c：DPABI sandbox smoke contract tests | ✅ |
| M7-DPABI-T004d：allow sandbox-only DPABI smoke reviewed execution | ✅ |
| M7-DPABI-T005a：single-function safety contract | ✅ |
| M7-DPABI-T005b：single-function runtime hardening | ✅ |
| M7-DPABI-T005c：single-function contract tests | ✅ |
| M7-DPABI-T005d：single-function sandbox-only allowlist | ✅ |
| M7-DPABI-T006a：subject smooth safety contract | ✅ |
| M7-DPABI-T006b：subject smooth runtime hardening | ✅ |
| M7-DPABI-T006c：subject smooth contract tests | ✅ |
| M7-DPABI-T006d：subject smooth sandbox-only allowlist | ✅ |
| **M7 DPABI subject smooth closeout** | ✅ |

| M7-DPABI-T007a：wrapper report safety contract | ✅ |
| M7-DPABI-T007b：wrapper report output hardening | ✅ |
| M7-DPABI-T007c：wrapper report contract tests | ✅ |
| M7-DPABI-T007d：wrapper report sandbox-only allowlist | ✅ |
| **M7 DPABI wrapper report closeout** | ✅ |

> 15 metadata + sandbox_smoke + single_function + subject_smooth + wrapper_report (report-only) allowlisted.
> validation_matrix blocked. Unrestricted DPABI execution blocked. 19 DPABI nodes total.
| DPABI execution | — | ❌ |
| GPU | — | ❌ |
| GUI/manual | — | ❌ |

> M6 Full SPM Sandbox Pipeline COMPLETE (7 SPM nodes, all sandbox-gated). Manual smoke guide added. Unrestricted SPM NOT open. DPABI/GPU/GUI blocked.

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

## 已知问题

1. **audit_logger.py 不存在**：已被 M5-T007（audit_record.py）取代。
2. **Python-only 项目兼容性**：ProjectSettings 要求 `third_party.spm_dir/dpabi_dir` 为关键字段。
3. **前端执行按钮未实现**：需 M5-T019。
4. **SPM/DPABI 仍阻断**：需 M6 safety review 后逐步开放。
