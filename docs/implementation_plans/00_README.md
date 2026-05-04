# MedImage Agent 实施计划索引

> 基于 `docs/MedImage_Agent_Next_Stage_Plan.md` 的逐阶段详细实施方案
> 每个 Phase 对应一个独立文档，包含具体文件路径、代码模式、验收标准

---

## 计划文档清单

| 编号 | 文档 | 阶段 | 目标版本 | 预计工期 |
|------|------|------|---------|---------|
| 00 | [README.md](00_README.md) | 索引 | — | — |
| A | [phase_a_v0.1_seal.md](phase_a_v0.1_seal.md) | MVP 封版验证 | v0.1.0 | 2–3 天 |
| B1 | [phase_b1_session_db.md](phase_b1_session_db.md) | SessionDB + FTS5 | v0.2.0 | 3–4 天 |
| B2 | [phase_b2_insights.md](phase_b2_insights.md) | Insights Dashboard | v0.2.0 | 2–3 天 |
| B3 | [phase_b3_error_intelligence.md](phase_b3_error_intelligence.md) | Error Intelligence | v0.2.0 | 2–3 天 |
| B4 | [phase_b4_async_review.md](phase_b4_async_review.md) | Async Background Review | v0.2.0 | 1–2 天 |
| B5 | [phase_b5_memory_provider.md](phase_b5_memory_provider.md) | MemoryProvider 抽象 | v0.2.0 | 2–3 天 |
| C | [phase_c_spm_integration.md](phase_c_spm_integration.md) | 真实 SPM 联调 | v0.3.0-alpha | 3–4 周 |
| D | [phase_d_dpabi_wrapper.md](phase_d_dpabi_wrapper.md) | DPABI wrapper 原型 | v0.3.0-beta | 2–3 周 |
| E | [phase_e_gpu_backend.md](phase_e_gpu_backend.md) | GPU backend 原型 | v0.3.0 | 2–3 周 |
| F | [phase_f_llm_advisor.md](phase_f_llm_advisor.md) | LLM Advisor Layer | v0.4.0 | 3–4 周 |
| G | [phase_g_real_data_sandbox.md](phase_g_real_data_sandbox.md) | 真实数据沙盒 | v0.5.0 | 2–3 周 |

---

## 实施顺序

```
Phase A (v0.1 封版)
  ↓
Phase B1 (SessionDB)  →  Phase B2 (Insights)
  ↓                          ↓
Phase B3 (Error Intelligence)
  ↓
Phase B4 (Async Review)  +  Phase B5 (MemoryProvider)
  ↓
Phase C (SPM 联调)  →  Phase D (DPABI)  →  Phase E (GPU)
  ↓
Phase F (LLM Advisor)
  ↓
Phase G (Real Data Sandbox)
```

---

## 核心原则（所有 Phase 通用）

1. **确定性 pipeline 核心不可被 LLM 替代**
2. **所有执行必须经过 approval gate**
3. **rawdata 永远只读**
4. **每个新模块 = spec + tool + API + frontend + test + docs**
5. **增量 PR，不做大规模重构**
6. **不接入 LLM 时系统仍可完整运行**

---

## 每份实施文档的结构

```text
1. 目标与范围
2. 前置条件检查
3. 新增/修改文件清单
4. 逐步实施步骤（含代码模式）
5. API 端点设计
6. 前端组件设计
7. 测试用例
8. 验收标准
9. 风险与注意事项
```
