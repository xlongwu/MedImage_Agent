# LLM Provider 手动 Smoke Test

本文档说明如何用真实 OpenAI-compatible API 手动验证 LLM Planner。

**重要：本测试手动运行，不进入 CI，不写入仓库密钥。**

## 安全边界

真实 LLM provider **只能**生成 candidate plan。禁止：

- 真实 LLM 直接执行 pipeline
- 真实 LLM 调用 node runner
- 真实 LLM 修改 rawdata / 写 outputs
- 真实 LLM 绕过 Plan Validator
- 在日志或 response 中泄露 API key

流程：

```text
User Goal → OpenAI API → Candidate Plan JSON → Plan Validator → Response
```

## 环境变量

```bash
export MEDIMAGE_LLM_API_KEY="sk-..."          # 必需
export MEDIMAGE_LLM_BASE_URL="https://api.openai.com/v1"  # 可选，默认值
export MEDIMAGE_LLM_MODEL="gpt-4.1-mini"      # 可选，默认值
```

不要将 API key 写入仓库、日志或截图。

## 启动后端

```bash
uvicorn src.backend.app.main:app --host 127.0.0.1 --port 8000
```

验证：

```bash
curl http://127.0.0.1:8000/health
# → {"ok":true,"service":"medimage-agent-api","status":"healthy",...}
```

## Smoke Test 1：Motion Correction

```bash
curl -s -X POST http://127.0.0.1:8000/api/planner/plan-from-goal \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "对 rs-fMRI 数据做 realign 和 motion QC",
    "provider": "openai_compatible",
    "constraints": {"allow_matlab": true}
  }' | python -m json.tool
```

**预期成功**：

- HTTP 200
- `ok: true`
- `plan.pipeline_id` 非空
- `plan.nodes` 非空，每个 node 包含 `id`, `backend`, `depends_on`, `params`
- `validation.errors` 为空
- `validation.approval_required_nodes` 包含 SPM 节点
- `risk_summary.requires_approval: true`

## Smoke Test 2：ALFF / ReHo

```bash
curl -s -X POST http://127.0.0.1:8000/api/planner/plan-from-goal \
  -H "Content-Type: application/json" \
  -d '{"goal": "compute ALFF and ReHo", "provider": "openai_compatible"}' \
  | python -m json.tool
```

**预期成功**：

- `ok: true`
- plan 包含 `alff_falff_subject` / `reho_subject`

## 失败场景

### 无 API key

```bash
unset MEDIMAGE_LLM_API_KEY
curl -s -X POST http://127.0.0.1:8000/api/planner/plan-from-goal \
  -H "Content-Type: application/json" \
  -d '{"goal": "motion correction", "provider": "openai_compatible"}' \
  | python -m json.tool
```

**预期**：

- HTTP 200
- `ok: false`
- `errors` 包含 `LLM_API_KEY_MISSING`
- 无网络请求发出

### LLM 返回非法 JSON

（需要 LLM 配合产生 malformed response 时测试）

**预期**：

- `ok: false`
- 不 fallback 成 ok=true
- 不执行任何工具

### LLM 编造未知 node

（如果 LLM 返回不在 Tool Catalog 中的 node id）

**预期**：

- `ok: false`
- `validation.unknown_nodes` 非空
- `validation.errors` 包含 `UNKNOWN_NODE_ID`

## 本地 Python smoke（可选）

不启动 uvicorn 时可直接调用：

```python
import os
os.environ["MEDIMAGE_LLM_API_KEY"] = "sk-..."
os.environ["MEDIMAGE_LLM_BASE_URL"] = "https://api.openai.com/v1"
os.environ["MEDIMAGE_LLM_MODEL"] = "gpt-4.1-mini"

from src.backend.app.planner.llm_planner import generate_plan_from_goal
resp = generate_plan_from_goal("run motion correction", provider="openai_compatible")
print(resp.to_dict())
```

**预期**：同 API 结果一致。

## CI 说明

本 smoke test 不进入 CI。CI 中 `provider="openai_compatible"` 的测试使用 fake HTTP client 或 monkeypatch，不发真实网络请求。
