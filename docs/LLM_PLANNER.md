# LLM Planner

## 目的

LLM Planner 将用户自然语言目标转换为 candidate pipeline plan。

流程：

```
User Goal → Planner → Tool Catalog lookup → Plan generation → Plan Validator → PlannerResponse
```

## 当前 Provider

| Provider | 说明 |
|----------|------|
| `mock` | 基于关键词规则匹配（MVP） |
| `rule_based` | 同 mock |

未来扩展 `openai`、`claude` 等真实 LLM provider。

## 支持的 Goal

| 关键词 | Pipeline |
|--------|---------|
| motion / realign / 头动 | data_inspection → spm_realign → motion_qc → motion_qc_report |
| alff / falff | data_inspection → nuisance_regression → alff_falff → alff_qc_report |
| reho | data_inspection → nuisance_regression → reho → reho_qc_report |
| smooth / 平滑 | data_inspection → spm_smooth → smoothing_qc_report |
| full pipeline / 全流程 | 完整 6 步预处理 |

## 安全边界

- Planner 不执行任何工具
- 所有 plan 必须通过 Plan Validator
- 不调用真实 LLM API
- 不读写文件

## 代码位置

- `src/backend/app/planner/llm_planner.py`
- `tests/unit/test_llm_planner.py` — 17 个测试
