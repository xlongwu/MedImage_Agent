# Frontend Smoke Check

手动验证 Plan Review Console 的 checklist。每次前端改动后运行。

## 前置条件

```bash
# 启动后端
uvicorn src.backend.app.main:app --host 127.0.0.1 --port 8000

# 启动前端
cd src/frontend && npm run dev
```

## Build 检查

```bash
cd src/frontend && npm run build
# 必须 0 errors
```

## Smoke Checklist

### 1. Plan Review 页面可访问

- [ ] 点击 "Plan Review" 按钮 → 进入 Plan Review Console
- [ ] 页面包含 Goal 输入框、Provider 选择、Generate Plan 按钮

### 2. 生成 plan

- [ ] 输入 goal: `对 rs-fMRI 数据做 realign 和 motion QC`
- [ ] Provider 选 `mock`
- [ ] 点击 Generate Plan
- [ ] 显示 candidate plan（pipeline_id + nodes 表格）
- [ ] 显示 validation（ok/errors/warnings）
- [ ] 显示 risk_summary（nodes_total / approval_required_count / high_risk_count）
- [ ] 显示 approval_required_nodes / high_risk_nodes
- [ ] 显示 node metadata（name / risk / approval / tags）
- [ ] 点击某个 node → 右侧显示 detail panel

### 3. 编辑 + Re-validate

- [ ] 修改 JSON 编辑区中的内容
- [ ] 点击 Re-validate
- [ ] validation / risk_summary 更新
- [ ] 显示 "(re-validated)" 标签
- [ ] 输入非法 JSON → 显示 "JSON Parse Error"

### 4. Export / Copy

- [ ] 点击 Export JSON → 下载 `.json` 文件
- [ ] 点击 Copy JSON → 显示 "Copied!"
- [ ] 无 plan 时按钮 disabled

### 5. 安全边界

- [ ] 页面无 "Execute" 按钮
- [ ] 页面无 "Run Pipeline" 按钮
- [ ] 页面无 "Approve and Execute" 按钮
- [ ] 页面无 "Submit" 按钮

### 6. Provider 切换

- [ ] 切换 provider 为 `rule_based` → 生成 plan 正常
- [ ] 切换 provider 为 `openai_compatible`（无 API key）→ 显示 LLM_API_KEY_MISSING

### 7. 错误处理

- [ ] 后端未启动 → 显示连接错误提示
- [ ] 空 goal → 显示 "Please enter a goal"
