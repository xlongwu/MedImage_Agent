# 当前状态 (CURRENT_STATE)

> 最后更新：2026-05-29

## 里程碑进度

| 里程碑 | 状态 | 完成日期 |
|--------|------|---------|
| M1：稳定当前基础设施 | ✅ 已完成 | 2026-05-29 |
| M2：Tool Catalog MVP | 🔄 进行中 | — |
| M2-T001a：Tool Catalog 只读 MVP | ✅ 已完成 | 2026-05-29 |
| M2-T001b：Tool Catalog API endpoint | ✅ 已完成 | 2026-05-29 |
| M2-T002a：Plan Validator Python 模块 | ✅ 已完成 | 2026-05-29 |
| M2-T002b：Plan Validator API endpoint | ✅ 已完成 | 2026-05-29 |
| M3-T001a：LLM Planner MVP（mock/rule-based） | ✅ 已完成 | 2026-05-29 |

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
| pytest 全量（本地） | 255 passed, 4 skipped |
| pytest CI（Linux） | ✅ 全绿 |
| CI frontend build | ✅ 通过 |
| test_tool_catalog.py | 13 passed |
| test_tool_catalog_api.py | 12 passed |
| test_plan_validator.py | 24 passed |
| test_llm_planner.py | 17 passed |
| test_project_settings.py | 14 passed |
| test_release_readiness.py | 24 passed |
| test_backend_app_import.py | 3 passed |
| test_agent_plan_project_settings.py | 12 passed |
| test_pipeline_executor_project_settings.py | 10 passed |
| test_routes_project_settings.py | 8 passed |
| npm run build | ✅ 成功 |

## 新增模块

| 模块 | 说明 |
|------|------|
| `src/backend/app/config/` | ProjectSettings 统一配置读取层 |
| `.github/workflows/ci.yml` | GitHub Actions CI（backend pytest + frontend build） |

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

## 已知问题

1. **audit_logger.py 不存在**：non-blocking，planned for M2。不阻塞 Tool Catalog MVP。
2. **Python-only 项目兼容性**：ProjectSettings 要求 `third_party.spm_dir/dpabi_dir` 为关键字段。后续支持纯 Python pipeline 时需调整。
3. **CI 全绿** ✅：backend + frontend 均通过。M1 基础设施完全闭环。
