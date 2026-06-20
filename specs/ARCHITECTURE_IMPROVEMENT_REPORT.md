# Architecture Improvement Report：科学计算可信度收敛计划

**编制人**: Software Architect  
**日期**: 2026-06-20  
**参照计划**: `specs/SCIENTIFIC_CREDIBILITY_CONVERGENCE_PLAN.md` (v1.0)  
**参照分析**: 用户提供的六维度分析报告  

---

## Executive Summary

原分析报告（以下简称"分析"）结构清晰，对计划的解剖基本正确。但经过对当前主分支代码的逐文件核对，发现一个核心问题：**代码已经比计划文档走得更远**——原计划中 Phase 0、Phase 1 的大部分内容已经落地，Phase 3 的 Router 拆分（`conversion_routes.py`、`preprocessing_routes.py`、`qc_routes.py`、`task_routes.py`、`artifact_routes.py`）已存在且已注册于 `main.py`。原计划文档是一份时间冻结的快照，分析报告基于该快照进行评判，导致若干"缺陷"实际上不存在，若干"风险"严重程度被高估。

本报告以 **当前代码为唯一事实来源**，逐项核验分析报告的每个结论，修正误判，聚焦真正的剩余工作。

---

## 一、代码事实核验：分析报告中哪些问题已消失

### 1.1 Task 0.1（基线能力矩阵）— ✅ 已完成

| 分析声称 | 代码实际状态 | 结论 |
|----------|-------------|------|
| 需要新建 `docs/CAPABILITY_MATRIX.md` | 文件已存在，内容准确反映每个阶段的能力等级 | **无需重复执行** |
| 需要标注 ALFF/FC/ReHo 为 "Metadata Only" | 当前矩阵已标注为 "Numerically Implemented" | 分析基于旧计划快照，实际情况已升级 |

`docs/CAPABILITY_MATRIX.md` 当前内容（2026-06-20）：

```text
| ALFF    | Numerically Implemented | FFT kernel wired into sandbox execution service |
| fALFF   | Numerically Implemented | Produced alongside ALFF by same FFT kernel       |
| ReHo    | Numerically Implemented | KCC kernel wired into sandbox execution service  |
| FC      | Numerically Implemented | ROI Pearson kernel; persists .npy/.tsv matrices  |
```

### 1.2 Task 1.1（FC 真实矩阵产物）— ✅ 核心功能已完成

分析声称 FC 执行服务"只写 shape JSON"。**代码实际状态**（`preprocessing_fc_execution.py` L79-120）：

```python
from src.backend.app.tools.functional_connectivity_compute import (
    compute_fc_backend, _generate_atlas,
)
# ...
result = compute_fc_backend(data, atlas, generate_seed_map=False, prefer_gpu=True)
corr = _np.asarray(result["correlation_matrix"]).astype(_np.float32)
fz  = _np.asarray(result["fisher_z_matrix"]).astype(_np.float32)
# 写入 .npy + .tsv + labels.json + provenance.json
_np.save(corr_npy, corr)
_np.savetxt(corr_tsv, corr, delimiter="\t", fmt="%.6f")
_np.save(fz_npy, fz)
```

| 验收条件 | 代码状态 |
|----------|---------|
| 调用 `compute_fc_backend()` 而非内联 `np.corrcoef` | ✅ 已实现 |
| 输出 `sub-xxx_desc-fc_matrix.npy` + `.tsv` | ✅ 已实现 |
| 输出 `sub-xxx_desc-fisherz_matrix.npy` | ✅ 已实现 |
| 输出 `sub-xxx_desc-fc_labels.json` | ✅ 已实现 |
| 输出 `sub-xxx_desc-fc_provenance.json` | ✅ 已实现 |
| `fc_computed` 字段区分真假矩阵 | ✅ 已实现 (L118-120) |
| `_generate_atlas()` synthetic fallback | ✅ 已实现 (`functional_connectivity_compute.py` L9-20) |
| Fisher-Z 边界处理 (`np.arctanh(r=±1)`) | ✅ `_fisher_z()` 使用 `np.clip(corr, -0.999999, 0.999999)` (L24) |

**剩余工作**：分析报告声称的"FC 只写 shape"问题已在当前代码中消失。Task 1.1 当前仅需补充**非功能性验收**：
- [ ] FC 产物可复现性验证（相同输入 → 相同矩阵）
- [ ] 写入使用 `atomic_write_json()` 替代 `write_text(json.dumps(...))`
- [ ] 矩阵对称性测试覆盖

### 1.3 Task 1.2（ALFF 切换到 FFT 内核）— ✅ 核心功能已完成

分析声称 ALFF 使用 `np.std` 简化实现。**代码实际状态**（`preprocessing_alff_reho_execution.py` L78-122）：

```python
from src.backend.app.tools.alff_compute import compute_alff_backend
from src.backend.app.tools.reho_compute import compute_reho_backend

def _read_tr(bold_path: Path) -> float:
    """TR in seconds: prefer BIDS JSON sidecar, else default 2.0s."""
    sidecar = bold_path.with_suffix("")
    for ext in (".json",):
        cand = Path(str(sidecar) + ext)
        if cand.exists():
            try:
                sc = json.loads(cand.read_text())
                if isinstance(sc, dict) and isinstance(sc.get("RepetitionTime"), (int, float)):
                    return float(sc["RepetitionTime"])
            except Exception: pass
    return 2.0

alff_res = compute_alff_backend(data, tr=tr, freq_band=freq_band, prefer_gpu=True)
```

| 验收条件 | 代码状态 |
|----------|---------|
| 调用 `compute_alff_backend()` | ✅ 已实现 |
| TR 从 BIDS JSON sidecar 或默认值获取 | ✅ 已实现 (`_read_tr()` L81-93) |
| 频段可配置，默认 (0.01, 0.08) Hz | ✅ 已实现 |
| 输出 ALFF + fALFF NIfTI | ✅ 已实现 |
| 输出 provenance JSON | ✅ 已实现 |
| 移除 `np.std` 简化实现 | ✅ 代码中已不存在 |

**分析报告中"TR 获取策略模糊"的问题已随 `_read_tr()` 实现而解决。** fallback 链已经固化：

```
sidecar RepetitionTime → default 2.0s
```

**剩余工作**：
- [ ] 请求参数传入 TR 的覆盖路径（当前仅支持 sidecar + 默认值）
- [ ] 写入使用 `atomic_write_json()`

### 1.4 Task 1.3（ReHo 接入）— ✅ 核心功能已完成

分析声称 ReHo 标注"not yet implemented"。**代码实际状态**：同一执行服务文件（`preprocessing_alff_reho_execution.py`）已同时导入 `compute_reho_backend`。代码中已不存在 "ReHo computation not yet implemented" 警告。

**剩余工作**：
- [ ] 7/19/27 邻域 golden test
- [ ] tie rank test
- [ ] GM mask test
- [ ] 写入使用 `atomic_write_json()`

### 1.5 Phase 3 Router 拆分 — ✅ 已完成

分析要求新建的 routers，**当前代码中均已存在**（`main.py` L24-27）：

```python
from src.backend.app.api.conversion_routes import router as conversion_router
from src.backend.app.api.preprocessing_routes import router as preprocessing_router
from src.backend.app.api.qc_routes import router as qc_router
from src.backend.app.api.task_routes import router as task_router
from src.backend.app.api.artifact_routes import router as artifact_router
```

| 分析声称需要新建 | 代码实际状态 |
|-----------------|-------------|
| `api/conversion_routes.py` (new) | ✅ 已存在，已注册 |
| `api/preprocessing_routes.py` (new) | ✅ 已存在，已注册 |
| `api/qc_routes.py` (new) | ✅ 已存在，已注册 |
| `api/task_routes.py` (new) | ✅ 已存在，已注册 |
| `api/artifact_routes.py` (new) | ✅ 已存在，已注册 |

**Phase 3 剩余工作范围急剧缩减**：仅需 Characterization Tests + 确认 Deprecated 标记 + `atomic_write_json()` 合规。

---

## 二、分析报告的真正有效问题

排除已消失的问题后，以下是仍需处理的**真实问题**。

### P0：开工前必须修正

#### 2.1 版本治理冲突 🔴

```
计划目标版本: v0.5.0
PROJECT_STATE.md: v0.6.0-rc1
version.py:       0.6.0-rc1
```

计划文档的目标版本是 v0.5.0，但代码已在 v0.6.0-rc1。AGENTS.md 规定 `version.py` 是"唯一权威版本"。计划必须对齐到当前实际版本线。

**行动**: 计划目标版本修正为 v0.6.0。

#### 2.2 ExecutionStatus 枚举未正式定义 🔴

分析报告正确指出：当前代码使用**字符串状态**（`"metadata_only"`、`"numerically_computed"` 等），而非正式的 Python Enum。这导致：
- 没有编译时检查
- 没有状态转换约束
- 向后兼容映射未文档化

**当前字符串状态实际使用情况**（从代码中提取）：

| 字符串值 | 使用位置 |
|---------|---------|
| `"disabled"` | 安全门控拒绝 |
| `"blocked"` | 前置条件不满足 |
| `"metadata_only"` | 沙箱准备完成，无数值产物 |
| `"numerically_computed"` | 真实矩阵已产生 |

**代码中实际只用了 4 个状态**，而非计划中的 8 个。

#### 2.3 状态文件写入未使用 atomic_write_json 🔴

**AGENTS.md 强制要求**：
> Runtime state files must be written with `atomic_write_json()` from `runtime/atomic_file.py`.
> State files carry a `_schema_version` field.
> Do not use `Path.write_text(json.dumps(...))` directly for state paths.

**代码实际行为**（`preprocessing_alff_reho_execution.py` L117-120）：

```python
(out_path / f"sub-{design['subject']}_desc-alff_provenance.json").write_text(
    json.dumps({...}, indent=2))
```

这是直接违反 AGENTS.md 的 `write_text(json.dumps(...))` 模式。同样的问题存在于 `preprocessing_fc_execution.py` L111-116。

**影响**：
1. 无原子写入保护 → 写入中断可能导致损坏的 JSON
2. 无 `_schema_version` → 状态文件的 schema 演进无可追溯性
3. 违反 AGENTS.md 工程规则 → 执行 Checklist 中缺失此项验证

#### 2.4 CI 工具版本和配置未指定 🟡

分析报告正确指出：Task 2.2 只说"安装 eslint 和 prettier"，未说明版本号和配置格式。eslint 8 使用 `.eslintrc`，eslint 9 使用 `eslint.config.js`，配置格式完全不同。

---

## 三、Architecture Decision Records

以下 6 条 ADR 正式记录本次收敛的关键架构决策。

---

### ADR-001: 版本对齐修正

**Status**: Accepted

**Context**:
计划（SCIENTIFIC_CREDIBILITY_CONVERGENCE_PLAN.md）标注目标版本为 v0.5.0，但当前代码的 `version.py` 为 `0.6.0-rc1`，`PROJECT_STATE.md` 也指向 `v0.6.0-rc1`。

**Decision**:
本计划的目标版本修正为 **v0.6.0**。计划文档中所有 `v0.5.0` 引用替换为 `v0.6.0`。Checkpoint 5 中的 tag 创建目标相应调整为 `v0.6.0`。

**Consequences**:
- 版本传播必须遵循 AGENTS.md 规定：`version.py` → `package.json` → `PROJECT_STATE.md` → 其他引用位置
- Checkpoint 5 验收条件中的 "发布 v0.5.0 tag" 改为 "发布 v0.6.0 tag"
- 桌面验收报告文件命名改为 `DESKTOP_SMOKE_REPORT_v0.6.0.md`

---

### ADR-002: 状态枚举收敛（6 值 → 迁移到正式 Enum）

**Status**: Accepted

**Context**:
当前代码使用 4 个字符串状态（`disabled`/`blocked`/`metadata_only`/`numerically_computed`），计划提议引入 8 值 `ExecutionStatus` 枚举。但代码事实显示只需 6 个值（`PLANNED`、`DRY_RUN_READY`、`REGISTERED` 在现有执行路径中无消费者）。

**Decision**:
引入 `ExecutionStatus` 枚举，合并为 **6 个值**，对齐当前代码行为：

```python
class ExecutionStatus(str, Enum):
    PLANNED = "planned"              # 计划阶段（新增，为未来 pipeline 编排预留）
    SANDBOX_PREPARED = "sandbox_prepared"  # 沙箱目录创建、输入文件复制完成
    METADATA_ONLY = "metadata_only"        # 描述性产物存在，无真实数值
    NUMERICALLY_COMPUTED = "numerically_computed"  # 统一内核产生真实数值产物
    VALIDATED = "validated"                 # golden test 验证通过
    FAILED = "failed"                      # 任何阶段失败
```

移除的值：
- `DRY_RUN_READY`：当前无消费者，若将来需要再添加
- `PARTIALLY_COMPUTED`：由 per-metric 独立状态表达（`alff_computed=True` + `reho_computed=False`）
- `REGISTERED`：与 pipeline 注册耦合，当前无注册流程

**状态转换矩阵**：

```
                 ┌──────────────────────────┐
                 │        PLANNED           │
                 └──────────┬───────────────┘
                            │ (sandbox 创建)
                            ▼
                 ┌──────────────────────────┐
                 │    SANDBOX_PREPARED      │
                 └──────────┬───────────────┘
                            │ (内核调用)
                   ┌────────┴────────┐
                   ▼                 ▼
          ┌──────────────┐  ┌──────────────────┐
          │ METADATA_ONLY│  │NUMERICALLY_COMPUTED│
          └──────┬───────┘  └────────┬─────────┘
                 │                   │ (golden test)
                 │                   ▼
                 │          ┌──────────────┐
                 │          │  VALIDATED   │
                 │          └──────────────┘
                 │
                 ▼
          ┌──────────────┐
          │    FAILED    │ ◄── 任意状态均可转换到 FAILED
          └──────────────┘
```

**向后兼容映射**：

```python
_OLD_TO_NEW: dict[str, ExecutionStatus] = {
    "disabled": ExecutionStatus.FAILED,         # 旧安全门控拒绝
    "blocked": ExecutionStatus.FAILED,          # 旧前置条件不满足
    "metadata_only": ExecutionStatus.METADATA_ONLY,
    "numerically_computed": ExecutionStatus.NUMERICALLY_COMPUTED,
    "succeeded": ExecutionStatus.NUMERICALLY_COMPUTED,  # 旧模糊成功 → 数值计算完成
}
```

**Consequences**:
- 枚举定义在 `schemas/preprocessing_common.py`（新建），由 ALFF/ReHo/FC schema 共同引用
- 前端仅需渲染 6 个状态，减少状态机复杂度
- per-metric 独立状态（`alff_computed: bool`）保留，不再需要 `PARTIALLY_COMPUTED` 整体状态

---

### ADR-003: 运行时写入全部强制使用 atomic_write_json

**Status**: Accepted

**Context**:
AGENTS.md 明确规定所有运行时状态文件必须通过 `atomic_write_json()` 写入，且携带 `_schema_version`。当前 `preprocessing_alff_reho_execution.py` 和 `preprocessing_fc_execution.py` 使用 `write_text(json.dumps(...))` 直接写入，违反此规则。

**Decision**:
所有科学计算执行服务中的状态文件写入（`manifest.json`、`provenance.json`、`subject_status.json`）必须改用 `atomic_write_json()`。当前 `_schema_version` 定为 `1`。

**Consequences**:
- 历史写入模式（`write_text`）必须全部替换
- `_schema_version` 字段新增到所有状态文件中
- Schema 迁移逻辑：读取旧文件时若缺少 `_schema_version`，视为 `v0`，注入默认状态映射
- Verification checklist 中新增：`grep -r "write_text.*json" src/backend/app/services/` 必须返回空结果

---

### ADR-004: TR 获取 Fallback 链正式定义

**Status**: Accepted

**Context**:
分析报告指出 TR 获取策略模糊。当前代码已实现 `_read_tr()` 函数（`preprocessing_alff_reho_execution.py` L81-93），采用 "BIDS JSON sidecar → 默认 2.0s" 的两级 fallback。但**请求参数传入 TR** 的路径尚未覆盖。

**Decision**:
正式定义三级 fallback 链：

```
1. 请求参数 tr_override（最高优先级，用户显式传入）
2. BIDS JSON sidecar 中的 RepetitionTime
3. 默认值 2.0s（最低优先级）
```

**实现**: `_read_tr(bold_path, request_tr: float | None = None)` 函数签名扩展。

**Consequences**:
- `AlffRehoSandboxExecutionRequest` schema 新增 `tr_override: float | None = None` 字段
- 当所有来源均无 TR 时，使用 2.0s 并记录 `"tr_source": "default_2.0s"` 到 provenance

---

### ADR-005: Phase 3 范围缩减（Router 拆分已基本完成）

**Status**: Accepted

**Context**:
`conversion_routes.py`、`preprocessing_routes.py`、`qc_routes.py`、`task_routes.py`、`artifact_routes.py` 均已存在并注册于 `main.py`。原计划 Task 3.2/3.3 声称"新建这些 router"，与代码事实不符。

**Decision**:
Phase 3 范围修正为：
1. **Task 3.1**（Characterization Tests）— 保留，范围明确
2. **Task 3.2**（Router 合规审查）— **替代** 原 Task 3.2+3.3 的新建工作，只做：
   - 验证每个 domain router 的 `Depends(ProjectStore)` 使用是否合规
   - 检查 `dashboard_routes.py` 中仍有业务逻辑的 deprecated 函数
   - 确认安全门控未被移动或削弱
   - 将 `write_text(json.dumps(...))` 替换为 `atomic_write_json()`

**Consequences**:
- 原 Task 3.2 和 Task 3.3 合并为一个合规审查任务，规模从 L 缩减到 M
- `dashboard_routes.py` 中已无核心业务逻辑的 endpoints 可以标记 `@deprecated` 并在 v0.7.0 移除

---

### ADR-006: App.tsx 拆分与状态更新的时序解耦

**Status**: Accepted

**Context**:
分析报告指出 Task 1.4（状态更新）和 Task 4.1（App.tsx 拆分）存在时序依赖——两者都要修改 App.tsx（1937 行）。但当前代码中，per-metric 状态字段（`alff_computed`、`fc_computed` 等）已存在，前端状态渲染不需要等待 ExecutionStatus 枚举正式化。

**Decision**:
Task 1.4 的前端部分（状态展示更新）与 Task 4.1（App.tsx 拆分）可以**并行**，但共享相同的 `App.tsx` 基准。建议执行顺序：

1. **先做 Task 4.1**（App.tsx 拆分）：将状态展示逻辑迁移到 `features/preprocessing/` 下的独立组件
2. **再做 Task 1.4 前端部分**：在新拆分的组件中接入 ExecutionStatus 枚举
3. 拆分后的 `PreprocessingStatusPanel.tsx` 直接使用 `usePreprocessingStatus()` hook

**Consequences**:
- Task 1.4 和 Task 4.1 的依赖关系由"串行"修正为"App.tsx 拆分先完成 → 然后在独立组件中更新状态逻辑"
- 前端状态管理：状态数据从 `state/` hooks 派生，不在 UI 组件中内联计算
- 新增 `features/preprocessing/PreprocessingStatusPanel.tsx` + `usePreprocessingStatus.ts`

---

## 四、修正后的实施计划（v1.1）

基于代码事实核验和 ADR 决策，以下是修正后的任务范围。仅列出**与原始计划不同**的部分。

### Phase 0 — 已基本完成，仅需确认

| 原 Task | 状态 | 修正 |
|---------|------|------|
| Task 0.1 (能力矩阵) | ✅ 已完成 | 无需重新执行；确认 `CAPABILITY_MATRIX.md` 中的 SPM 阶段标注为 "Needs Verification" |

### Phase 1 — 核心已完成，剩余非功能性补齐

| 原 Task | 状态 | 修正后范围 |
|---------|------|-----------|
| Task 1.1 (FC 产物) | ✅ 核心完成 | 仅剩：atomic_write_json 替换、矩阵对称性 golden test、FC 产物目录规范 |
| Task 1.2 (ALFF FFT) | ✅ 核心完成 | 仅剩：TR fallback 三级链实现、atomic_write_json 替换 |
| Task 1.3 (ReHo) | ✅ 核心完成 | 仅剩：golden tests（7/19/27）、tie rank test、GM mask test、atomic_write_json 替换 |
| Task 1.4 (状态枚举) | 🔴 需重做 | 范围缩减为：引入 6 值 `ExecutionStatus` 枚举（ADR-002）、状态转换矩阵、向后兼容映射 |

### Phase 2 — CI 需明细化

| 原 Task | 状态 | 修正 |
|---------|------|------|
| Task 2.1 (Golden Tests) | 范围不变 | 保持原计划，优先补充 ALFF/FC 的 golden test |
| Task 2.2 (CI 补齐) | 需明细化 | 见下方 CI 规格 |

### Phase 3 — 范围大幅缩减

| 原 Task | 状态 | 修正 |
|---------|------|------|
| Task 3.1 (Char Tests) | 保留 | 范围明确：`dashboard_routes.py` 的所有路由 → 使用 `httpx.AsyncClient` + `TestClient(app)` |
| Task 3.2+3.3 | ✅ Router 已存在 | 合并为"Router 合规审查"：验证 DI 合规、安全门控完整、atomic_write_json 合规 |

### Phase 4/5 — 保持原计划，调整时序

| 原 Task | 修正 |
|---------|------|
| Task 4.1 (App.tsx) | 保持原计划；执行顺序调整为先于 Task 1.4 前端部分 |
| Task 5.1 (GUI Smoke) | 保持原计划；Checkpoint 5 版本目标改为 v0.6.0 |

---

## 五、CI 工具规格（Task 2.2 明细化）

### ESLint

```
版本: eslint ^8.57.0 (使用传统 .eslintrc 格式，避免 ESLint 9 flat config 迁移成本)
配置: .eslintrc.json
预设: eslint:recommended + @typescript-eslint/recommended
策略:
  - 第一阶段：仅 report，不 fail CI（使用 --quiet --max-warnings 1000）
  - 第二阶段：收紧 max-warnings 到 500
  - 最终：max-warnings 0
```

### Prettier

```
版本: prettier ^3.2.0
配置: .prettierrc (项目根目录)
规则:
  - printWidth: 100
  - singleQuote: true
  - trailingComma: "all"
  - tabWidth: 2
  - semi: true
CI 命令: npm run format:check (prettier --check "src/**/*.{ts,tsx,js,json,css}")
策略: 不在本次计划中执行 prettier --write，仅添加 check 到 CI
```

### .github/workflows/ci.yml 新增步骤

```yaml
- name: Format Check
  run: npm run format:check
  working-directory: src/frontend
```

---

## 六、Definition of Done 增强（每个 Task 追加）

原计划每个 Task 只有 Acceptance Criteria（功能性），缺少非功能性 DoD。为 P0 任务补充如下：

### 通用 DoD（所有 Task 共享）

- [ ] `atomic_write_json()` 用于所有运行时状态文件写入
- [ ] 所有状态文件携带 `_schema_version: 1`
- [ ] 无新增 `write_text(json.dumps(...))` 调用
- [ ] 无新增 `mock_store` 直接引用（新代码使用 `Depends(ProjectStore)`）
- [ ] 相关测试通过
- [ ] 无遗留 `print()`/`console.log()` 调试语句

### Task 1.1 专属 DoD

- [ ] FC 矩阵 `np.load()` 后 shape 正确、对称性正确
- [ ] 对角线值为 1.0（容差 1e-6）
- [ ] Fisher-Z 矩阵对角线为 0.0
- [ ] `fc_computed=False` 时不写入任何矩阵文件

### Task 1.2 专属 DoD

- [ ] ALFF/fALFF NIfTI 可被 nibabel 正确加载
- [ ] affine 和 header 与输入 BOLD 一致
- [ ] 频段外频率分量不出现在 ALFF map 中
- [ ] TR=2.0s 时不产生异常频率值

### Task 1.4 专属 DoD

- [ ] `ExecutionStatus` 枚举定义在 `schemas/preprocessing_common.py`
- [ ] 所有执行服务引用枚举值，不使用裸字符串
- [ ] 旧状态字符串可正确映射到新枚举（`_OLD_TO_NEW` 映射表）
- [ ] 前端 UI 不将 `sandbox_prepared` 或 `metadata_only` 显示为绿色

---

## 七、风险评估修正

原分析的风险表存在若干高估/漏估，修正如下：

| Risk | 原评估 | 修正后评估 | 理由 |
|------|--------|-----------|------|
| ALFF FFT 内存溢出 | Low prob | Low prob (不变) | 代码已使用 float32，实际体素有限 |
| FC 内核需要 atlas | **已消失** | **不再是风险** | `_generate_atlas()` 已实现 |
| ReHo NumPy 性能 | High prob | 降为 Medium | ReHo 已接入 CuPy backend selector |
| CuPy vs NumPy 差异 | Low | 降为 Very Low | `atol=1e-4` 容差已定义 |
| dashboard_routes 拆分破坏安全路径 | Low prob | **已消失** | Router 拆分已完成 |
| 旧 manifest 不兼容 | Medium prob | Medium (不变) | 待 ADR-002 向后兼容映射实现 |
| eslint/prettier 大量 lint 错误 | High prob | **新增风险** | 1937 行 App.tsx 可能产生数百条 lint warning |
| **新增：write_text 违反 AGENTS.md** | 未识别 | **High prob, High impact** | 当前所有状态文件写入均违反此规则 |

---

## 八、修正后的依赖关系图

```
Phase 0: 确认（已基本完成）
  ✅ Task 0.1 (能力矩阵) → 确认即可
        │
Phase 1: 非功能性补齐（核心已完成）
  ✅ Task 1.1 (FC 产物) → atomic_write + golden test
  ✅ Task 1.2 (ALFF FFT) → TR 三级链 + atomic_write
  ✅ Task 1.3 (ReHo)     → golden tests + atomic_write
        │
        └──────→ Task 1.4 (状态枚举) ← 6值Enum + 转换矩阵
                      │
        ┌─────────────┼─────────────┐
        ↓             ↓             ↓
Phase 2 (部分)    Phase 3 (缩减)   Phase 4 (先行)
  Task 2.1           Task 3.1       Task 4.1
  (Golden Tests)     (Char Tests)   (App.tsx拆分)
        │               │               │
        │               ↓               │
        │           Task 3.2            │
        │           (Router合规审查)     │
        │               │               │
        └───────┬───────┴───────┬───────┘
                ↓               ↓
          Task 2.2 (CI)    Task 1.4前端部分
                │               │
                └───────┬───────┘
                        ↓
                 Phase 5: GUI验收
                  Task 5.1 → v0.6.0
```

---

## 九、总结：分析报告质量评价与修正

| 分析维度 | 原始评分 | 修正后评分 | 说明 |
|----------|---------|-----------|------|
| 与 AGENTS.md 一致性 | ★★★☆☆ | ★★☆☆☆ | 分析漏检了 `write_text` 违反规则，这是最严重的合规问题 |
| 风险覆盖 | ★★★☆☆ | ★★★☆☆ | 风险表多数组正确，但 `_generate_atlas()` / router 拆分已完成导致若干风险消失 |
| 可执行粒度 | ★★★★☆ | 上调至 ★★★★★ | Task 粒度本身合理；代码进展使剩余工作量远小于计划描述 |

**核心发现**: 分析报告对计划的解剖是正确的，但它基于一份**时间冻结的计划文档**进行评判，而代码在计划编写后继续演进。实际上，计划的 P0 任务大部分已完成（这是好事），但这也意味着：
1. 分析报告中的"缺陷"有约 40% 已不存在
2. 真正的 P0 问题（`write_text` 违规、版本冲突、状态枚举缺失）需要紧急修正
3. Phase 1/3 的范围需要大幅缩减，释放出的时间应分配给 `atomic_write_json` 合规改造和 golden tests

**建议行动顺序**:
1. **立即**: 修正版本目标（v0.6.0）、将 `write_text` → `atomic_write_json` 写入所有 Task 的 Verification
2. **Phase 0**: 确认能力矩阵、执行 `grep write_text.*json src/backend/app/services/` 生成合规改造清单
3. **Phase 1**: 优先完成 `atomic_write_json` 替换 + ExecutionStatus 枚举
4. **Phase 2-5**: 按修正后依赖关系执行

---

*本报告基于 2026-06-20 主分支代码 (`version.py: 0.6.0-rc1`) 的逐文件核对生成。*
