# Reviewed Execution Smoke Test

> 手动验证 synthetic-only reviewed plan execution (M5-T018b)

**前置条件**: M5 全部完成。safe allowlist Python-only 节点可通过 12-gate execution 进入真实 executor。

**状态**: 手动 smoke — 不进入 CI。

## 一、依赖检查

```bash
# 确认 Python dependencies
python -c "import numpy, nibabel, yaml; print('OK')"

# 如果缺少 numpy/nibabel:
pip install numpy nibabel
```

## 二、环境变量

```bash
# 启用 reviewed execution
# Windows: set MEDIMAGE_ENABLE_REVIEWED_EXECUTION=1
export MEDIMAGE_ENABLE_REVIEWED_EXECUTION=1

# 验证
echo $MEDIMAGE_ENABLE_REVIEWED_EXECUTION
# 应输出: 1
```

## 三、启动后端

```bash
uvicorn src.backend.app.main:app --host 127.0.0.1 --port 8000
```

## 四、构造 smoke 请求

创建 `smoke_request.json`:

```json
{
  "plan": {
    "pipeline_id": "synthetic_smoke_python_only",
    "nodes": [
      {
        "id": "create_synthetic_bids",
        "backend": "python",
        "depends_on": [],
        "params": {
          "output_dir": "./tmp_smoke_synthetic_rawdata",
          "subjects": ["sub-smoke01"]
        }
      },
      {
        "id": "data_inspection",
        "backend": "python",
        "depends_on": ["create_synthetic_bids"],
        "params": {
          "rawdata_dir": "./tmp_smoke_synthetic_rawdata",
          "output_dir": "./tmp_smoke_dataset_index"
        }
      }
    ]
  },
  "approval": {
    "approved": true,
    "approved_by": "smoke-tester",
    "approved_nodes": ["*"],
    "rejected_nodes": []
  },
  "project_config_path": "examples/project_config_synthetic_smoke.yaml",
  "dry_run": false,
  "persist_audit": true,
  "write_pipeline_yaml": true,
  "confirm_execution": true,
  "actor": "smoke-tester"
}
```

## 五、节点说明

| Node | 功能 | 输出 |
|------|------|------|
| `create_synthetic_bids` | 生成合成 BIDS 数据 (sub-smoke01) | `./tmp_smoke_synthetic_rawdata/` |
| `data_inspection` | 检查 BIDS 目录结构 | `./tmp_smoke_dataset_index/` |

两个节点均为纯 Python，不依赖 MATLAB/SPM/DPABI/GPU。

## 六、调用 API

```bash
curl -s -X POST http://127.0.0.1:8000/api/plans/execute-reviewed \
  -H "Content-Type: application/json" \
  -d @smoke_request.json | python -m json.tool
```

## 七、预期响应

### 成功 (`EXECUTION_SUBMITTED`)

```json
{
  "ok": true,
  "status": "EXECUTION_SUBMITTED",
  "dry_run": false,
  "would_execute": true,
  "execution_allowed": true,
  "validation": { "ok": true },
  "approval_gate": { "execution_allowed": true },
  "adapter": { "ok": true, "pipeline": { "available": true } },
  "pipeline_yaml": {
    "would_write": true,
    "written": true,
    "path": "outputs/work/reviewed_pipelines/reviewed_synthetic_smoke_..."
  },
  "audit": {
    "persisted": true,
    "audit_id": "audit_...",
    "event_type": "execution_requested"
  },
  "execution": {
    "submitted": true,
    "run_id": "reviewed_synthetic_smoke_python_only",
    "executor_called": true
  },
  "executor_result": {
    "status": "SUCCESS"
  }
}
```

### 如果 env var 未设置

```json
{
  "ok": false,
  "status": "REVIEWED_EXECUTION_DISABLED",
  "execution": { "executor_called": false }
}
```

### 如果 confirm_execution=false

```json
{
  "ok": false,
  "status": "CONFIRMATION_REQUIRED"
}
```

## 八、验证清单

| # | 验证项 | 命令/方法 |
|---|--------|----------|
| 1 | `status == EXECUTION_SUBMITTED` | 检查 response |
| 2 | `executor_called == true` | 检查 response.execution |
| 3 | `submitted == true` | 检查 response.execution |
| 4 | `run_id` 非空 | 检查 response.execution |
| 5 | pipeline YAML 写入 | `ls outputs/work/reviewed_pipelines/` |
| 6 | audit record 写入 | `ls outputs/reports/audit_records/` |
| 7 | audit event_type | 应为 `execution_requested` |
| 8 | 合成数据已生成 | `ls tmp_smoke_synthetic_rawdata/` |
| 9 | 数据检查已完成 | `ls tmp_smoke_dataset_index/` |
| 10 | 无 rawdata 修改 | `git status data/` (应为空) |

## 九、SPM/DPABI/GUI/GPU 阻断验证

构造包含被阻断节点的 plan:

```json
{
  "plan": {
    "pipeline_id": "should_be_blocked",
    "nodes": [
      {"id": "spm_realign_subject", "backend": "matlab-spm", "depends_on": [], "params": {}}
    ]
  },
  "approval": {
    "approved": true,
    "approved_nodes": ["*"],
    "rejected_nodes": []
  },
  "project_config_path": "examples/project_config_synthetic_smoke.yaml",
  "dry_run": false,
  "persist_audit": true,
  "write_pipeline_yaml": true,
  "confirm_execution": true
}
```

预期: `EXECUTION_POLICY_BLOCKED` 或 `SAFE_EXECUTION_POLICY_BLOCKED`, `executor_called=false`.

## 十、清理

```bash
# 清理 smoke 产物
rm -rf tmp_smoke_synthetic_rawdata/
rm -rf tmp_smoke_dataset_index/
rm -rf outputs/work/reviewed_pipelines/reviewed_synthetic_smoke_*.yaml
rm -rf outputs/reports/audit_records/audit_*.json

# 清理 env
unset MEDIMAGE_ENABLE_REVIEWED_EXECUTION

# 停止后端
# Ctrl+C
```

## 十一、已知限制

- 需要 `numpy` + `nibabel` (`create_synthetic_bids` 依赖)
- 不依赖真实 neuroimaging dataset
- 不依赖 MATLAB/SPM/DPABI/GPU
- `project_config_synthetic_smoke.yaml` 中 `spm_dir`/`dpabi_dir` 为 dummy 路径
- 本 smoke 不进入 CI（executor 创建真实 state 文件，CI 稳定性未验证）
- 如需 CI smoke，可 monkeypatch `run_pipeline` 并仅验证 preflight 路径

## 十二、故障排查

| 症状 | 可能原因 | 解决 |
|------|---------|------|
| `REVIEWED_EXECUTION_DISABLED` | env var 未设置 | `export MEDIMAGE_ENABLE_REVIEWED_EXECUTION=1` |
| `CONFIRMATION_REQUIRED` | `confirm_execution` 未 true | 修改请求 body |
| `PROJECT_CONFIG_INVALID` | config yaml 格式错误 | 检查 YAML 语法 |
| `VALIDATION_FAILED` | node id 不在 tool catalog | 确认 `create_synthetic_bids` / `data_inspection` |
| `SAFE_EXECUTION_POLICY_BLOCKED` | 节点不在 safe allowlist | 只能用 Python-only 节点 |
| `EXECUTION_FAILED` | 缺少 numpy/nibabel | `pip install numpy nibabel` |
| `ModuleNotFoundError: numpy` | CI 缺少依赖 | 仅在本地运行 smoke |

---

## 十三、前端 UI smoke（M5-T019 / M5-T020）

验证前端 Plan Review Console 的 Reviewed Execution 区域。

### 前置条件

```bash
# 1. 启动后端
uvicorn src.backend.app.main:app --host 127.0.0.1 --port 8000

# 2. 启动前端
cd src/frontend && npm run dev
```

### 验证步骤

1. 打开浏览器 → `http://localhost:5173`
2. 导航到 Plan Review Console
3. 在 Goal 输入框输入: `test`
4. 点击 **Generate Plan**
5. 在 Approval Gate 区域填写 approval 信息并点击 **Check Approval Gate**
6. 在 Dry-run 区域点击 **Dry-run Execution Check**
7. 确认 dry-run result 显示 **DRY_RUN_OK**
8. 向下滚动到 **Reviewed Execution** 区域

### 预期行为

| # | 验证项 | 预期 |
|---|--------|------|
| 1 | 按钮文案 | "Execute Reviewed Plan"（不是 Run/Start/Submit/Go） |
| 2 | 按钮默认 disabled | 初始状态灰色，不可点击 |
| 3 | project_config_path 默认值 | `examples/project_config_synthetic_smoke.yaml` |
| 4 | Actor 默认值 | `frontend-user` |
| 5 | 二次确认 checkbox | 默认未勾选 |
| 6 | dry-run 非 DRY_RUN_OK 时 | 显示 "Run Dry-run Execution Check first"，按钮 disabled |
| 7 | dry-run OK + checkbox 未勾选 | 按钮 disabled |
| 8 | dry-run OK + checkbox 勾选 + config 非空 | 按钮 enabled（红色） |
| 9 | config path 为空 | 显示 "Project config path is required" |
| 10 | 点击执行后 | 发送 dry_run=false, confirm_execution=true, persist_audit=true, write_pipeline_yaml=true |
| 11 | 后端 blocked (env var 未开) | 显示 "REVIEWED_EXECUTION_DISABLED"（橙色），不报网络错误 |
| 12 | SPM plan + 执行 | 返回 EXECUTION_POLICY_BLOCKED，按钮不绕过 |
| 13 | 区域标题 | "🚀 Reviewed Execution" |
| 14 | 安全说明 | 包含 "Backend gated execution only" 和 "SPM / DPABI / GUI / GPU nodes remain blocked" |

### 前端不修改后端

前端按钮仅调用现有 `/api/plans/execute-reviewed` endpoint，不设置环境变量，不绕过任何 gate。
