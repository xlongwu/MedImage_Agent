# MedImage Agent 前端重构方案

> 目标：将当前“开发者调试台式”的复杂前端，重构为面向研究人员和普通用户的简洁工作流界面。  
> 核心原则：默认展示主流程；底层 pipeline、agent、node、API、日志等调试信息移入“高级模式 / 开发者模式”。

---

## 1. 当前界面问题

从当前截图看，前端已经把很多底层功能直接暴露出来，例如：

- API 状态
- 项目配置
- Pipeline 浏览器
- Agent 控制
- rs-fMRI Core Preprocessing Plan
- SPM Slice Timing + Metadata QC
- 各类单节点面板
- 各类 JSON / Markdown / Debug 信息

这些内容对开发者有用，但对普通用户或研究人员来说会造成明显困惑。

当前主要问题：

1. **入口不清晰**：用户不知道应该先上传数据、先选 pipeline，还是先点 Agent。
2. **概念过于底层**：pipeline、agent run、plan JSON、node 级执行不应该默认展示。
3. **页面过长**：所有模块平铺，用户无法形成清晰操作路径。
4. **错误提示不友好**：`Failed to fetch` 直接暴露，缺少“后端未启动”等可理解解释。
5. **缺少主流程**：没有形成“上传数据 → 设置预处理 → 设置分析 → 运行 → 查看结果”的用户路径。
6. **开发模式和用户模式混杂**：高级调试能力应保留，但不应默认显示。

---

## 2. 重构目标

重构后的前端应让用户清楚完成以下任务：

1. 了解 MedImage Agent 是什么。
2. 上传或选择数据。
3. 自动检查数据是否符合要求。
4. 选择预处理步骤。
5. 设置常用预处理参数。
6. 选择是否进行后续分析。
7. 设置 ALFF / ReHo / Functional Connectivity 等分析参数。
8. 确认配置并运行。
9. 查看运行进度、QC、分析结果和报告。
10. 进入高级模式查看 pipeline、agent、日志、contracts、release readiness 等底层信息。

一句话目标：

```text
从“开发者调试台”重构为“医学影像处理任务向导”。
```

---

## 3. 新的信息架构

建议将前端分成两个模式：

```text
MedImage Agent Frontend
├── 用户模式 User Mode
│   ├── 项目简介
│   ├── 数据上传
│   ├── 预处理设置
│   ├── 分析设置
│   ├── 确认并运行
│   ├── 结果查看
│   └── 历史记录
│
└── 高级模式 Advanced / Developer Mode
    ├── API 状态
    ├── 项目配置
    ├── Pipeline 浏览器
    ├── Agent 控制
    ├── 单节点执行面板
    ├── SPM / DPABI / GPU 环境检查
    ├── Run History JSON
    ├── Release Readiness
    ├── Docs Inventory
    └── Debug Logs
```

默认进入 **用户模式**。  
高级模式通过右上角按钮进入。

---

## 4. 推荐主界面：五步向导

主界面建议使用 Stepper：

```text
1. 上传数据
2. 设置预处理
3. 设置分析
4. 确认并运行
5. 查看结果
```

每一步只展示当前需要的信息，不再把所有面板平铺在首页。

---

# 5. 用户模式详细设计

---

## Step 1：上传数据

### 目标

让用户导入数据，并完成初步数据识别。

### 支持方式

建议支持三种入口：

```text
1. 上传 ZIP 数据包
2. 选择服务器本地数据目录
3. 使用示例 synthetic 数据
```

### 页面示例

```text
步骤 1：上传数据

请选择数据来源：

( ) 上传 ZIP 文件
( ) 选择已有数据目录
( ) 使用示例数据

数据路径 / 上传文件：
[________________________] [选择 / 上传]

[扫描数据]
```

扫描后显示：

```text
数据检查结果

数据类型：BIDS-like / Unknown
模态：rs-fMRI
Subjects：12
Sessions：1
Runs：12
JSON metadata：完整 / 缺失
NIfTI 文件：完整 / 缺失
状态：通过 / 警告 / 失败
```

### 错误提示规范

不要只显示：

```text
Failed to fetch
```

应显示：

```text
无法连接后端服务。请确认后端已启动：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

并提供：

```text
[查看技术细节]
```

### 建议 API

如果已有 API 不够聚合，建议后续新增：

```text
POST /api/dataset/upload
POST /api/dataset/inspect
POST /api/dataset/use-demo
GET  /api/dataset/current
```

### 前端状态

```ts
type DatasetState = {
  sourceType: "none" | "upload" | "directory" | "demo";
  datasetPath?: string;
  uploadedFileName?: string;
  inspectionStatus: "NOT_RUN" | "PASS" | "WARNING" | "FAIL";
  subjectCount?: number;
  sessionCount?: number;
  modality?: string;
  warnings: string[];
  errors: string[];
};
```

---

## Step 2：设置预处理

### 目标

让用户用 checklist 方式选择预处理步骤和常用参数，而不是直接面对 pipeline YAML 或单节点面板。

### 默认预处理步骤

建议默认勾选：

```text
[x] Slice Timing Correction
[x] Realignment / Motion Correction
[x] Coregistration
[x] Segmentation
[x] Normalization
[x] Smoothing
[x] Nuisance Regression
[x] Temporal Filtering
```

每个步骤旁边放一句简短说明：

```text
Slice Timing Correction：校正不同切片采集时间差异。
Realignment：校正头动并生成运动参数。
Normalization：将图像变换到标准空间。
```

### 常用参数

默认展示：

```text
TR：自动读取 / 手动输入
Slice Order：自动读取 / 手动选择
Reference Slice：中间切片 / 自定义
Smoothing FWHM：6 mm
Filtering Band：0.01 - 0.08 Hz
Nuisance Model：Friston 24 + WM + CSF
```

### 高级参数

默认折叠：

```text
[展开高级参数]

- Normalization voxel size
- Bounding box
- FD threshold
- Head radius
- Global signal regression
- Linear trend
- Intercept
```

### 页面示例

```text
步骤 2：设置预处理

基础预处理步骤

[x] Slice Timing Correction       参数
[x] Realignment                   参数
[x] Coregistration                参数
[x] Segmentation                  参数
[x] Normalization                 voxel size: 3 x 3 x 3
[x] Smoothing                     FWHM: 6 mm
[x] Nuisance Regression           Friston 24 + WM + CSF
[x] Temporal Filtering            0.01 - 0.08 Hz

[恢复推荐设置] [保存为模板] [下一步]
```

### 前端状态

```ts
type PreprocessingConfig = {
  sliceTiming: {
    enabled: boolean;
    tr: number | null;
    sliceOrder: "auto" | "ascending" | "descending" | "custom";
    referenceSlice: "middle" | number;
  };
  realignment: {
    enabled: boolean;
  };
  coregistration: {
    enabled: boolean;
  };
  segmentation: {
    enabled: boolean;
  };
  normalization: {
    enabled: boolean;
    voxelSize: [number, number, number];
  };
  smoothing: {
    enabled: boolean;
    fwhm: [number, number, number];
  };
  nuisanceRegression: {
    enabled: boolean;
    model: "friston24" | "basic";
    includeWM: boolean;
    includeCSF: boolean;
    includeGlobalSignal: boolean;
    includeLinearTrend: boolean;
  };
  temporalFiltering: {
    enabled: boolean;
    lowHz: number;
    highHz: number;
  };
};
```

---

## Step 3：设置分析

### 目标

让用户决定是否在预处理后继续分析，并选择分析类型。

### 主开关

```text
是否对预处理后的数据进行分析？

(o) 只做预处理
(o) 预处理后继续分析
```

### 分析选项

如果选择继续分析，显示：

```text
[x] ALFF / fALFF
[x] ReHo
[x] Functional Connectivity
[x] Group Summary
[x] Report Export
```

### 分析参数

#### ALFF / fALFF

```text
Frequency band: 0.01 - 0.08 Hz
Mask: auto
```

#### ReHo

```text
Neighborhood:
(o) 27 voxels
( ) 19 voxels
( ) 7 voxels
```

#### Functional Connectivity

```text
ROI atlas:
(o) Synthetic ROI atlas
( ) Upload atlas
( ) Future: AAL / Schaefer / Brainnetome

ROI count: 4
Generate seed-to-voxel map: Yes / No
Correlation: Pearson
Fisher-z transform: Yes
```

#### Report

```text
[x] Generate dataset summary
[x] Export report package
[x] Validate report package
```

### 前端状态

```ts
type AnalysisConfig = {
  enabled: boolean;
  alffFalff: {
    enabled: boolean;
    lowHz: number;
    highHz: number;
  };
  reho: {
    enabled: boolean;
    neighborhood: 7 | 19 | 27;
  };
  functionalConnectivity: {
    enabled: boolean;
    roiAtlas: "synthetic" | "uploaded";
    roiCount: number;
    generateSeedMap: boolean;
    correlation: "pearson";
    fisherZ: boolean;
  };
  groupSummary: {
    enabled: boolean;
  };
  reportExport: {
    enabled: boolean;
    validateAfterExport: boolean;
  };
};
```

---

## Step 4：确认并运行

### 目标

在运行前给用户一个清晰摘要，并要求确认。

### 配置摘要

```text
运行摘要

数据：
- 数据来源：上传 ZIP
- Subjects：12
- 模态：rs-fMRI

预处理：
- Slice Timing
- Realignment
- Coregistration
- Segmentation
- Normalization
- Smoothing
- Nuisance Regression
- Temporal Filtering

分析：
- ALFF / fALFF
- ReHo
- Functional Connectivity
- Group Summary
- Report Export + Validation

输出：
- derivatives/
- reports/
- exports/
```

### 安全确认

如果涉及 SPM / MATLAB：

```text
本次运行将调用 MATLAB/SPM。请确认：

[x] 我确认使用当前数据运行预处理
[x] 我确认 rawdata 不会被修改
[x] 我确认输出写入 derivatives/reports
```

如果是 Quickstart Demo 或 Python-only：

```text
本次运行不调用 SPM、MATLAB、DPABI 或 GPU。
```

### 按钮

```text
[保存配置] [生成执行计划] [开始运行]
```

建议流程：

```text
用户配置
→ 生成 plan preview
→ 用户确认
→ 执行
```

### 运行状态

```text
运行中...

当前阶段：Temporal Filtering
当前被试：sub-003
整体进度：42%
已完成：5 / 12 subjects
```

---

## Step 5：查看结果

### 目标

让用户查看处理结果、QC、报告、导出文件和历史记录。

### 结果摘要

```text
运行状态：完成 / 警告 / 失败
Subjects：12
PASS：10
WARNING：2
FAIL：0
报告包：已生成
验证：通过
```

### 结果 Tabs

```text
[总览] [QC] [分析结果] [报告] [历史记录] [日志]
```

#### 总览

- 运行状态
- subject 数量
- stage summary
- warning/error 数量

#### QC

- motion QC
- normalization QC
- filtering QC
- ALFF QC
- ReHo QC
- FC QC

#### 分析结果

- ALFF/fALFF summary
- ReHo summary
- FC matrix summary

#### 报告

- Markdown report
- ZIP report package
- validation result

#### 历史记录

- 当前 run
- 最近 runs
- quickstart demo
- run history browser

#### 日志

默认折叠，仅高级用户查看。

---

# 6. 高级模式设计

高级模式保留现有大部分面板，但重新分类。

## 6.1 高级模式入口

右上角：

```text
[高级模式]
```

提示：

```text
高级模式面向开发者和管理员，包含 pipeline、agent、node、API、日志等底层调试信息。
```

## 6.2 高级模式菜单

建议左侧菜单：

```text
系统状态
Pipeline
Agent
SPM / DPABI / GPU
rs-fMRI 单步骤
Reports
Memory / Insights
Docs / Release
Debug Logs
```

### 系统状态

- API health
- backend version
- project config
- environment check

### Pipeline

- pipeline browser
- pipeline YAML preview
- node registry
- pipeline run summary

### Agent

- agent plan
- agent run
- background review
- memory state

### SPM / DPABI / GPU

- MATLAB check
- SPM check
- DPABI check
- GPU capability
- contracts

### rs-fMRI 单步骤

- slice timing
- realignment
- coregistration
- segmentation
- normalization
- smoothing
- nuisance regression
- filtering
- ALFF
- ReHo
- FC

### Reports

- group summary
- report exporter
- report validator
- run history

### Memory / Insights

- SessionDB
- insights
- error intelligence
- ERROR_KB

### Docs / Release

- docs inventory
- release readiness

---

# 7. 组件设计建议

## 7.1 新增核心组件

```text
frontend/src/components/workflow/
  WorkflowShell.tsx
  WorkflowStepper.tsx
  IntroCard.tsx
  DataUploadStep.tsx
  DatasetSummaryCard.tsx
  PreprocessingConfigStep.tsx
  PreprocessingStepCard.tsx
  AnalysisConfigStep.tsx
  RunConfirmStep.tsx
  RunProgressPanel.tsx
  ResultsOverviewStep.tsx
  ResultSummaryCards.tsx
  AdvancedModePanel.tsx
```

## 7.2 新增状态文件

```text
frontend/src/state/
  workflowTypes.ts
  defaultWorkflowConfig.ts
  workflowReducer.ts
```

## 7.3 保留旧组件

旧组件不要删除，先迁移到高级模式：

```text
RsfmriPreprocessingPlanPanel
RsfmriSliceTimingPanel
RsfmriRealignmentPanel
RsfmriAlffFalffPanel
RsfmriRehoPanel
RsfmriFunctionalConnectivityPanel
RsfmriGroupSummaryPanel
RsfmriReportExporterPanel
RsfmriReportValidatorPanel
ReleaseReadinessPanel
DocumentationCenterPanel
RunHistoryBrowserPanel
QuickstartDemoPanel
```

---

# 8. App.tsx 推荐结构

```tsx
export default function App() {
  const [mode, setMode] = useState<"user" | "advanced">("user");

  return (
    <AppShell>
      <Header mode={mode} setMode={setMode} />
      {mode === "user" ? (
        <WorkflowShell />
      ) : (
        <AdvancedModePanel />
      )}
    </AppShell>
  );
}
```

---

# 9. 推荐 API 设计

为了支持简洁工作流，建议后续新增聚合式 workflow API，减少前端直接调用底层 API。

## 9.1 Workflow API

```text
GET  /api/workflow/default-config
POST /api/workflow/validate-config
POST /api/workflow/create-plan
POST /api/workflow/run
GET  /api/workflow/status/{run_id}
GET  /api/workflow/result/{run_id}
```

## 9.2 Dataset API

```text
POST /api/dataset/upload
POST /api/dataset/inspect
POST /api/dataset/use-demo
GET  /api/dataset/current
```

## 9.3 Results API

```text
GET /api/results/latest
GET /api/results/{run_id}
GET /api/results/{run_id}/qc
GET /api/results/{run_id}/reports
```

## 9.4 保留现有高级 API

```text
/api/rsfmri/...
/api/quickstart-demo/...
/api/run-history/...
/api/release-readiness
/api/docs/inventory
```

---

# 10. 运行模式设计

建议用户可以选择运行模式：

```text
运行模式：
(o) Quickstart Demo：使用 synthetic 示例数据
(o) Python-only：只运行 Python 后处理和报告
(o) SPM Approved：运行 SPM 预处理，需要确认
(o) Future DPABI：暂不可用 / contract-only
(o) Future GPU：可选加速，需要环境检查
```

当前默认推荐：

```text
Quickstart Demo
```

或者：

```text
Python-only
```

真实 SPM / DPABI / GPU 不应默认开启。

---

# 11. 错误展示规范

## 11.1 普通用户错误

不要只显示：

```text
Failed to fetch
```

应该显示：

```text
无法连接后端服务。请确认后端已启动。
```

并给出启动命令：

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

## 11.2 技术细节折叠

```text
[查看技术细节]

GET http://127.0.0.1:8000/api/health
net::ERR_CONNECTION_REFUSED
```

## 11.3 错误分类

结合 Error Intelligence：

```text
错误类型：后端未启动
建议操作：启动后端服务后点击刷新
严重程度：中
是否可重试：是
```

---

# 12. 视觉与交互建议

## 12.1 页面风格

- 首页更简洁；
- 卡片数量减少；
- 每页只展示当前任务；
- JSON 默认折叠；
- Debug 信息默认隐藏；
- 高级参数默认折叠；
- 报告和日志使用 tabs。

## 12.2 推荐布局

```text
Header
------------------------------------------------
Stepper: 上传数据 > 预处理 > 分析 > 运行 > 结果
------------------------------------------------
Main Card
------------------------------------------------
Footer Actions: 上一步 / 下一步 / 保存 / 开始运行
```

## 12.3 状态颜色

```text
PASS      绿色
WARNING   黄色
FAIL      红色
RUNNING   蓝色
IDLE      灰色
```

---

# 13. 现有模块迁移表

| 当前模块 | 新位置 |
|---|---|
| API 状态 | 高级模式 / 系统状态 |
| 项目配置 | 高级模式 / 系统状态 |
| Pipeline 浏览器 | 高级模式 / Pipeline |
| Agent 控制 | 高级模式 / Agent |
| rs-fMRI Core Plan | 高级模式 / Pipeline |
| SPM Slice Timing 面板 | 高级模式 / rs-fMRI 单步骤 |
| ALFF / ReHo / FC 面板 | 用户模式分析配置 + 高级模式单步骤 |
| Report Exporter | 用户模式结果 + 高级模式 Reports |
| Report Validator | 用户模式结果 + 高级模式 Reports |
| Release Readiness | 高级模式 / Docs & Release |
| Docs Inventory | 高级模式 / Docs & Release |
| Quickstart Demo | 用户模式运行入口 |
| Run History Browser | 用户模式历史记录 + 高级模式 Reports |

---

# 14. 分阶段实施计划

## Phase 1：信息架构重构

目标：先不改 backend，只重组前端。

任务：

1. 新建 `WorkflowShell`。
2. 新建 5 步 Stepper。
3. 创建简介 / 上传 / 预处理 / 分析 / 运行 / 结果组件。
4. 将旧组件放入 `AdvancedModePanel`。
5. 默认显示用户模式。

验收：

- 首页不再显示大量开发者模块；
- 用户能看到清晰 5 步流程；
- 高级模式仍可访问旧功能。

---

## Phase 2：前端状态与配置模型

目标：让用户选择的数据、预处理和分析参数能形成统一 config。

任务：

1. 定义 `WorkflowState`。
2. 定义 `defaultWorkflowConfig`。
3. 实现参数表单。
4. 实现配置摘要。
5. 实现保存 / 加载配置。

验收：

- 用户选择内容能形成 JSON；
- 配置摘要准确；
- 参数可恢复默认。

---

## Phase 3：聚合式 Workflow API

目标：减少前端直接调用底层 API。

任务：

1. 新增 `/api/workflow/default-config`。
2. 新增 `/api/workflow/validate-config`。
3. 新增 `/api/workflow/create-plan`。
4. 新增 `/api/workflow/run`。
5. 新增 `/api/workflow/status/{run_id}`。
6. 新增 `/api/workflow/result/{run_id}`。

验收：

- 前端通过 workflow API 完成主流程；
- 底层 pipeline API 保留给高级模式。

---

## Phase 4：数据上传与数据检查

目标：支持真实用户上传或选择数据。

任务：

1. 实现 ZIP upload。
2. 实现 local path input。
3. 实现 demo dataset。
4. 实现 dataset inspection summary。
5. 处理 BIDS / 非 BIDS 警告。

验收：

- 用户能上传数据；
- 能看到 subject/session/modality；
- 错误提示友好。

---

## Phase 5：运行进度与结果展示

目标：提升运行体验。

任务：

1. 实现 run status polling。
2. 显示 stage progress。
3. 显示 subject progress。
4. 显示 QC summary。
5. 显示 report package link。
6. 显示 validation status。

验收：

- 用户能知道当前运行到哪一步；
- 完成后能看到结果和报告；
- 失败时能看到原因和建议。

---

## Phase 6：高级模式整理

目标：保留开发能力，但不打扰普通用户。

任务：

1. 对旧面板分组。
2. 加入侧边栏。
3. JSON 默认折叠。
4. 增加搜索 / 快速跳转。
5. Debug 信息只在高级模式显示。

验收：

- 高级用户仍可调试；
- 普通用户默认看不到底层复杂内容。

---

# 15. 最小可行改造版本

如果不想一次重构太大，建议先做最小版。

## MVP UI Redesign v1

只实现：

1. 新首页简介；
2. 5 步 Stepper；
3. 数据选择支持“使用示例数据”；
4. 预处理 checklist；
5. 分析 checklist；
6. 运行 Quickstart Demo；
7. 显示 Quickstart Demo 结果；
8. 旧功能全部移入高级模式。

暂不立即实现：

- 真正 ZIP 上传；
- 完整 workflow API；
- 复杂进度条；
- 完整真实数据 pipeline 运行。

这样可以快速改善用户体验，同时不大幅改 backend。

---

# 16. 最小版用户流程

```text
进入首页
→ 阅读简介
→ 点击“使用示例数据”
→ 勾选预处理步骤
→ 勾选分析步骤
→ 点击“开始演示运行”
→ 查看 QC / 报告 / 历史记录
```

---

# 17. 验收标准

完成前端重构后，应满足：

1. 默认首页不再显示所有开发者调试面板。
2. 用户能看到清晰的 5 步流程。
3. 用户可以选择数据来源。
4. 用户可以勾选预处理步骤。
5. 用户可以勾选是否进行后续分析。
6. 用户可以设置常用参数。
7. 用户可以确认配置后运行。
8. 用户可以看到结果摘要。
9. 用户可以进入高级模式查看旧功能。
10. 后端未启动时显示友好错误，而不是只显示 `Failed to fetch`。
11. JSON / Plan / Logs 默认不暴露给普通用户。
12. Quickstart Demo 能从新界面启动。
13. Report Export / Validator 能在结果页展示。
14. Run History 能作为历史记录展示。
15. 高级模式仍可访问 pipeline、agent、SPM、DPABI、GPU、docs、release readiness 等功能。

---

# 18. 推荐 Trae 开发 Prompt

```text
现在我要重构 MedImage Agent 前端。

当前前端把 API 状态、Pipeline 浏览器、Agent 控制、SPM 单步骤、各种 QC 和报告面板全部平铺显示，界面太复杂，不适合普通用户。

请先完成前端重构第一阶段：信息架构重构，不改 backend。

目标：

1. 默认进入简洁用户模式；
2. 用户模式使用 5 步向导：
   - 上传数据
   - 设置预处理
   - 设置分析
   - 确认并运行
   - 查看结果
3. 新增首页简介；
4. 新增数据上传/选择 step，占位支持：
   - 上传 ZIP
   - 输入本地数据目录
   - 使用示例数据
5. 新增预处理设置 step：
   - Slice Timing
   - Realignment
   - Coregistration
   - Segmentation
   - Normalization
   - Smoothing
   - Nuisance Regression
   - Temporal Filtering
   - 常用参数：TR、FWHM、filter band、nuisance model
6. 新增分析设置 step：
   - 是否进行后续分析
   - ALFF/fALFF
   - ReHo
   - Functional Connectivity
   - Group Summary
   - Report Export
7. 新增确认并运行 step：
   - 显示配置摘要
   - 暂时调用现有 Quickstart Demo API 作为演示运行
8. 新增结果查看 step：
   - 加载 latest quickstart demo
   - 显示状态、subjects、stages、report
9. 将旧的复杂面板全部移入 AdvancedModePanel；
10. App.tsx 默认显示用户模式，右上角可切换 Advanced Mode；
11. 不删除旧组件；
12. 不改动 backend；
13. 保持 TypeScript 编译通过。

新增文件建议：
- frontend/src/components/workflow/WorkflowShell.tsx
- frontend/src/components/workflow/WorkflowStepper.tsx
- frontend/src/components/workflow/IntroCard.tsx
- frontend/src/components/workflow/DataUploadStep.tsx
- frontend/src/components/workflow/PreprocessingConfigStep.tsx
- frontend/src/components/workflow/AnalysisConfigStep.tsx
- frontend/src/components/workflow/RunConfirmStep.tsx
- frontend/src/components/workflow/ResultsOverviewStep.tsx
- frontend/src/components/workflow/AdvancedModePanel.tsx
- frontend/src/state/workflowTypes.ts
- frontend/src/state/defaultWorkflowConfig.ts

修改：
- frontend/src/App.tsx
- frontend/src/api.ts 如有必要
- frontend/src/App.css 或 index.css

完成后请总结：
1. 新增了哪些文件
2. 修改了哪些文件
3. 用户模式如何操作
4. 高级模式如何进入
5. 旧组件如何保留
6. 当前还有哪些 backend API 后续需要补齐
```

---

# 19. 结论

当前 MedImage Agent 前端的问题不是功能不够，而是功能暴露方式不适合用户。

重构方向应是：

```text
开发者调试台
→ 用户任务向导
```

推荐最终用户路径：

```text
简介
→ 上传数据
→ 设置预处理
→ 设置分析
→ 确认运行
→ 查看结果
```

推荐开发者路径：

```text
高级模式
→ Pipeline / Agent / Node / API / Logs / Contracts / Release Readiness
```

这样既不会浪费已经完成的大量底层功能，又能让普通用户真正理解和使用这个系统。
