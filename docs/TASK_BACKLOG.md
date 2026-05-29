# 任务待办池 (TASK_BACKLOG)

每个任务包含：task_id、title、priority、scope、allowed_files、forbidden_changes、acceptance_criteria、test_commands、depends_on。

优先级定义：
- **P0**：阻塞性，必须立即完成
- **P1**：高优先级，当前里程碑的关键路径
- **P2**：中优先级，当前里程碑的辅助任务
- **P3**：低优先级，后续里程碑的预备任务

---

## M1 任务：稳定当前基础设施

### T-0001：修复文档路径不一致

- **task_id**: T-0001
- **title**: 修复 README.md 中的旧路径引用
- **priority**: P0
- **scope**: 仅修复文档中的路径引用，不修改业务代码
- **allowed_files**:
  - `README.md`
- **forbidden_changes**:
  - 不修改 `src/` 下的任何代码
  - 不修改 `examples/*.yaml`
  - 不修改 `tests/`
- **acceptance_criteria**:
  - README.md 中的 `cd frontend` 改为 `cd src/frontend`
  - `uvicorn backend.app.main:app` 改为 `uvicorn src.backend.app.main:app`
  - `python -m backend.app.tools.*` 改为 `python -m src.backend.app.tools.*`
  - 项目结构树反映实际文件布局（移除不存在的 `safety/` 目录，补充 `advisor/`、`schemas/`）
- **test_commands**:
  - 无（纯文档修改）
- **status**: ✅ 已完成（2025-07-18）

---

### T-0002：修复 release_readiness 与项目结构一致性

- **task_id**: T-0002
- **title**: 修复 release_readiness.py 中的路径/endpoint 一致性问题，新增 M1 文档检查
- **priority**: P1
- **scope**: release_readiness.py 和 developer_guide.md 的路径修正
- **allowed_files**:
  - `src/backend/app/tools/release_readiness.py`
  - `tests/unit/test_release_readiness.py`
  - `docs/developer_guide.md`
  - `docs/CURRENT_STATE.md`
  - `docs/NEXT_ACTIONS.md`
  - `docs/DEV_LOG/`
  - `docs/TASK_BACKLOG.md`
- **forbidden_changes**:
  - 不修改 `src/backend/app/runtime/` 核心逻辑
  - 不修改 `src/backend/app/api/routes.py`
- **acceptance_criteria**:
  - `/api/rsfmri/report-validator` → `/api/rsfmri/report-validation`（bug 修复）
  - 新增 M1 文档检查（10 个文档 + 内容检查）
  - `outputs/exports/rsfmri_report_package/` 缺失时使用 WARNING 而非 FAIL
  - 24 个单元测试全部通过
  - release_readiness 全 PASS（78 checks）
- **test_commands**:
  - `pytest tests/unit/test_release_readiness.py -v`
- **status**: ✅ 已完成（2026-05-29）

---

### T-0003：新增 ProjectSettings 统一配置层

- **task_id**: T-0003
- **title**: 新增 ProjectSettings，统一 project_config 读取逻辑
- **priority**: P0
- **scope**: 新增配置模块和测试，不改动现有业务代码
- **allowed_files**:
  - `src/backend/app/config/__init__.py`
  - `src/backend/app/config/settings.py`
  - `tests/unit/test_project_settings.py`
  - `docs/CURRENT_STATE.md`
  - `docs/NEXT_ACTIONS.md`
  - `docs/TASK_BACKLOG.md`
  - `docs/DEV_LOG/`
- **forbidden_changes**:
  - 不修改 `src/backend/app/runtime/` 核心执行逻辑
  - 不修改 `src/backend/app/api/routes.py`
  - 不修改 `examples/*.yaml`
  - 不替换现有配置读取代码
- **acceptance_criteria**:
  - `ProjectSettings.from_yaml()` 从现有 YAML 正常加载
  - 新增 14 个单元测试全部通过
  - 关键字段缺失时抛出 `ValueError`
  - 文件不存在时抛出 `FileNotFoundError`
  - YAML 格式错误时抛出 `ValueError`
  - 可选字段使用安全默认值
  - `pytest` 全量通过（209 passed, 4 skipped）
- **test_commands**:
  - `pytest tests/unit/test_project_settings.py -v`
  - `pytest`（全量回归）
- **status**: ✅ 已完成（2026-05-29）

---

### T-0004：验证并统一前后端启动方式

- **task_id**: T-0004
- **title**: 统一前后端端口为 8000，验证 app 导入和前端 build
- **priority**: P0
- **scope**: 端口统一 + 验证，不改动业务逻辑
- **allowed_files**:
  - `src/frontend/package.json`
  - `src/frontend/src/api.ts`
  - `src/frontend/src/App.tsx`
  - `src/frontend/src/lib/api/client.ts`
  - `src/frontend/src/components/workflow/DataUploadStep.tsx`
  - `src/frontend/src/hooks/useAppState.ts`
  - `src/frontend/electron/main.cjs`
  - `src/frontend/electron/preload.cjs`
  - `src/backend/app/core/config.py`
  - `tests/unit/test_backend_app_import.py`
  - 文档更新
- **forbidden_changes**:
  - 不修改核心执行逻辑（routes/pipeline_executor/agent_runtime/node_registry）
  - 不删除环境变量覆盖能力
- **acceptance_criteria**:
  - 所有默认端口统一为 8000（11 处引用全部修正）
  - `from src.backend.app.main import app` 可导入
  - `npm run build` 成功
  - `pytest` 212 passed, 4 skipped
  - `grep 8765` 源代码无残留（除 dist/ 和 __pycache__ 构建产物）
- **test_commands**:
  - `pytest tests/unit/test_backend_app_import.py -v`
  - `pytest tests/unit/test_project_settings.py -v`
  - `pytest tests/unit/test_release_readiness.py -v`
  - `pytest`
- **status**: ✅ 已完成（2026-05-29）

---

### T-0005a：agent_plan 接入 ProjectSettings 校验

- **task_id**: T-0005a
- **title**: 将 agent_plan.py 的 _load_project_config 接入 ProjectSettings 结构校验
- **priority**: P1
- **scope**: agent_plan.py + 测试，保持 dict 兼容
- **allowed_files**:
  - `src/backend/app/runtime/agent_plan.py`
  - `tests/unit/test_agent_plan_project_settings.py`
  - 文档更新
- **forbidden_changes**:
  - 不修改 hook_manager、scheduler、agent_runtime 接口
  - 不修改 pipeline_executor、routes、node_registry
  - 不修改 ProjectSettings
- **acceptance_criteria**:
  - `_load_project_config()` 在返回 dict 前调用 `ProjectSettings.from_yaml()` 校验
  - 缺失关键字段在 PLAN 阶段失败（而非后续执行阶段 KeyError）
  - `_load_project_config()` 仍返回 dict
  - 12 个新增测试全部通过
  - `pytest` 全量 224 passed, 4 skipped
- **test_commands**:
  - `pytest tests/unit/test_agent_plan_project_settings.py -v`
  - `pytest tests/integration/test_agent_plan.py -v`
  - `pytest`
- **status**: ✅ 已完成（2026-05-29）

---

### T-0005b：pipeline_executor 接入 ProjectSettings 校验

- **task_id**: T-0005b
- **title**: 将 pipeline_executor.py 的 load_project_config 接入 ProjectSettings 结构校验
- **priority**: P1
- **scope**: pipeline_executor.py + 测试，保持 dict 兼容
- **allowed_files**:
  - `src/backend/app/runtime/pipeline_executor.py`
  - `tests/unit/test_pipeline_executor_project_settings.py`
  - 文档更新
- **forbidden_changes**:
  - 不修改 run_pipeline() 主体逻辑、scheduler、node runner、subject-level 并行
  - 不修改 agent_runtime、node_registry、routes、tools
  - 不修改 ProjectSettings
- **acceptance_criteria**:
  - `load_project_config()` 在返回 dict 前调用 `ProjectSettings.from_yaml()` 校验
  - `load_project_config()` 仍返回 dict
  - bad config → `run_pipeline()` 返回 `status == "INVALID"`
  - 10 个新增测试全部通过
  - `pytest` 全量 234 passed, 4 skipped
- **test_commands**:
  - `pytest tests/unit/test_pipeline_executor_project_settings.py -v`
  - `pytest tests/unit/test_agent_plan_project_settings.py -v`
  - `pytest`
- **status**: ✅ 已完成（2026-05-29）

---

### T-0005c：routes API 层接入 ProjectSettings 校验

- **task_id**: T-0005c
- **title**: 将 routes.py 的 _load_project_config 接入 ProjectSettings 结构校验
- **priority**: P1
- **scope**: routes.py _load_project_config + 测试，保持 dict 兼容
- **allowed_files**:
  - `src/backend/app/api/routes.py`
  - `tests/unit/test_routes_project_settings.py`
  - 文档更新
- **forbidden_changes**:
  - 不修改任何 endpoint 业务逻辑、路由、请求模型、返回结构
  - 不修改 agent_plan、pipeline_executor、agent_runtime、node_registry
  - 不修改 ProjectSettings
- **acceptance_criteria**:
  - `_load_project_config()` 在返回 dict 前调用 `ProjectSettings.from_yaml()` 校验
  - ValueError/FileNotFoundError 包装为 HTTPException(400)
  - `_load_project_config()` 仍返回 dict
  - 8 个新增测试全部通过
  - `pytest` 全量 242 passed, 4 skipped
- **test_commands**:
  - `pytest tests/unit/test_routes_project_settings.py -v`
  - `pytest`
- **status**: ✅ 已完成（2026-05-29）

---

### T-0006：新增 CI / smoke tests

- **task_id**: T-0006
- **title**: 建立 GitHub Actions CI，固化 pytest + frontend build
- **priority**: P0
- **scope**: CI workflow + 文档更新，不改业务代码
- **allowed_files**:
  - `.github/workflows/ci.yml`
  - `README.md`、`AGENTS.md`、`CLAUDE.md`
  - `docs/DEVELOPMENT_WORKFLOW.md`
  - 其他文档
- **forbidden_changes**:
  - 不修改 runtime/routes/tools/frontend 业务代码
  - 不修改 examples YAML
- **acceptance_criteria**:
  - `.github/workflows/ci.yml` 存在
  - backend job：Python 3.11 + pytest
  - frontend job：Node 20 + npm ci + npm run build
  - CI 不依赖 MATLAB/SPM/DPABI/GPU
  - 本地 `pytest` 242 passed
  - 本地 `npm run build` 成功
- **test_commands**:
  - `pytest --tb=short`
  - `cd src/frontend && npm run build`
- **status**: ✅ 已完成（2026-05-29）

---

### T-0008：修复 CI 存量测试失败（error_classifier + background_task_manager）

- **task_id**: T-0008
- **title**: 修复 Linux CI 上 8 个存量测试失败
- **priority**: P1
- **scope**: error_classifier.py KB 路径 + background_task_manager 原子写入
- **allowed_files**:
  - `src/backend/app/tools/error_classifier.py`
  - `src/backend/app/tools/error_kb_validator.py`
  - `src/backend/app/runtime/background_task_manager.py`
- **forbidden_changes**:
  - 不修改 KB 文件内容
  - 不用 skip/xfail
- **acceptance_criteria**:
  - CI 上 8 个测试全部 PASS
  - 本地 242 passed 保持
- **test_commands**:
  - `pytest tests/unit/test_error_classifier.py -v`
  - `pytest tests/unit/test_background_task_manager.py -v`
- **status**: ✅ 已完成（2026-05-29）

---

### T-0008b：ERROR_KB.yaml 完整内容提交

- **task_id**: T-0008b
- **title**: 提交完整 ERROR_KB.yaml（v0.2.0, 15 categories）
- **priority**: P0
- **scope**: 替换 Git 中 v0.1.0 空占位符为本地完整 KB
- **allowed_files**:
  - `memory/global/ERROR_KB.yaml`
- **acceptance_criteria**:
  - CI error_classifier 8 tests 全 PASS
  - CI 全绿
- **status**: ✅ 已完成（2026-05-29）

---

### T-0005：实现 audit_logger 或从文档中移除引用

- **task_id**: T-0005
- **title**: 实现 audit_logger.py 或更新文档移除不存在的引用
- **priority**: P1
- **scope**: 新建文件或修改文档
- **allowed_files**:
  - `src/backend/app/runtime/audit_logger.py`（如选择实现）
  - `README.md`、`docs/ARCHITECTURE.md`、`docs/SAFETY_BOUNDARIES.md`
- **forbidden_changes**:
  - 不修改已有的运行时代码
- **acceptance_criteria**:
  - 选项 A：实现 `audit_logger.py`，记录所有工具调用和文件操作
  - 选项 B：从所有文档中移除 `audit_logger.py` 的引用，标记为 "planned"
- **test_commands**:
  - `pytest tests/unit/test_audit_logger.py`（如选择 A）
- **status**: 待决策（建议先 B 后 A，在 M2 中实现）

---

## M2 任务：拆分 Node Registry，建立 Tool Catalog

### T-0010：设计 Tool Catalog schema

- **task_id**: T-0010
- **title**: 设计 tool_registry.py 的完整 schema，包含所有处理工具的权限定义
- **priority**: P1
- **scope**: 设计和文档，暂不实现
- **allowed_files**:
  - `docs/ARCHITECTURE.md`（Tool Catalog 部分）
  - `specs/`（新增 spec 文件）
- **forbidden_changes**:
  - 不修改 `src/` 代码
- **acceptance_criteria**:
  - 所有处理工具（30+）的权限定义文档
  - 每个工具的 read_only、writes_files、destructive、requires_confirmation、parallel_safe 标志
  - 每个工具的 allowed_read_paths、allowed_write_paths
  - 与现有 `tool_registry.py` 格式兼容
- **test_commands**:
  - 无（设计阶段）
- **status**: 待执行
- **depends_on**: T-0003

---

### T-0011：将现有工具注册到 tool_registry.py

- **task_id**: T-0011
- **title**: 在 tool_registry.py 中注册所有处理工具（30+）
- **priority**: P1
- **scope**: 扩展 tool_registry.py，不改动 node_registry.py 的映射逻辑
- **allowed_files**:
  - `src/backend/app/runtime/tool_registry.py`
  - `tests/unit/test_tool_registry.py`（如需要扩展）
- **forbidden_changes**:
  - 不修改 `node_registry.py` 的 runner 函数
  - 不修改 `pipeline_executor.py` 的核心执行逻辑
- **acceptance_criteria**:
  - `TOOL_REGISTRY` 包含所有处理工具
  - 每个工具正确声明权限
  - `assert_tool_allowed()` 对新工具生效
  - 已有 pipeline 执行行为不变
- **test_commands**:
  - `pytest tests/unit/test_tool_registry.py -v`
  - `pytest`（全量回归）
- **status**: 待执行
- **depends_on**: T-0010

---

### T-0012：在 pipeline_executor 中集成权限检查

- **task_id**: T-0012
- **title**: 在 run_pipeline() 的节点执行前添加 assert_tool_allowed 调用
- **priority**: P1
- **scope**: 修改 pipeline_executor.py 的执行流程，在 get_node_runner 前检查权限
- **allowed_files**:
  - `src/backend/app/runtime/pipeline_executor.py`
  - `tests/unit/`（新增或扩展）
- **forbidden_changes**:
  - 不修改 node runner 内部逻辑
- **acceptance_criteria**:
  - 每个节点执行前调用 `assert_tool_allowed(node.id, approved=...)`
  - 未授权的 `requires_confirmation` 工具被拒绝
  - 所有已有测试通过
- **test_commands**:
  - `pytest tests/unit/ -v`
  - `pytest tests/integration/ -v`
- **status**: 待执行
- **depends_on**: T-0011

---

### T-0013：实现 audit_logger.py

- **task_id**: T-0013
- **title**: 实现审计日志模块，记录所有工具调用和文件操作
- **priority**: P2
- **scope**: 新建 audit_logger.py 并集成到 pipeline_executor
- **allowed_files**:
  - `src/backend/app/runtime/audit_logger.py`（新建）
  - `src/backend/app/runtime/pipeline_executor.py`（添加日志调用）
  - `tests/unit/test_audit_logger.py`（新建）
- **forbidden_changes**:
  - 不修改现有 node runner 内部逻辑
- **acceptance_criteria**:
  - 每次工具调用记录：时间戳、run_id、node_id、tool、参数、结果摘要
  - 每次文件写入记录：路径、大小、校验和
  - 审计日志本身不可变（append-only）
  - 日志存储在 `outputs/logs/audit/`
- **test_commands**:
  - `pytest tests/unit/test_audit_logger.py -v`
- **status**: 待执行
- **depends_on**: T-0012

---

## M3 任务：实现 Plan Validator

### T-0020：实现安全边界校验

- **task_id**: T-0020
- **title**: 在 Plan Validator 中添加安全边界校验
- **priority**: P1
- **scope**: 在 plan 执行前校验是否尝试写入 rawdata 或越权目录
- **allowed_files**:
  - `src/backend/app/schemas/plan_validator.py`（新建）
  - `src/backend/app/runtime/agent_runtime.py`（集成调用）
  - `tests/unit/test_plan_validator.py`（新建）
- **forbidden_changes**:
  - 不修改 `pipeline_executor.py` 核心执行逻辑
- **acceptance_criteria**:
  - 检测 pipeline YAML 中任何节点的 output 路径是否指向 `data/`
  - 检测 pipeline YAML 中任何节点的 input 路径是否试图写入 rawdata
  - 校验失败返回结构化错误列表
  - `agent_runtime.py` 在 `run_pipeline` 前调用 validator
- **test_commands**:
  - `pytest tests/unit/test_plan_validator.py -v`
  - `pytest tests/unit/test_pipeline_schema.py -v`
- **status**: 待执行
- **depends_on**: T-0003, T-0012

---

### T-0021：实现参数合法性校验

- **task_id**: T-0021
- **title**: 校验 pipeline YAML 中每个节点的 params 参数范围和类型
- **priority**: P2
- **scope**: 扩展 plan_validator.py
- **allowed_files**:
  - `src/backend/app/schemas/plan_validator.py`
  - `src/backend/app/schemas/pipeline_schema.py`（可能需要添加参数约束定义）
  - `tests/unit/test_plan_validator.py`
- **forbidden_changes**:
  - 不修改 node runner 的参数处理逻辑
- **acceptance_criteria**:
  - FWHM 值范围校验（如 [2, 12] mm）
  - TR 值正值校验
  - FD threshold 范围校验
  - GPU mode 枚举校验（prefer/require/off）
  - 数值类型校验（int、float、list of numbers）
- **test_commands**:
  - `pytest tests/unit/test_plan_validator.py -v -k test_param`
- **status**: 待执行
- **depends_on**: T-0020

---

### T-0022：实现 backend 可用性校验

- **task_id**: T-0022
- **title**: 校验 pipeline 中引用的 backend 在当前环境中是否可用
- **priority**: P2
- **scope**: 扩展 plan_validator.py，检测 MATLAB、GPU、Python backend 可用性
- **allowed_files**:
  - `src/backend/app/schemas/plan_validator.py`
  - `tests/unit/test_plan_validator.py`
- **forbidden_changes**:
  - 不修改 node runner
- **acceptance_criteria**:
  - 如果 pipeline 包含 matlab-spm 节点但 `MEDIMAGE_MATLAB_ENABLED != true`，发出警告
  - 如果 pipeline 包含 `gpu_supported=true` 且 `gpu_mode=require` 但 GPU 不可用，校验失败
  - 警告/错误信息包含具体节点 ID 和原因
- **test_commands**:
  - `pytest tests/unit/test_plan_validator.py -v -k test_backend`
- **status**: 待执行
- **depends_on**: T-0020

---

## M4 任务：实现 LLM Planner MVP

### T-0030：设计 LLM Planner prompt 和 tool catalog 注入

- **task_id**: T-0030
- **title**: 设计 LLM Planner 的系统 prompt，包含 tool catalog 注入和输出格式约束
- **priority**: P2
- **scope**: 设计和文档
- **allowed_files**:
  - `specs/llm_planner_design.md`（新建）
  - `docs/ARCHITECTURE.md`（LLM Planner 部分）
- **forbidden_changes**:
  - 不修改 `src/` 代码
- **acceptance_criteria**:
  - Prompt 模板包含完整的 tool catalog（节点列表 + 参数说明）
  - 输出格式为严格的 pipeline YAML（通过 schema 校验）
  - 包含 few-shot 示例（至少 3 个典型场景）
  - 安全约束嵌入 prompt（不能写入 rawdata、需要 approval 的操作标记）
- **test_commands**:
  - 无（设计阶段）
- **status**: 待执行
- **depends_on**: T-0011

---

### T-0031：实现 planner_llm.py

- **task_id**: T-0031
- **title**: 实现 LLM Planner 核心模块
- **priority**: P2
- **scope**: 新建模块，集成到 advisor
- **allowed_files**:
  - `src/backend/app/advisor/planner_llm.py`（新建）
  - `src/backend/app/api/planner_routes.py`（扩展端点）
  - `tests/unit/test_planner_llm.py`（新建）
- **forbidden_changes**:
  - LLM 不能直接调用工具——只能输出 plan
- **acceptance_criteria**:
  - 输入：自然语言目标字符串
  - 输出：合法的 pipeline YAML
  - 生成的 YAML 通过 pipeline_schema 校验
  - API 端点 `POST /api/planner/generate-plan` 返回 YAML
  - LLM 调用失败时返回友好错误信息
- **test_commands**:
  - `pytest tests/unit/test_planner_llm.py -v`
  - 手动验证生成的 YAML 可通过 `load_pipeline_yaml()`
- **status**: 待执行
- **depends_on**: T-0030, T-0020

---

## M5 任务：接入 GUI Manual Node

### T-0040：实现 NIfTI 图像渲染组件

- **task_id**: T-0040
- **title**: 在前端实现基于 Canvas/WebGL 的 NIfTI 图像渲染组件
- **priority**: P3
- **scope**: 前端组件，纯展示和交互
- **allowed_files**:
  - `src/frontend/src/components/NiftiViewer.tsx`（新建）
  - `src/frontend/package.json`（可能需要添加依赖）
- **forbidden_changes**:
  - 不修改后端代码
- **acceptance_criteria**:
  - 支持加载 NIfTI 文件（通过后端 API 代理）
  - 支持三视图（轴向/冠状/矢状）
  - 支持窗宽窗位调节
  - 支持鼠标滚轮切换切片
- **test_commands**:
  - `cd src/frontend && npm run typecheck`
  - 手动验证组件渲染正常
- **status**: 待执行
- **depends_on**: T-0004

---

### T-0041：实现 GUI Agent Provider（非 Mock）

- **task_id**: T-0041
- **title**: 实现真正的 GUI Agent Provider，替换 mock
- **priority**: P3
- **scope**: 后端 provider + 前端交互
- **allowed_files**:
  - `src/backend/app/tools/gui_agent_provider.py`（新建或扩展）
  - `src/backend/app/api/gui_agent_routes.py`
  - `src/frontend/src/components/`（新增标注交互组件）
- **forbidden_changes**:
  - GUI Agent 不能绕过 Pipeline Executor 直接操作文件
  - 不能访问 rawdata 以外的目录
- **acceptance_criteria**:
  - AC-PC 定位：用户在图像上点击两个点，坐标写回 pipeline state
  - 标注结果持久化（不易丢失）
  - 超时处理：如果用户长时间未操作，pipeline 可安全超时
- **test_commands**:
  - `pytest tests/unit/test_gui_agent_runtime.py -v`
- **status**: 待执行
- **depends_on**: T-0040

---

## 文档维护任务

### T-0050：更新 ROADMAP.md 状态

- **task_id**: T-0050
- **title**: 每个里程碑完成后更新 ROADMAP.md 中的状态
- **priority**: P2
- **scope**: 文档更新
- **allowed_files**:
  - `docs/ROADMAP.md`
  - `docs/TASK_BACKLOG.md`
- **forbidden_changes**:
  - 无
- **acceptance_criteria**:
  - 每个完成的任务标记 status: completed
  - 更新里程碑状态（✅ / 🔄）
- **test_commands**:
  - 无
- **status**: 持续执行

---

### T-0051：记录新架构决策到 DECISIONS

- **task_id**: T-0051
- **title**: 重要架构决策记录为 ADR 文档
- **priority**: P2
- **scope**: 文档
- **allowed_files**:
  - `docs/DECISIONS/`（新增）
- **forbidden_changes**:
  - 无
- **acceptance_criteria**:
  - 每个重大决策有一个 ADR 文件
  - 格式遵循：状态、上下文、决策、后果
- **test_commands**:
  - 无
- **status**: 持续执行

---

*最后更新：2025-07-18*
