# Safe Reviewed Execution Design

本文档定义从 reviewed plan 到真实 pipeline execution 的安全实现路径。

**状态**: 设计阶段 (M5-T012c)，尚未实现。

## 一、真实执行硬条件

未来 `dry_run=false` 真实执行必须**同时满足**以下所有条件：

| # | 条件 | 不满足时 |
|---|------|---------|
| 1 | `dry_run == false` | `DRY_RUN_ONLY` |
| 2 | `confirm_execution == true` | `EXECUTION_NOT_CONFIRMED` |
| 3 | `persist_audit == true` | `AUDIT_REQUIRED` |
| 4 | `MEDIMAGE_ENABLE_REVIEWED_EXECUTION == "1"` | `REVIEWED_EXECUTION_DISABLED` |
| 5 | `validate_plan(plan).ok == true` | `VALIDATION_FAILED` |
| 6 | `check_approval_gate(...).execution_allowed == true` | `APPROVAL_GATE_BLOCKED` |
| 7 | `adapt_reviewed_plan(plan).ok == true` | `PLAN_ADAPTER_FAILED` |
| 8 | policy 无 blocked nodes | `EXECUTION_POLICY_BLOCKED` |
| 9 | `manual_required_nodes == []` | `MANUAL_REQUIRED_BLOCKED` |
| 10 | `unknown_nodes == []` | `UNKNOWN_NODES_BLOCKED` |
| 11 | `project_config_path` 存在且 ProjectSettings 校验通过 | `PROJECT_CONFIG_INVALID` |
| 12 | `rawdata_readonly == true` | `RAWDATA_SAFETY_VIOLATION` |
| 13 | audit record 写入成功 | `AUDIT_WRITE_FAILED` |
| 14 | pipeline YAML 写入安全目录成功 | `PIPELINE_WRITE_FAILED` |

## 二、环境变量

```bash
MEDIMAGE_ENABLE_REVIEWED_EXECUTION=1
```

- 默认 `0` / unset → 所有 `dry_run=false` 请求返回 `REVIEWED_EXECUTION_DISABLED`
- 不设置时不调用任何 executor
- 不在代码中硬编码默认值以外的执行路径

## 三、confirm_execution

请求必须包含：

```json
{ "confirm_execution": true }
```

- 前端必须二次确认后才设置为 true
- 后端必须校验此字段
- `confirm_execution` 不为 true → `EXECUTION_NOT_CONFIRMED`

## 四、persist_audit 强制

真实执行时 `persist_audit` 必须为 true：

- 前端不可选（后端强制覆盖）
- audit record 写入成功前不调用 executor
- audit 写入失败 → `AUDIT_WRITE_FAILED`

## 五、Pipeline YAML 写入策略

### 为什么需要

`run_pipeline(project_config_path, pipeline_path)` 需要 YAML 文件路径。

### 转换流程

```
reviewed plan dict
  → plan_adapter.reviewed_plan_to_pipeline_dict()
  → pipeline dict
  → YAML 文件（atomic write）
  → run_pipeline(project_config_path, pipeline_yaml_path)
```

### 写入规则

| 规则 | 值 |
|------|-----|
| 目录 | `outputs/work/reviewed_pipelines/` |
| 文件名 | `{plan_hash[:12]}_{timestamp}.yaml` |
| 写入方式 | atomic（`.tmp` + `replace`） |
| 不允许 | 用户指定路径、覆盖已有文件、写 rawdata |

## 六、第一版 Node Allowlist

| 节点 | 说明 |
|------|------|
| `create_synthetic_bids` | 合成数据 |
| `data_inspection` | 数据检查 |
| `environment_check` | 环境检查 |
| Python QC/report 节点 | motion_qc, slice_timing_qc 等 |
| Python 后处理 | nuisance_regression, temporal_filtering, alff, reho, fc |

### GPU 节点

第一版建议**继续阻断**，避免 CuPy 环境不一致。后续通过独立环境变量开启。

### 第一版 Blocklist

| 类别 | 节点 |
|------|------|
| SPM | `spm_*` |
| DPABI execution | `dpabi_subject_*`, `dpabi_sandbox_*`, `dpabi_single_function_*` |
| GUI | `gui_*`, `manual_required=true` |
| Unknown | 不在 NODE_REGISTRY 中的 id |
| Uncataloged | fallback metadata 节点 |

## 七、Rawdata Readonly

- `project_config_path` → `ProjectSettings.from_yaml()` → `safety.rawdata_readonly`
- 如果 `rawdata_readonly != True` → 阻断执行
- 不信任前端传入的任何安全声明

## 八、ProjectConfig 校验

- `project_config_path` 必须存在
- 必须通过 `ProjectSettings.from_yaml()` 校验
- 不通过 → `PROJECT_CONFIG_INVALID`

## 九、API 状态机

完整状态枚举（dry_run=false）：

```
DRY_RUN_ONLY                     ← dry_run != true
REVIEWED_EXECUTION_DISABLED      ← env var 未开启
EXECUTION_NOT_CONFIRMED          ← confirm_execution != true
AUDIT_REQUIRED                   ← persist_audit != true
VALIDATION_FAILED                ← validate_plan 不通过
APPROVAL_GATE_BLOCKED            ← approval gate 不通过
PLAN_ADAPTER_FAILED              ← plan_adapter 失败
EXECUTION_POLICY_BLOCKED         ← policy 有 blocked nodes
MANUAL_REQUIRED_BLOCKED          ← manual_required_nodes 非空
UNKNOWN_NODES_BLOCKED            ← unknown_nodes 非空
PROJECT_CONFIG_INVALID           ← project_config 无效
RAWDATA_SAFETY_VIOLATION         ← rawdata_readonly != true
AUDIT_WRITE_FAILED               ← audit record 写入失败
PIPELINE_WRITE_FAILED            ← pipeline YAML 写入失败
EXECUTION_SUBMITTED              ← run_pipeline() 调用成功
EXECUTION_FAILED                 ← run_pipeline() 抛异常
```

## 十、Audit 强制策略

| 事件 | audit 写入时机 |
|------|--------------|
| `execution_requested` | 接收请求后、校验前（可选） |
| `execution_blocked` | 任何阻断条件命中时 |
| `execution_submitted` | `run_pipeline()` 返回后 |
| `execution_failed` | `run_pipeline()` 抛异常后 |
| `execution_completed` | pipeline status SUCCESS/PARTIAL |

Audit 必须包含：

- plan_hash / validation_hash / approval_hash
- adapter/policy summary
- pipeline_yaml_path
- run_id
- executor_called
- status
- actor / source

## 十一、前端执行按钮策略

| 规则 | 说明 |
|------|------|
| 当前 | 无执行按钮 |
| 未来默认 | hidden / disabled |
| 可用条件 | 最近 dry-run status == DRY_RUN_OK |
| 文案 | "Execute Reviewed Plan" |
| 二次确认 | 弹出对话框 + confirm_execution=true |
| 禁止文案 | "Run" / "Start" / "Submit" |
| 阻断提示 | SPM/DPABI/GUI 节点显示阻止原因 |

## 十二、代码修改预估

| 文件 | 修改 |
|------|------|
| `execute_reviewed_routes.py` | 增加 dry_run=false 分支 + 状态机 |
| `plan_adapter.py` | pipeline dict → YAML 写入函数 |
| 无需新增文件 | — |

预计 ~100 行新增代码，~50 行测试。

## 十三、建议实现步骤

| Phase | 内容 |
|-------|------|
| M5-T012d | execute_reviewed 真实执行路径（dry_run=false 分支） |
| M5-T012e | 前端 safe execution 按钮（disabled 默认） |
| 后续 | SPM/DPABI 逐步开放 |
