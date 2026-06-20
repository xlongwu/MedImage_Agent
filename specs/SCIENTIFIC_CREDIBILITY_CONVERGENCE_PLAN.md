# Implementation Plan: 科学计算可信度与发布基线收敛

**版本**: v1.0 | **日期**: 2026-06-20 | **目标版本**: v0.5.0

---

## 一、Overview

当前 MedImage_Agent_WebUI_App v0.5.0-rc1 存在工程平台层与科学计算层两层成熟度差异。工程平台层（API、安全门控、前端工作区、Electron 封装）已经成熟，但科学计算层存在以下核心问题：

1. **ALFF** 执行服务使用 `np.std` 简化实现，而仓库已有完整 FFT 内核
2. **FC** 执行服务只写 `{"shape": [N, N], "method": "pearson"}` 而不写真实矩阵
3. **ReHo** 计算内核存在但未接入正式执行服务
4. **状态语义**"succeeded"同时表示"sandbox 准备完成"和"产生了可信数值结果"

本计划旨在完成一次系统性的科学计算可信度收敛，使每个预处理阶段的数值产物可审计、可验证、可复现。

**本计划覆盖的优先级路线：**
```
能力真实性基线 → FC 真实产物 → ALFF/fALFF 统一计算
→ ReHo 验证与接入 → 状态语义修复 → 科学计算 golden tests
→ CI 与依赖固定 → 后端和前端结构拆分 → Windows GUI 验收
```

---

## 二、Architecture Decisions

| # | 决策 | 理由 |
|---|------|------|
| AD-1 | 所有科学计算必须统一调用 `tools/*_compute.py` 内核，Execution Service 不再内联数学逻辑 | 消除重复实现，保证 ALFF/ReHo/FC 定义唯一 |
| AD-2 | 计算状态从单值 `succeeded/failed` 扩展为分层状态枚举 | 不再用同一字段表示"sandbox 就绪"和"数值计算完成" |
| AD-3 | 每个 metric 独立报告状态，不再整体标记成功 | ALFF 完成而 ReHo 未实现时，不应整体返回 succeeded |
| AD-4 | FC 产物从 JSON shape 升级为真实 `.npy`/`.tsv` 矩阵 | 矩阵必须可重新加载且与内存计算结果一致 |
| AD-5 | 拆分遵循 characterization test 先行原则 | 遗留路由和安全关键路径重构必须先用测试固化现有行为 |
| AD-6 | 状态文档更新但不修改历史 release notes | `PROJECT_STATE.md` 反映当前状态；`docs/releases/v0.5.0-rc1.md` 保持不变 |

---

## 三、代码验证事实（2026-06-20 静态核对）

以下问题已通过读取当前主分支代码确认：

| 问题 | 文件 | 行号 | 确认状态 |
|------|------|------|----------|
| ALFF 用 `np.std` 替代 FFT | `services/preprocessing_alff_reho_execution.py` | L84-85 | ✅ 已确认 |
| FC 只写 shape 不写矩阵 | `services/preprocessing_fc_execution.py` | L96-97 | ✅ 已确认 |
| ReHo 服务标注"not yet implemented" | `services/preprocessing_alff_reho_execution.py` | L94 | ✅ 已确认 |
| 已有完整 FFT ALFF 内核 | `tools/alff_compute.py::compute_alff_numpy` | L16-71 | ✅ 已确认 |
| 已有 ReHo CPU/GPU 内核 | `tools/reho_compute.py::compute_reho_numpy` | L25-85 | ✅ 已确认 |
| 已有 FC ROI 内核 | `tools/functional_connectivity_compute.py` | L30-109 | ✅ 已确认 |
| `dashboard_routes.py` 2667 行 | `api/dashboard_routes.py` | — | ✅ 已确认 |
| `App.tsx` 1937 行 | `frontend/src/App.tsx` | — | ✅ 已确认 |

以下与原始分析存在差异，已修正：

| 原分析描述 | 实际状态 | 影响 |
|-----------|---------|------|
| ERROR_KB.yaml 在 `memory/global/` | 已在 `src/backend/app/resources/error_kb.yaml`，解析逻辑完整 | P0-006 降级为验证任务 |
| 前端依赖用 "latest" | 已使用 `^19.2.5` 等明确版本号 | 依赖固定任务范围缩减 |
| CI 只有 pytest + build | CI 已包含 lint、test、typecheck、project-runs-smoke、desktop-check | CI 修复任务范围缩减，但仍缺 format:check 和 eslint/prettier 依赖 |

---

## 四、任务列表

### Phase 0: 基线建立与项目状态同步

#### Task 0.1: 建立当前能力真实性矩阵

**优先级**: P0 | **规模**: S (2 files) | **依赖**: 无

**Description**: 更新 `PROJECT_STATE.md` 和新建 `docs/CAPABILITY_MATRIX.md`，明确每个预处理阶段的真实能力等级。

**Acceptance criteria:**
- [ ] `PROJECT_STATE.md` 日期更新为 2026-06-20，反映最新打包进展（Electron smoke 已通过）
- [ ] `PROJECT_STATE.md` 新增 Known Limitations 条目，明确标注 ALFF/FC/ReHo 的真实状态
- [ ] 新建 `docs/CAPABILITY_MATRIX.md`，按阶段列出能力等级：
  - DICOM Conversion: Release Ready
  - Slice Timing: Needs Verification
  - Realignment: Needs Verification
  - Coregistration/Normalization: Needs Verification
  - Smoothing: Needs Verification
  - Nuisance Regression: Needs Verification
  - Filtering: Needs Verification
  - **ALFF: Metadata Only (simplified std, not FFT-based)**
  - **fALFF: Not Implemented**
  - **ReHo: Not Implemented (kernel exists, not connected)**
  - **FC: Metadata Only (shape descriptor, no matrix persisted)**
- [ ] 能力等级定义严格使用：Contract Only / Dry-run / Sandbox Scaffold / Metadata Only / Numerically Implemented / Reference Validated / Release Ready

**Verification:**
- [ ] `PROJECT_STATE.md` 语法正确，所有新增描述可被现有代码证明
- [ ] `docs/CAPABILITY_MATRIX.md` 中每个阶段都可追溯到对应服务代码

**Files likely touched:**
- `PROJECT_STATE.md`
- `docs/CAPABILITY_MATRIX.md` (new)

---

### Checkpoint 0: 基线建立

- [ ] PROJECT_STATE.md 反映 2026-06-20 实际状态
- [ ] CAPABILITY_MATRIX.md 准确描述每个阶段能力
- [ ] 所有"metadata-only"标注与代码行为一致

---

### Phase 1: 科学计算核心修复（最高优先级）

#### Task 1.1: 修复 FC 实际矩阵产物

**优先级**: P0 | **规模**: M (4 files) | **依赖**: Task 0.1

**Description**: 将 FC 执行服务从"写 shape JSON"改为调用 `tools/functional_connectivity_compute.py` 的内核，持久化真实 correlation matrix 和 Fisher-Z matrix。

**Acceptance criteria:**
- [ ] `run_fc_sandbox_execution()` 调用 `compute_fc_numpy()`（或 backend selector），不再内联 `np.corrcoef` + `json.dumps({"shape":...})`
- [ ] 真实 FC 产物输出为：`sub-xxx_desc-fc_matrix.npy`（NPY 格式，可 `np.load`）和 `sub-xxx_desc-fc_matrix.tsv`（TSV 格式，便于人工检查）
- [ ] Fisher-Z 矩阵输出为：`sub-xxx_desc-fisherz_matrix.npy`
- [ ] ROI labels 写入 `sub-xxx_desc-fc_labels.json`，记录 label 编号和 ROI 名称
- [ ] atlas checksum 写入 `sub-xxx_desc-fc_provenance.json`
- [ ] 当没有真实矩阵产出时，`fc_computed` **必须**为 `false`
- [ ] 保留原有 1000-voxel subset 路径，但改名为 `voxel_subset_debug`，不作为正式 FC 结果
- [ ] 产物重新加载后的矩阵与内存计算结果一致（含测试验证）
- [ ] 矩阵对称性、对角线语义正确

**Verification:**
- [ ] 新增/更新 FC 相关测试：`pytest tests/ -k "fc" --tb=short`
- [ ] 手动验证：生成产物后 `np.load()` 成功，shape 正确

**Files likely touched:**
- `src/backend/app/services/preprocessing_fc_execution.py`
- `src/backend/app/tools/functional_connectivity_compute.py`
- `src/backend/app/schemas/preprocessing_fc_execution.py`
- `tests/` (new/updated FC tests)

**Risks:**
- FC 内核依赖 atlas 输入，需要确认执行服务能否提供有效 atlas；如无 atlas，需生成 synthetic atlas 作为 fallback（使用 `_generate_atlas()`）

---

#### Task 1.2: 将正式 ALFF 链路切换到统一 FFT 内核

**优先级**: P0 | **规模**: M (4 files) | **依赖**: Task 0.1

**Description**: 将 `preprocessing_alff_reho_execution.py` 中的 `np.std` 实现替换为 `tools/alff_compute.py::compute_alff_backend()`，使用 FFT + TR + 频段正式计算 ALFF 和 fALFF。

**Acceptance criteria:**
- [ ] 执行服务调用 `compute_alff_backend(data, tr=TR, freq_band=(0.01, 0.08), ...)`
- [ ] TR 从 BIDS JSON sidecar 或请求参数获取（优先 sidecar）
- [ ] 频段可配置，默认 (0.01, 0.08) Hz
- [ ] 输出 ALFF NIfTI：`sub-xxx_desc-alff_map.nii.gz`（保留 affine 和 header）
- [ ] 输出 fALFF NIfTI：`sub-xxx_desc-falff_map.nii.gz`
- [ ] provenance JSON 记录：TR、频段、算法版本、后端（cpu-numpy / gpu-cupy / gpu-torch）、输入 checksum
- [ ] 移除原有 `voxel_std = np.std(data, axis=-1)` 的简化实现
- [ ] NumPy 与 GPU 结果在定义容差内一致（如 GPU 可用则验证）

**Verification:**
- [ ] 新增 ALFF 数值测试：`pytest tests/ -k "alff" --tb=short`
- [ ] 小数据 golden test：固定输入 → 固定 ALFF/fALFF 输出
- [ ] GPU 一致性测试（条件性，仅 CuPy/PyTorch 可用时运行）

**Files likely touched:**
- `src/backend/app/services/preprocessing_alff_reho_execution.py`
- `src/backend/app/tools/alff_compute.py`
- `src/backend/app/schemas/preprocessing_alff_reho_execution.py`
- `tests/` (new/updated ALFF tests)

**Risks:**
- ALFF 内核需要 4D BOLD + TR + 频段，需确认执行服务能正确获取 TR（从 BIDS JSON sidecar 读取或从请求传入）
- FFT 计算对长时序数据内存占用较高，需确认最大可处理体素数

---

#### Task 1.3: 验证并接入 ReHo

**优先级**: P0 | **规模**: M (4 files) | **依赖**: Task 1.2（可与 1.2 并行设计，但实现需串行避免 ALFF/ReHo 执行服务冲突）

**Description**: 将 `tools/reho_compute.py::compute_reho_backend()` 接入 ALFF/ReHo 执行服务，完成 7/19/27 邻域验证、tie rank 验证、GM mask 验证后正式启用。

**Acceptance criteria:**
- [ ] 执行服务调用 `compute_reho_backend(data_4d, neighborhood=27, gm_mask=..., ...)`
- [ ] 7、19、27 邻域 golden test：固定小数组 → 固定 KCC 输出
- [ ] tie rank 测试：含相同值的时间序列 → 正确处理 tied ranks
- [ ] GM mask 测试：mask 为 0 的体素 → ReHo 值为 0
- [ ] 边界体素（图像边缘）处理方式明确记录
- [ ] CPU/GPU 一致性验证（条件性，仅 CuPy 可用时）
- [ ] 输出 ReHo NIfTI：`sub-xxx_desc-reho_map.nii.gz`
- [ ] provenance JSON 记录：邻域大小、KCC 方法、mask 来源、后端、输入 checksum
- [ ] 在独立参考验证完成前，状态标记为 `numerically_implemented_unvalidated`
- [ ] 移除执行服务中的 "ReHo computation not yet implemented" 警告

**Verification:**
- [ ] 新增 ReHo 测试套件：`pytest tests/ -k "reho" --tb=short`
- [ ] golden tests 通过
- [ ] tie rank tests 通过
- [ ] GPU consistency test 通过（条件性）

**Files likely touched:**
- `src/backend/app/services/preprocessing_alff_reho_execution.py`
- `src/backend/app/tools/reho_compute.py`
- `src/backend/app/schemas/preprocessing_alff_reho_execution.py`
- `tests/` (new ReHo tests)

**Risks:**
- CuPy KCC 实现使用 `argsort` 近似 rank（不处理 ties），与 NumPy 实现存在微小差异。需定义容差范围
- ReHo 计算量大（三重循环），大图像可能需要分块处理或 GPU 加速

---

#### Task 1.4: 统一状态与产物语义

**优先级**: P0 | **规模**: M (4-5 files) | **依赖**: Task 1.1, 1.2, 1.3

**Description**: 重新定义计算状态枚举，每个 metric 独立报告，UI 端不再将"sandbox 完成"展示为"指标计算完成"。

**Acceptance criteria:**
- [ ] 状态枚举定义（schema 层）：
  ```python
  class ExecutionStatus(str, Enum):
      PLANNED = "planned"
      DRY_RUN_READY = "dry_run_ready"
      SANDBOX_PREPARED = "sandbox_prepared"
      METADATA_ONLY = "metadata_only"
      PARTIALLY_COMPUTED = "partially_computed"
      NUMERICALLY_COMPUTED = "numerically_computed"
      VALIDATED = "validated"
      REGISTERED = "registered"
      FAILED = "failed"
  ```
- [ ] 每个 metric 独立报告状态：
  ```python
  {
    "alff": {"computed": True, "validated": False, "artifact_path": "...", "algorithm_version": "..."},
    "falff": {"computed": True, "validated": False, "artifact_path": "..."},
    "reho": {"computed": False, "reason": "reference_validation_pending"}
  }
  ```
- [ ] `manifest.json`、`provenance.json`、`subject_status.json` 使用新状态枚举
- [ ] 前端 UI 不再将 `sandbox_prepared` 或 `metadata_only` 展示为绿色/"已完成"
- [ ] 前端 UI 对 `partially_computed` 状态显示警告图标和具体说明
- [ ] 向后兼容：旧 manifest 读取时 fallback 到合理状态

**Verification:**
- [ ] Schema 测试：新枚举序列化/反序列化正确
- [ ] 执行服务测试：各阶段返回正确的状态值
- [ ] 前端组件测试

**Files likely touched:**
- `src/backend/app/schemas/preprocessing_alff_reho_execution.py`
- `src/backend/app/schemas/preprocessing_fc_execution.py`
- `src/backend/app/services/preprocessing_alff_reho_execution.py`
- `src/backend/app/services/preprocessing_fc_execution.py`
- `src/frontend/src/features/` (preprocessing status components)

---

### Checkpoint 1: 科学计算核心修复

- [ ] FC 产生真实 .npy/.tsv 矩阵产物
- [ ] ALFF 使用 FFT 内核，输出 ALFF + fALFF NIfTI
- [ ] ReHo 接入执行服务，输出真实 ReHo NIfTI
- [ ] 状态语义精确区分 sandbox 准备 vs 数值计算完成
- [ ] 所有新增/修改的测试通过
- [ ] 不再有代码路径将 metadata-only 报告为 succeeded

---

### Phase 2: 验证体系与质量基础设施

#### Task 2.1: 建立科学计算 Golden Tests

**优先级**: P1 | **规模**: L (6-8 files) | **依赖**: Task 1.1, 1.2, 1.3

**Description**: 在 `tests/fixtures/scientific/` 下建立包含固定输入和固定期望输出的 golden test 体系，覆盖 ALFF、fALFF、ReHo、FC、Fisher-Z 和 CPU/GPU 一致性。

**Acceptance criteria:**
- [ ] `tests/fixtures/scientific/` 目录结构：
  ```
  fixtures/scientific/
    input/
      tiny_bold.npy        # 小合成 4D BOLD (e.g., 8x8x8x20)
      tiny_atlas.npy       # 合成 atlas
      tiny_gm_mask.npy     # 合成 GM mask
      sidecar.json         # TR=2.0 等参数
    golden/
      alff_golden.npy      # 已知正确的 ALFF
      falff_golden.npy     # 已知正确的 fALFF
      reho_7_golden.npy    # 邻域 7 KCC
      reho_19_golden.npy   # 邻域 19 KCC
      reho_27_golden.npy   # 邻域 27 KCC
      fc_matrix_golden.npy # 已知正确的 FC
      fisherz_golden.npy   # 已知正确的 Fisher-Z
  ```
- [ ] Golden tests 覆盖：常数时间序列、完全相同时间序列、完全负相关、含 NaN/Inf、空 ROI、零方差 ROI、边界体素
- [ ] GPU consistency tests：CPU vs CuPy 结果在 `atol=1e-4` 内一致
- [ ] Golden values 生成脚本可复现：`python tests/fixtures/scientific/generate_golden.py`
- [ ] 所有 golden tests 进入 CI 流程

**Verification:**
- [ ] `pytest tests/ -k "golden" --tb=short`
- [ ] 所有 golden 值与参考一致

**Files likely touched:**
- `tests/fixtures/scientific/` (new directory)
- `tests/test_scientific_alff_golden.py` (new)
- `tests/test_scientific_reho_golden.py` (new)
- `tests/test_scientific_fc_golden.py` (new)
- `tests/test_scientific_gpu_consistency.py` (new)
- `tests/conftest.py` (可能需更新 fixture)

---

#### Task 2.2: 补齐 CI 质量门（修正版）

**优先级**: P1 | **规模**: S (2-3 files) | **依赖**: Task 1.4

**Description**: 基于当前 CI 已有水平，补齐遗漏项：安装 eslint/prettier 依赖、添加 format:check 到 CI、确认 lint 可正常运行。

**当前 CI 已有**（无需重复添加）：
- ✅ Backend: pytest --collect-only + pytest
- ✅ Frontend: npm ci + typecheck + lint + test + test:project-runs + build
- ✅ Desktop: npm ci + check

**需要补齐**：

**Acceptance criteria:**
- [ ] `src/frontend/package.json` 的 devDependencies 中添加 `eslint` 和 `prettier`
- [ ] `npm run lint` 和 `npm run format:check` 在本地可执行
- [ ] CI frontend job 中 `lint` 步骤通过（之前可能因缺少 eslint 而失败）
- [ ] CI frontend job 中新增 `npm run format:check` 步骤
- [ ] CI 各 job 全部绿色

**Verification:**
- [ ] 本地执行 `cd src/frontend && npm ci && npm run lint && npm run format:check` 通过
- [ ] GitHub Actions CI 运行通过

**Files likely touched:**
- `src/frontend/package.json`
- `src/frontend/package-lock.json`
- `.github/workflows/ci.yml`

---

### Checkpoint 2: 验证体系

- [ ] Golden tests 通过
- [ ] GPU consistency tests 通过（条件性）
- [ ] CI 全部绿色
- [ ] 本地 `npm run lint` 和 `npm run format:check` 通过

---

### Phase 3: 后端结构拆分

#### Task 3.1: 为 dashboard_routes.py 建立 Characterization Tests

**优先级**: P1 | **规模**: L (5-8 files) | **依赖**: Task 1.4

**Description**: 在拆分 dashboard_routes.py 之前，为所有现有 API 端点建立 characterization tests，固化当前行为。这是安全关键路径（DICOM 执行），必须在重构前锁定现有行为。

**Acceptance criteria:**
- [ ] 新增 `tests/characterization/test_dashboard_routes_char.py`，覆盖所有路由
- [ ] 每个测试记录：请求参数、响应状态码、响应 schema 关键字段、安全门控行为
- [ ] DICOM 转换相关路由的测试覆盖：环境变量门控、confirmation 语义、readiness/approval 行为
- [ ] 测试独立于 mock_store 的具体实现细节，只验证外部可观察行为
- [ ] 所有 characterization tests 在当前代码上通过

**Verification:**
- [ ] `pytest tests/characterization/ --tb=short` 全部通过
- [ ] 测试不依赖 mock_store 内部状态格式

**Files likely touched:**
- `tests/characterization/test_dashboard_routes_char.py` (new)
- `tests/characterization/conftest.py` (new)
- `tests/characterization/__init__.py` (new)

---

#### Task 3.2: 拆分 Conversion Routes 到独立 Router

**优先级**: P1 | **规模**: M (4-5 files) | **依赖**: Task 3.1

**Description**: 将 DICOM 转换相关的路由和业务逻辑从 `dashboard_routes.py` 迁移到 `api/conversion_routes.py` + `services/dicom_conversion_service.py`。

**Acceptance criteria:**
- [ ] 新建 `api/conversion_routes.py`，包含所有 DICOM 转换端点
- [ ] 路径保持不变（URL 不变）
- [ ] 业务逻辑从 route 移到 `services/dicom_conversion_service.py`
- [ ] 使用 `Depends(ProjectStore)` 而非 `mock_store` direct access（新增端点部分）
- [ ] 安全门控不变：环境变量、confirmation、readiness、approval、checksum、rollback、安全输出目录
- [ ] Characterization tests 在新路由上通过
- [ ] 原始 `dashboard_routes.py` 中的 conversion 相关函数标记为 `@deprecated`（不在本任务中删除）

**Verification:**
- [ ] `pytest tests/characterization/ -k "conversion" --tb=short` 通过
- [ ] 现有 conversion smoke test 通过

**Files likely touched:**
- `src/backend/app/api/conversion_routes.py` (new)
- `src/backend/app/services/dicom_conversion_service.py` (new)
- `src/backend/app/api/dashboard_routes.py` (标记 deprecated)
- `src/backend/app/main.py` (注册新 router)
- `tests/characterization/test_dashboard_routes_char.py`

---

#### Task 3.3: 拆分 Preprocessing/QC/Task/Artifact Routes

**优先级**: P1 | **规模**: L (6-8 files) | **依赖**: Task 3.2

**Description**: 继续将 `dashboard_routes.py` 中预处理、QC、任务管理和产物相关的路由拆分到各自的 domain router 和 service。

**Acceptance criteria:**
- [ ] 新建 `api/preprocessing_routes.py` + `services/preprocessing_query_service.py`
- [ ] 新建 `api/qc_routes.py`（QC 端点）
- [ ] 新建 `api/task_routes.py` + `services/task_query_service.py`
- [ ] 新建 `api/artifact_routes.py`（产物端点）
- [ ] 所有新路由使用 `Depends(ProjectStore)`
- [ ] 路径保持不变
- [ ] 所有 characterization tests 通过

**Verification:**
- [ ] `pytest tests/characterization/ --tb=short` 全部通过
- [ ] 所有现有集成测试通过

**Files likely touched:**
- `src/backend/app/api/preprocessing_routes.py` (new)
- `src/backend/app/api/qc_routes.py` (new)
- `src/backend/app/api/task_routes.py` (new)
- `src/backend/app/api/artifact_routes.py` (new)
- `src/backend/app/services/preprocessing_query_service.py` (new)
- `src/backend/app/services/task_query_service.py` (new)
- `src/backend/app/api/dashboard_routes.py` (标记 deprecated)
- `src/backend/app/main.py` (注册新 routers)

---

### Checkpoint 3: 后端结构拆分

- [ ] Characterization tests 全部通过
- [ ] 新 routers 功能与旧路由一致
- [ ] API 路径未改变
- [ ] 安全门控语义未改变
- [ ] mock_store direct access 已从新代码中移除

---

### Phase 4: 前端应用控制器拆分

#### Task 4.1: 拆分 App.tsx Workspace 和 Controller

**优先级**: P1 | **规模**: L (8-10 files) | **依赖**: Task 1.4（可与 Phase 3 并行）

**Description**: 将 App.tsx（1937 行）中的 workspace 组件、controller hook 和内联逻辑拆分到独立的 feature 文件和 hooks。

**Acceptance criteria:**
- [ ] 新建结构化文件：
  ```
  features/app/
    AppShell.tsx              # 应用壳（初始化 + 路由 + 全局布局）
    useAppController.ts       # 应用级状态管理 hook
  features/projects/
    useProjectController.ts   # 项目管理 hook
    ProjectCreateResultPanel.tsx
  features/tasks/
    useTaskController.ts
    CompactTaskLog.tsx
    TaskDetailsPanel.tsx
  features/workspaces/
    DataConversionWorkspace.tsx
    PreprocessingWorkspace.tsx
    QCReportsWorkspace.tsx
    SettingsEnvironmentWorkspace.tsx
  features/assistant/
    useAssistantController.ts
  ```
- [ ] App.tsx 缩减到 ~200 行以内，只负责：初始化 → 组合 controller → 根据 mode 渲染页面
- [ ] 关键用户流有 Vitest 覆盖（项目创建、数据检测、计划审核、运行状态查看、结果预览）
- [ ] UI 设计不变
- [ ] API 行为不变
- [ ] 安全行为不变

**Verification:**
- [ ] `cd src/frontend && npm run typecheck` 通过
- [ ] `cd src/frontend && npm run test` 通过
- [ ] `cd src/frontend && npm run build` 通过
- [ ] 关键用户流 Vitest 覆盖

**Files likely touched:**
- `src/frontend/src/App.tsx`
- `src/frontend/src/features/app/` (new)
- `src/frontend/src/features/projects/` (new/update)
- `src/frontend/src/features/tasks/` (new/update)
- `src/frontend/src/features/workspaces/` (new)
- `src/frontend/src/features/assistant/` (new/update)
- `tests/frontend/` (new/updated tests)

---

### Checkpoint 4: 前端拆分

- [ ] App.tsx 减少到 ~200 行
- [ ] 类型检查通过
- [ ] 测试通过
- [ ] 构建通过
- [ ] 关键用户流测试覆盖

---

### Phase 5: 桌面验收与最终交付

#### Task 5.1: 完成稳定版桌面 GUI 验收

**优先级**: P1 | **规模**: M (验证为主，少量代码) | **依赖**: 所有以上任务完成

**Description**: 在 Windows 本地交互式环境中完成桌面 GUI 完整验收，记录结果。

**Acceptance criteria:**
- [ ] Windows 本地 GUI 启动成功
- [ ] Electron 成功启动 backend sidecar
- [ ] 项目创建 smoke test 通过
- [ ] 数据检测 smoke test 通过
- [ ] 计划审核 smoke test 通过
- [ ] 运行状态查看 smoke test 通过
- [ ] 结果预览 smoke test 通过
- [ ] 退出应用后 sidecar 正确停止（无残留进程）
- [ ] 安装包 checksum 记录
- [ ] 明确记录当前构建是否签名（已知当前为未签名构建）

**Verification:**
- [ ] 交互式 Windows 会话中完成以上所有 smoke tests
- [ ] 验收结果记录到 `docs/DESKTOP_SMOKE_REPORT_v0.5.0.md`

**Files likely touched:**
- `docs/DESKTOP_SMOKE_REPORT_v0.5.0.md` (new)
- `PROJECT_STATE.md` (更新)

**Note**: 此任务需要交互式 Windows 桌面环境，部分验证无法在 CI 中自动化。

---

### Checkpoint 5: 最终验收

- [ ] 所有 Phase 0-4 任务完成
- [ ] 桌面 GUI smoke tests 通过
- [ ] 完整代码 diff 审核
- [ ] 版本号确认：v0.5.0
- [ ] CHANGELOG 更新
- [ ] 发布 v0.5.0 tag

---

## 五、任务依赖关系图

```
Phase 0: 基线建立
  Task 0.1 (能力矩阵)  ← 无依赖
        │
        ├──────────────────────────────────────┐
        ↓                                      ↓
Phase 1: 科学计算核心修复                   Phase 4: 前端拆分
  Task 1.1 (FC 产物)    Task 1.2 (ALFF)      Task 4.1 (App.tsx)
        │                    │                    ↑
        │              ┌─────┘                    │
        ↓              ↓                          │
  Task 1.3 (ReHo) ← 可与 1.2 并行设计             │
        │              │                          │
        └──────┬───────┘                          │
               ↓                                  │
  Task 1.4 (状态语义) ←───────────────────────────┘
               │
               ├──────────────────┐
               ↓                  ↓
Phase 2: 验证体系          Phase 3: 后端拆分
  Task 2.1 (Golden Tests)  Task 3.1 (Char Tests)
  Task 2.2 (CI 补齐)            │
               │              Task 3.2 (Conversion)
               │              Task 3.3 (Preproc/QC/Task/Artifact)
               │                  │
               └──────┬───────────┘
                      ↓
Phase 5: 桌面验收
  Task 5.1 (GUI Smoke)
```

**可并行执行的任务对：**
- Task 1.1 (FC) 与 Task 1.2 (ALFF) — 不同文件，无冲突
- Task 1.2 与 Task 1.3 的设计阶段可并行，但实现需串行（共享 `preprocessing_alff_reho_execution.py`）
- Phase 3 (后端拆分) 与 Phase 4 (前端拆分) — 完全独立
- Phase 2 (验证体系) 与 Phase 3/4 可并行

---

## 六、Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|------------|------------|
| ALFF FFT 计算内存溢出（大体素 4D 数据） | Medium | Low | 使用 float32、限制单次最大体素数、分块处理 fallback |
| FC 内核需要 atlas 但执行服务无 atlas 来源 | High | Medium | 使用 `_generate_atlas()` synthetic fallback，标注"无外部 atlas" |
| ReHo NumPy 三重循环性能差 | Medium | High | 默认使用 CuPy（如可用）；提供 z-chunk 分块 CPU 方案 |
| CuPy ReHo KCC 与 NumPy 存在微小差异 | Low | Medium | 记录容差（atol=1e-4），差异来源（tie handling）写入文档 |
| dashboard_routes 拆分破坏安全路径 | High | Low | Characterization tests 先行；DICOM 执行默认关闭保持不变 |
| 旧 manifest 与新状态枚举不兼容 | Medium | Medium | 向后兼容读取：旧 status 值自动映射到新枚举 |
| eslint/prettier 安装后大量 lint 错误 | Medium | High | 先只安装依赖 + format:check，lint 规则逐步收紧，不阻塞 CI |

---

## 七、不包含在本计划中的内容

以下内容明确排除，将在后续版本中处理：

- 组水平统计（Group statistics）
- 协变量设计（Covariate design）
- 多重比较校正
- 分类模型 / 预测建模
- Atlas 管理 / 多 atlas 支持
- ROI parcellation 扩展
- 批量 subject 资源控制
- Windows 代码签名
- 独立参考实现外部验证（本计划仅建立 golden test 内部验证基准）
- 自动更新机制

---

## 八、版本路线建议

| 版本 | 范围 |
|------|------|
| **v0.5.0** | 本计划全部内容：科学计算收敛 + 状态语义 + golden tests + CI + 结构拆分 + GUI 验收 |
| v0.5.1 | Atlas 管理、ROI parcellation、多 atlas 支持、批量 subject、更完整 QC |
| v0.6.0 | 组水平统计、协变量设计、多重比较校正、组间对比、可重复统计报告 |
| v0.7.0+ | Research classification / predictive modeling（不冠以"诊断"措辞） |

---

## 九、Open Questions

1. **Atlas 来源**：FC 执行服务当前无 atlas 输入机制。使用 synthetic atlas (_generate_atlas) 作为过渡是否可接受？正式 atlas 管理计划在 v0.5.1 中完成。
2. **TR 获取方式**：ALFF 需要 TR 参数。是否从 BIDS JSON sidecar 自动读取（需 BIDS 适配器支持），还是从请求参数传入？
3. **GPU 验证环境**：CuPy/PyTorch GPU tests 是否需要在 CI 中运行？CI 当前使用 ubuntu-latest（无 GPU），GPU tests 如何安排？
4. **代码签名**：v0.5.0 正式发布是否要求 Windows 代码签名？已知当前构建为未签名构建。
5. **独立参考实现**：ALFF/ReHo 独立外部验证的选择标准是什么？（DPABI? AFNI? 自有 MATLAB 实现？）

---

*本计划基于 2026-06-20 主分支代码的静态核对生成。所有任务依赖和风险判断基于代码实际状态，而非文档描述。*
