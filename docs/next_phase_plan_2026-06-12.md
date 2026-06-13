# 下一步后端架构优化 — 完整计划

> **当前基线**: 3684 passed, Phase 1 + Sprint 1 已交付并推送到 GitHub  
> **剩余**: Sprint 2 (routes.py 拆分) → Sprint 3 (node_registry 插件化) → Phase 3 (增强优化)

---

## 现状速查

```
✅ Phase 1   中间件基础设施    异常体系 / 请求追踪 / 限流 / API 版本层 / 原子存储 / ConfigService
✅ Sprint 1  异常处理迁移      66 处 catch-all → raise_api_error()，统一 MEDIMAGE_ERROR 响应格式
⬜ Sprint 2  routes.py 拆分   routes.py 1611 行 88 端点 → 10 个 domain router
⬜ Sprint 3  node_registry     node_registry.py 1361 行 → 7 个领域文件
⬜ Phase 3   增强优化          依赖注入 / 集成测试 / E2E 测试
```

---

## Sprint 2: routes.py 大拆分

**目标**: routes.py 从 1611 行缩减到 < 100 行，只保留 `/health` 和 `/api/project-config`

**前提**: 异常体系已就位（Sprint 1），拆分时可以安全使用 `raise_api_error()`

### 2.1 端点领域映射（88 端点 → 10 个 router）

| # | 领域 | 端点路径前缀 | 端点数 | 目标 router | 状态 |
|---|------|------------|--------|------------|------|
| 1 | DPABI | `/api/dpabi/*` | 20 | `dpabi_routes.py` | ✅ 已创建，端点已复制 |
| 2 | rs-fMRI | `/api/rsfmri/*`, `/api/release-readiness` | 25 | `rsfmri_routes.py` | ✅ 已创建，端点已复制 |
| 3 | Agent | `/api/agent/*`, `/api/runs/*`, `/api/retry/*`, `/api/scheduler/*` | 11 | `agent_routes.py` | ✅ 已创建，端点已复制 |
| 4 | GPU | `/api/gpu/*` | 4 | **新建 `gpu_routes.py`** | ❌ 需创建 |
| 5 | Pipeline | `/api/pipelines/*`, `/api/files/*`, `/api/logs/*` | 5 | **新建 `pipeline_routes.py`** | ❌ 需创建 |
| 6 | Session | `/api/sessions/*`, `/api/history/*` | 6 | **新建 `session_routes.py`** | ❌ 需创建 |
| 7 | Advisor | `/api/advisor/*`, `/api/kb/*` | 7 | **新建 `advisor_routes.py`** | ❌ 需创建 |
| 8 | Experiment | `/api/experiments/*`, `/api/artifacts/*`, `/api/insights` | 9 | **新建 `experiment_routes.py`** | ❌ 需创建 |
| 9 | Bundle | `/api/bundle/*`, `/api/docs/*`, `/api/deployment/*` | 5 | **新建 `artifact_routes.py`** | ❌ 需创建 |
| 10 | Real Data | `/api/real-data/*`, `/api/sandbox/*`, `/api/workflow/*` | 6 | **新建 `realdata_routes.py`** | ❌ 需创建 |

### 2.2 执行步骤

```
Step 0: 端点快照
  └── grep '@router\.' routes.py > endpoints_snapshot.txt  # 备份当前状态

Step 1: 创建 7 个新 domain router
  ├── gpu_routes.py       (4 端点)   # detect / benchmark / capability / synthetic-benchmark
  ├── pipeline_routes.py  (5 端点)   # list / detail / files-read / logs-read / runs
  ├── session_routes.py   (6 端点)   # index / query / runs / nodes / search + history
  ├── advisor_routes.py   (7 端点)   # protocol / error / qc-report / parameters / docs-qa + kb
  ├── experiment_routes.py(9 端点)   # run-index / record / compare / dashboard + artifacts + insights
  ├── artifact_routes.py  (5 端点)   # bundle-create / preview / download-info + docs + deploy
  └── realdata_routes.py  (6 端点)   # inspect / inventory / risk-report / protocol / sandbox / workflow
      └── 每个文件: from src.backend.app.api._errors import raise_api_error

Step 2: 按领域逐批迁移（从大到小）
  每批流程:
    1. 从 routes.py 注释掉该领域的全部端点
    2. 如果是已有 domain router → 在 main.py 取消注释并注册
    3. 如果是新建 domain router → 在 main.py 注册
    4. 运行 pytest --tb=short 确认无路由冲突
    5. 删除 routes.py 中的注释代码

  批 1: DPABI (20 端点)  → 激活 dpabi_router
  批 2: rs-fMRI (25 端点) → 激活 rsfmri_router
  批 3: Agent (11 端点)   → 激活 agent_router
  批 4: GPU (4 端点)      → 注册 gpu_router
  批 5: Pipeline (5 端点) → 注册 pipeline_router
  批 6: Session (6 端点)  → 注册 session_router
  批 7: Advisor (7 端点)  → 注册 advisor_router
  批 8: Experiment (9 端点)→ 注册 experiment_router
  批 9: Bundle (5 端点)   → 注册 artifact_router
  批10: Real Data (6 端点)→ 注册 realdata_router

Step 3: 收尾
  └── routes.py 只保留 /health 和 /api/project-config (约 50 行)
```

### 2.3 特别注意

**dpabi_routes.py、rsfmri_routes.py、agent_routes.py 已有完整端点副本**，但尚未在 main.py 激活。这三组端点迁移本质上就是：
1. 从 routes.py 删除对应端点代码
2. 在 main.py 取消注释 + 注册

**风险**: 如果这些 domain router 中的端点实现与 routes.py 有差异，行为可能变化。建议逐批对比关键端点的业务逻辑。

---

## Sprint 3: node_registry 插件化

**目标**: node_registry.py 从 1361 行单文件拆为 7 个领域文件 + 1 个轻量入口

**关键约束**: 所有 node_id 字符串不变、NODE_REGISTRY 全局变量保持兼容

### 3.1 领域拆分

```
node_registry.py (1361 行, 180+ import, 85+ 节点)
    ↓
node_registry/
├── base.py            NodeRunner Protocol + NodeRegistry 类
├── core_nodes.py      ~8 节点    environment_check, spm_smoke_test, create_synthetic_bids,
│                                 data_inspection, subject_qc, dataset_evaluation, contract_smoke, docs_inventory
├── spm_nodes.py       ~12 节点   spm_smooth_subject, spm_realign_subject, spm_slice_timing_subject,
│                                 spm_coregister_subject, spm_segment_subject, spm_normalize_subject,
│                                 spm_smooth_subject, motion_qc_*, slice_timing_qc_*, registration_qc_*,
│                                 tissue_qc_*, normalization_qc_*, smoothing_qc_*
├── dpabi_nodes.py     ~18 节点   dpabi_capability_inspection, dpabi_wrapper_scaffold, dpabi_input_manifest,
│                                 dpabi_preflight, dpabi_run_plan, dpabi_sandbox_smoke_run,
│                                 dpabi_signature_probe, dpabi_wrapper_contracts,
│                                 dpabi_single_function_sandbox, dpabi_subject_smooth,
│                                 dpabi_subject_wrapper_report, dpabi_wrapper_validation_matrix,
│                                 dpabi_template_*, dpabi_*_contract (4 个 contract)
├── gpu_nodes.py       ~5 节点    gpu_alff_subject, gpu_reho_subject, gpu_nuisance_regression_subject,
│                                 gpu_temporal_filtering_subject, gpu_functional_connectivity_subject
├── rsfmri_nodes.py    ~14 节点   rsfmri_preprocessing_plan, nuisance_regression_subject + report,
│                                 temporal_filtering_subject + report, alff_falff_subject + report + contracts,
│                                 reho_subject + report + contracts, fc_subject + report + contracts,
│                                 group_dataset_summary
├── qc_nodes.py        ~13 节点   motion_qc_subject + report, slice_timing_dataset_report,
│                                 st_realign_motion_chain_report, registration_qc_dataset_report,
│                                 tissue_qc_dataset_report, normalization_qc_dataset_report,
│                                 smoothing_qc_dataset_report, all *_dataset_report nodes
└── report_nodes.py    ~8 节点    report_export, report_validate, release_readiness,
                                  dpabi_subject_wrapper_report, docs_inventory
```

### 3.2 NodeRunner Protocol

```python
# node_registry/base.py
from typing import Any, Protocol

class NodeRunner(Protocol):
    @property
    def node_id(self) -> str: ...

    def __call__(self, node: Any, project_config: dict, context: dict) -> dict[str, Any]:
        """返回 {"ok": bool, "outputs": [...], "errors": [...], ...}"""
        ...

class NodeRegistry:
    def __init__(self):
        self._runners: dict[str, NodeRunner] = {}

    def register(self, runner: NodeRunner) -> None:
        if runner.node_id in self._runners:
            raise ValueError(f"Duplicate node_id: {runner.node_id}")
        self._runners[runner.node_id] = runner

    def get(self, node_id: str) -> NodeRunner:
        return self._runners[node_id]

    def __getitem__(self, node_id: str) -> NodeRunner:
        return self.get(node_id)

    def __contains__(self, node_id: str) -> bool:
        return node_id in self._runners

    def keys(self) -> list[str]:
        return sorted(self._runners.keys())

    def items(self):
        return self._runners.items()
```

### 3.3 向后兼容

```python
# node_registry.py [重构后，约 15 行]
from src.backend.app.runtime.node_registry.create import create_registry

NODE_REGISTRY = create_registry()  # pipeline_executor 继续 import 此变量
```

### 3.4 执行步骤

1. **快照**: 遍历当前 NODE_REGISTRY，输出所有 `(node_id, module.function)` 到 snapshot 文件
2. **创建 base.py**: NodeRunner Protocol + NodeRegistry 类
3. **创建 create.py**: `create_registry()` 工厂函数
4. **创建 7 个领域文件**: 复制 runner 定义，添加 `@property node_id` 适配
5. **更新 node_registry.py**: 替换为轻量入口
6. **全量 pytest** + node_id 快照 diff 验证

---

## Phase 3: 增强优化

Sprint 2 和 3 完成后，进入质量提升阶段。

### 3.1 依赖注入

```python
# 当前: 路由函数直接 import 服务模块
from src.backend.app.services.mock_store import mock_store

@router.get("/api/projects")
def list_projects():
    return mock_store.list_projects()

# 目标: FastAPI Depends() 注入
from fastapi import Depends
from src.backend.app.api.dependencies import get_store

@router.get("/api/projects")
def list_projects(store=Depends(get_store)):
    return store.list_projects()
```

**收益**: 测试时可以替换 `get_store` 为 mock，不再需要 monkeypatch。

### 3.2 API 集成测试

```
tests/
├── unit/                          # [现有]
└── integration/
    └── api/                       # [新增]
        ├── test_health_api.py     # GET /health → 200
        ├── test_pipeline_api.py   # GET /api/pipelines → 200 + schema 验证
        ├── test_dpabi_api.py      # DPABI 端点 smoke
        └── conftest.py            # TestClient fixture
```

### 3.3 端到端流水线测试

```python
# tests/integration/pipeline/test_synthetic_pipeline.py
def test_synthetic_bids_pipeline_runs():
    """从 project_config.yaml → 计划 → 执行 → 状态文件 → 验证完整链路"""
    result = run_pipeline("examples/project_config.yaml", "examples/pipeline_mvp.yaml")
    assert result["status"] == "SUCCESS"
    assert Path(result["summary_path"]).exists()
```

---

## 约束说明

**AGENTS.md 当前约束**: "Current P0 work is delivery-state repair only: no new features, no broad refactor."

- Sprint 2（routes.py 拆分）和 Sprint 3（node_registry 插件化）属于 **broad refactor** 范畴
- 建议在 P0 交付态修复完成、AGENTS.md 约束放宽后再推进
- Phase 3（依赖注入、集成测试）属于 **enhancement**，无功能变更，风险最低，可在任何时候推进

### 推荐推进顺序

```
当前 (P0 交付态修复) → Phase 3 集成测试（低风险）
                              ↓
                   P0 完成后 → Sprint 2（routes.py 拆分）
                              ↓
                              Sprint 3（node_registry 插件化）
```

---

## 一页总结

| 阶段 | 内容 | 文件 | 风险 | 状态 |
|------|------|------|------|------|
| Phase 1 | 中间件基础设施 | 15 文件 | 低 | ✅ 已交付 |
| Sprint 1 | 异常处理迁移 | 13 文件 | 低 | ✅ 已交付 |
| Sprint 2 | routes.py 拆分 | 1611→<100 行 | 中 | ⬜ 待约束放宽 |
| Sprint 3 | node_registry 插件化 | 1361 行→7 文件 | 高 | ⬜ 待约束放宽 |
| Phase 3 | 集成测试 + DI | 约 10 文件 | 低 | ⬜ 可随时推进 |
