# 当前状态 (CURRENT_STATE)

> 最后更新：2026-05-29

## 里程碑进度

| 里程碑 | 状态 | 完成日期 |
|--------|------|---------|
| M1：稳定当前基础设施 | 🔄 进行中 | — |

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
| pytest 全量 | 234 passed, 4 skipped |
| test_project_settings.py | 14 passed |
| test_release_readiness.py | 24 passed |
| test_backend_app_import.py | 3 passed |
| test_agent_plan_project_settings.py | 12 passed |
| npm run build | ✅ 成功 |

## 新增模块

| 模块 | 说明 |
|------|------|
| `src/backend/app/config/` | ProjectSettings 统一配置读取层 |
| `src/backend/app/config/settings.py` | RuntimeSettings / ThirdPartySettings / SafetySettings / ProjectSettings dataclass |
| `tests/unit/test_project_settings.py` | 14 个测试：加载、默认值、错误处理、无副作用 |

## 已知问题

1. **audit_logger.py 不存在**：多处文档引用该文件，但实际未实现。T-0005 待决策。
2. **前后端未验证启动**：T-0004 待执行。
3. **配置读取重复**：pipeline_executor、agent_plan、routes 中各自实现了 `_load_project_config`。agent_plan 已迁移（T-005a），pipeline_executor 和 routes 待后续。
4. **Python-only 项目兼容性**：ProjectSettings 当前要求 `third_party.spm_dir` 和 `third_party.dpabi_dir` 为关键字段。如后续支持纯 Python pipeline（无需 MATLAB/SPM/DPABI），需调整为可选字段或提供 Python-only config 模板。
