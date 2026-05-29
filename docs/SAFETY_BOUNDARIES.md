# 安全边界 (SAFETY_BOUNDARIES)

本文档定义 MedImage Agent 的所有安全边界。所有开发者、Code Agent、以及 LLM 生成的代码都必须遵守这些边界。违反任何一条边界都视为阻塞性 bug。

---

## 1. rawdata 只读

**规则**：`data/` 目录和任何原始 BIDS 数据**永远只读**。

- 禁止任何代码（Python、MATLAB、Shell）修改 `data/` 下的文件
- 禁止任何 pipeline node 将 rawdata 路径作为 output 目标
- 禁止任何工具删除 rawdata 文件

**实现**：
- 策略层面：`AGENTS.md`、`CLAUDE.md`、本文档明确声明
- 代码层面（计划 M3）：`plan_validator.py` 将在执行前检查所有 output 路径

**违反后果**：阻塞性 bug，必须立即修复。

---

## 2. Approval Gate

**规则**：所有会写文件、运行 MATLAB/SPM/DPABI、或修改 derivatives 的操作**必须经过 approval gate**。

### 2.1 Plan 级审批

- 整体 pipeline 执行需要用户确认
- 通过 `agent_runtime.py` → `run_orchestrator_execute(approved=true)` 控制
- API 端点 `POST /api/agent/execute` 要求 `approved=true`，否则返回 403

### 2.2 Step 级审批

- `requires_confirmation=true` 的工具需要二次确认
- 通过 `tool_registry.py` → `assert_tool_allowed()` 控制
- 未审批的工具调用会抛出 `ToolExecutionError`

### 2.3 默认安全

- 所有 `requires_confirmation` 的工具默认 `approved=false`
- 未明确审批的操作**安全失败**（fail closed），不会静默执行

**实现位置**：
- `src/backend/app/runtime/agent_runtime.py` — plan 级审批
- `src/backend/app/runtime/tool_registry.py` — step 级审批
- `src/backend/app/api/routes.py` — API 层审批检查

---

## 3. 允许写入目录（白名单）

**规则**：所有文件写入操作限制在以下白名单目录：

| 目录 | 用途 | 示例内容 |
|------|------|---------|
| `outputs/work/` | 运行时状态、中间结果 | `states/<run_id>/`、`agent_runs/` |
| `outputs/logs/` | 执行日志 | `pipeline_*.log`、`matlab_*.log` |
| `outputs/derivatives/` | 衍生数据（处理结果） | `spm_smooth/`、`alff/`、`reho/` |
| `outputs/reports/` | 报告和 QC 输出 | `dataset_evaluation/`、`motion_qc/` |
| `outputs/exports/` | 导出包 | `rsfmri_report_package/` |

**禁止写入的目录**：
- `data/` — rawdata（只读）
- `src/` — 源代码
- `examples/` — 示例配置
- `tests/` — 测试文件
- `docs/` — 文档
- 任何系统目录（`/etc/`、`/usr/`、`C:\Windows\` 等）

**实现**：
- `src/backend/app/runtime/path_safety.py` — 路径解析和目录遍历防护
- `src/backend/app/runtime/tool_registry.py` — 每个工具的 `allowed_write_paths`

---

## 4. LLM advice-only / planning-only

**规则**：LLM（包括 Claude、GPT 等）只能做**规划、建议、解释**，不能：

- 绕过 Pipeline Executor 直接调用工具
- 直接修改文件系统
- 直接控制 MATLAB/SPM/DPABI 的执行
- 在运行时做出未经人工审批的决策

**允许的 LLM 操作**：
- 生成 pipeline plan（结构化 YAML）
- 提供参数建议
- 解释 QC 报告
- 诊断错误并提供修复建议
- 回答文档问题

**实现**：
- 架构层面：Agent Runtime 的 Plan-then-Execute 模式
- 代码层面：所有 LLM 输出经过 Plan Validator 和 Approval Gate
- `src/backend/app/advisor/advisor_safety.py` — Advisor 安全边界控制

---

## 5. GUI Agent 限制

**规则**：GUI Agent 只能作为特殊的 node runner 接入 pipeline，不能接管整个系统控制流。

**约束**：
- GUI Agent 由 Pipeline Executor 在特定节点调用
- GUI Agent 不能主动触发其他 pipeline 节点
- GUI Agent 不能绕过 approval gate
- GUI Agent 不能直接访问 rawdata 以外的敏感目录
- GUI Agent 的会话必须有超时机制

**实现位置**：
- `src/backend/app/api/gui_agent_routes.py` — GUI Agent API
- `src/backend/app/runtime/pipeline_executor.py` — 未来集成 GUI Agent Node 暂停/继续

---

## 6. MATLAB / SPM / DPABI 执行限制

**规则**：MATLAB/SPM/DPABI 的执行受严格控制。

### 6.1 环境变量门控

- `MEDIMAGE_MATLAB_ENABLED` 环境变量控制 MATLAB 是否可用
- 默认 `false`，MATLAB 调用被阻止
- 即使 `true`，仍需 `approved=true`

### 6.2 MATLAB 执行约束

- MATLAB 脚本只从 `matlab/` 目录加载
- MATLAB 工作目录限制在 `outputs/work/` 和 `outputs/logs/`
- MATLAB 不能访问 `data/` 以写入模式
- MATLAB 输入文件只能是 rawdata 或上游节点的 derivatives 输出

### 6.3 DPABI 执行约束

- DPABI 函数禁止运行 `DPARSF_run`、`DPARSFA_run`、DPABI GUI
- 只允许单函数 wrapper 模式
- DPABI backend 是 contract-only：生成 spec 文件但不执行（除非明确审批）

**实现位置**：
- `src/backend/app/tools/matlab_runner.py`
- `src/backend/app/tools/dpabi_runner.py`
- `src/backend/app/tools/dpabi_safety.py`（如有）

---

## 7. API Key / Secret 管理

**规则**：不允许把 API key、绝对私有路径、实验数据路径写死进代码或文档。

**要求**：
- API key 通过环境变量注入（如 `OPENAI_API_KEY`、`ANTHROPIC_API_KEY`）
- 私有路径通过项目配置文件（YAML）或环境变量指定（如 `MEDIMAGE_DATA_ROOT`）
- 不允许在代码中使用绝对路径引用外部数据
- `.env` 文件在 `.gitignore` 中

**检查**：任何 PR 包含 API key 或绝对路径的硬编码，直接拒绝。

---

## 8. Clinical Disclaimer（临床免责声明）

**规则**：本项目是研究工程平台，不用于临床诊断或临床决策。

**所有对外接口必须包含**：
- 本项目不提供临床诊断功能
- 所有输出是工程验证级别，不是临床级别
- 不提供敏感度/特异度等临床指标
- 不输出患者级别的诊断报告

**文档声明位置**：
- `README.md` — Current Status & Boundaries 部分
- `docs/PROJECT_GOAL.md` — 非目标部分
- `docs/safety_and_limitations.md` — Limitations 部分

---

## 9. Path Safety 机制

**规则**：所有通过 API 的文件访问经过路径安全代理。

**实现**：`src/backend/app/runtime/path_safety.py`

- 所有路径强制归一化（resolve）
- 禁止目录遍历攻击（`../` 逃逸）
- 只允许访问白名单目录：`examples/`、`work/`、`logs/`、`reports/`、`memory/`、`specs/`
- 只允许读取白名单后缀：`.json`、`.yaml`、`.yml`、`.md`、`.txt`、`.csv`、`.html`、`.log`
- 系统敏感路径（`/etc/`、`/proc/`、`C:\Windows\` 等）不可访问

---

## 10. Tool Permission Grading

**规则**：所有工具在注册到 `tool_registry.py` 时声明权限等级。

| 权限标志 | 含义 |
|----------|------|
| `read_only` | 只读操作（如数据检查、报告生成） |
| `writes_files` | 写文件操作（如保存中间结果） |
| `destructive` | 破坏性操作（如删除、覆盖），自动触发 Approval Gate |
| `requires_confirmation` | 需要审批（`approved=true`），未审批则安全失败 |
| `parallel_safe` | 可以并行执行 |

**当前状态**：`TOOL_REGISTRY` 目前只定义了 `pipeline.plan` 和 `pipeline.execute` 两个工具。M2 计划将所有 30+ 处理工具注册进来。详见 `docs/TASK_BACKLOG.md` 的 T-0010 和 T-0011。

---

## 11. 前端隔离

**规则**：前端只能通过后端 HTTP API 与系统交互，不能直接操作本地文件系统。

**约束**：
- 前端所有文件读写通过 `/api/files/read`、`/api/logs/read` 等代理端点
- 前端不能调用 `fs` 模块（Node.js）直接读写文件
- 前端不能直接执行 MATLAB/SPM 命令
- Electron 桌面应用的主进程文件操作受同样限制（通过 `preload.cjs` 桥接）

---

*最后更新：2025-07-18*
