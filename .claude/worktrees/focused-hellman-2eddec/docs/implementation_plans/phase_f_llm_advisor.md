# Phase F：LLM Advisor Layer

> 目标版本：v0.4.0 | 预计工期：3–4 周 | 前置条件：Phase B 完成（SessionDB + Error Intelligence）

---

## 1. 目标与范围

在确定性 pipeline 引擎之上，增加 LLM 辅助顾问层。LLM 只能阅读和分析，不能执行 pipeline 或修改数据。

**核心规则**：
```
LLM 只能 → 阅读 metadata / QC / error / docs → 生成建议、解释、候选参数
LLM 不能 → 调用 pipeline_executor → 修改 NIfTI → 删除文件 → 执行 SP
M/DPABI/GPU
```

---

## 2. 前置条件检查

- [ ] Phase B 完成，SessionDB 和 Error Intelligence 可用
- [ ] OpenAI-compatible API key 或 Anthropic API key（可选，不配置时返回 fallback deterministic 消息）

---

## 3. 新增/修改文件清单

```text
backend/app/advisor/                       # 新增目录
  __init__.py
  advisor_models.py                        # Pydantic models
  advisor_safety.py                        # LLM safety gate
  protocol_advisor.py                      # Protocol Advisor
  error_advisor.py                         # Error Advisor
  qc_report_advisor.py                     # QC Report Advisor
  parameter_advisor.py                     # Parameter Advisor
  docs_qa_advisor.py                       # Docs Q&A Advisor
  advisor_router.py                        # 统一 advisor 入口

backend/app/api/routes.py                  # 修改：新增 advisor 端点
.env.example                               # 修改：新增 LLM 配置项
frontend/src/components/AdvisorCenterPanel.tsx # 新增：前端顾问面板
```

---

## 4. LLM 安全策略（强制执行）

### 4.1 每个 advisor 输出必须包含 safety flags

```json
{
  "advice_only": true,
  "requires_human_confirmation": true,
  "will_execute_pipeline": false,
  "will_modify_data": false,
  "clinical_conclusion": false
}
```

### 4.2 Advisor 与 Executor 物理隔离

```
advisor/ 目录不 import:
  - pipeline_executor
  - agent_runtime
  - node_registry
  - spm_runner / dpabi_runner / gpu_*
```

### 4.3 LLM 配置可选项

```bash
# .env
MEDIMAGE_LLM_ENABLED=false          # 默认关闭
MEDIMAGE_LLM_PROVIDER=openai        # openai | anthropic
MEDIMAGE_LLM_API_KEY=               # 空 = fallback
MEDIMAGE_LLM_MODEL=gpt-4o-mini      # 建议用便宜模型做 advisor
MEDIMAGE_LLM_BASE_URL=              # 可选自定义 endpoint
```

---

## 5. 五个 Advisor 模块详细设计

### 5.1 Protocol Advisor

输入：
```json
{
  "modality": "rs-fMRI",
  "task_goal": "standard preprocessing for ALFF analysis",
  "tr": 2.0,
  "slice_count": 32,
  "has_fieldmap": false,
  "available_data": ["T1w", "BOLD"],
  "constraints": ["no MATLAB license", "Python only"]
}
```

输出：
```json
{
  "recommended_pipeline_template": "rsfmri_python_quickstart",
  "parameter_suggestions": {
    "slice_timing_reference": "middle_slice",
    "smoothing_fwhm": [6, 6, 6],
    "filter_band": [0.01, 0.08]
  },
  "warnings": ["Python normalization is approximate, not MNI-registered"],
  "unsupported_items": ["Fieldmap distortion correction requires SPM"]
}
```

核心 prompt 模板：
```text
You are a medical imaging protocol advisor. Your role is to RECOMMEND,
NOT to execute. You do not run pipelines. You do not modify data.

Based on the user's input (modality, goal, available data, constraints),
recommend a preprocessing pipeline with:
- Pipeline template name
- Parameter suggestions
- Warnings about limitations
- Items that CANNOT be handled with the given constraints

Output as JSON with safety flags.
```

### 5.2 Error Advisor

输入：
```json
{
  "error_message": "NIfTI read error: sub-003_task-rest_bold.nii header corrupt",
  "node_id": "temporal_filtering",
  "backend": "python",
  "error_category": "nifti_io_error",
  "subject_id": "sub-003"
}
```

输出：
```json
{
  "plain_language_explanation": "The file for subject sub-003 appears to have a corrupted header...",
  "likely_cause": "Upstream normalization may have produced an invalid NIfTI",
  "safe_next_steps": [
    "Run nibabel.load() on the file to check corruption",
    "Check upstream node (normalize_subject) results for sub-003",
    "Consider regenerating derivatives for this subject"
  ],
  "retry_reasonable": true
}
```

### 5.3 QC Report Advisor

输入：所有 subject-level QC JSON

输出：
```json
{
  "narrative": "Dataset of 120 subjects. 108 passed preprocessing. 12 flagged for review...",
  "highlights": {
    "best_subject": "sub-045 (mean FD 0.05)",
    "worst_subject": "sub-078 (mean FD 0.72)"
  },
  "review_recommendations": ["sub-078: excessive motion", "sub-102: poor normalization"],
  "limitations": ["Motion thresholds based on default values"]
}
```

### 5.4 Parameter Advisor

输入：
```json
{
  "parameters": {
    "tr": 2.0,
    "slice_count": 32,
    "filter_band": [0.01, 0.08]
  }
}
```

输出：
```json
{
  "explanations": {
    "filter_band": "0.01-0.08 Hz is the standard resting-state band (corresponds to 12.5-125s period)..."
  },
  "candidate_values": {
    "filter_band": [["0.01", "0.1"], ["0.008", "0.09"]]
  },
  "risks": ["Too wide filter band may include physiological noise"],
  "requires_confirmation": true
}
```

### 5.5 Docs Q&A Advisor

输入：
```json
{
  "question": "What pipelines are available for rs-fMRI preprocessing?",
  "context_docs": ["README.md", "docs/user_guide.md", "specs/pipeline_schema.md"]
}
```

输出：
```json
{
  "answer": "MedImage Agent provides 3 preprocessing pipelines: ...",
  "source_docs": ["README.md#quickstart", "docs/user_guide.md#pipelines"],
  "related_topics": ["SPM pipeline", "DPABI wrapper", "Python-only pipeline"]
}
```

---

## 6. Fallback 机制

当 `MEDIMAGE_LLM_ENABLED=false` 或 API key 未配置时：

```python
def advisor_fallback(advisor_type: str) -> dict:
    return {
        "advice_only": True,
        "fallback": True,
        "message": f"LLM advisor is not enabled. Set MEDIMAGE_LLM_ENABLED=true and configure MEDIMAGE_LLM_API_KEY to enable the {advisor_type}.",
        "requires_human_confirmation": True,
        "will_execute_pipeline": False,
        "will_modify_data": False,
        "clinical_conclusion": False,
    }
```

---

## 7. API 端点

```text
POST /api/advisor/protocol         → Protocol Advisor
POST /api/advisor/error            → Error Advisor
POST /api/advisor/qc-report        → QC Report Advisor
POST /api/advisor/parameters       → Parameter Advisor
POST /api/advisor/docs-qa          → Docs Q&A Advisor
GET  /api/advisor/status           → LLM advisor status (enabled/disabled, provider, model)
```

统一请求格式：
```json
{
  "advisor_type": "protocol",
  "input": { ... },
  "save_to_memory": false
}
```

---

## 8. 验收标准

- [ ] 不配置 LLM key 时系统仍可完整运行（全部 advisor 返回 fallback 消息）
- [ ] 5 个 advisor 端点全部可用
- [ ] advisor 输出全部包含 5 个 safety flags
- [ ] advisor 目录不 import pipeline_executor / agent_runtime
- [ ] LLM 不可调用真实影像处理
- [ ] advisor 建议可保存到 SessionDB（save_to_memory=true）
- [ ] 前端 AdvisorCenterPanel 可用
- [ ] 用户确认后建议可转化为 pipeline config（人工操作，非自动）
