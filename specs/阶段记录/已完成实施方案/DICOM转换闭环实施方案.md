# MedImage Agent：DICOM→NIfTI 功能最终实施计划

## 1. 文档信息

- 项目：MedImage Agent WebUI App
- 仓库：`xlongwu/MedImage_Agent_WebUI_App`
- 核心目标：在桌面端页面中完成可用、可审计、默认安全关闭的 DICOM→NIfTI 转换闭环
- 技术路线：内置 `dcm2niix.exe`，由 Python 后端通过结构化参数和 `subprocess` 调用
- 任务模式：Feature Bundle Mode
- 目标平台：Windows 桌面应用
- 使用边界：科研用途，不用于临床诊断或临床决策

---

## 2. 最终技术决策

本功能采用以下实现方式：

```text
MedImage Agent 桌面应用
    ↓
前端发起转换请求
    ↓
FastAPI 后端执行安全检查与审批
    ↓
调用应用内置的 dcm2niix.exe
    ↓
生成 BIDS 风格 NIfTI、JSON sidecar 和执行证据
    ↓
注册转换结果并刷新项目状态
```

`dcm2niix.exe` 作为 MedImage Agent 的内部转换引擎随桌面程序分发。用户不需要单独下载、安装、配置或直接操作该程序。

后端调用必须满足以下约束：

- 使用参数列表调用，不拼接 shell 命令；
- `shell=False`；
- 输入目录只读；
- 输出目录必须位于项目 workspace 下；
- 输出目录不得位于 rawdata 内；
- 每个转换映射独立执行并记录结果；
- 捕获返回码、stdout、stderr 和耗时；
- 转换失败时执行清理或隔离；
- 转换前后验证 rawdata 未发生变化；
- 保存 manifest、provenance、audit 和 checksum 证据。

---

## 3. 为什么选择内置 dcm2niix.exe

### 3.1 产品层面

从用户视角，`dcm2niix.exe` 不作为独立工具暴露，而是 MedImage Agent 内部的 DICOM 转换算法组件。

用户只需执行：

```text
导入 DICOM
→ 审核转换计划
→ 点击 Convert DICOM to NIfTI
→ 查看转换结果
```

### 3.2 工程层面

相较于自行使用 `pydicom + nibabel` 重写转换逻辑，dcm2niix 已覆盖大量实际 MRI DICOM 兼容问题，包括：

- 多厂商私有字段；
- Siemens mosaic；
- Enhanced Multi-frame DICOM；
- 图像方向和 affine；
- 缩放参数；
- 4D 序列重建；
- BIDS JSON sidecar；
- 多 echo、phase encoding 和 diffusion 元数据；
- 异常序列、localizer 和重复 acquisition。

### 3.3 安全与稳定性

独立进程模式更适合当前项目：

- 原生程序崩溃不会直接破坏 Python 主进程；
- 可设置超时；
- 可捕获标准输出和错误输出；
- 可记录工具版本和二进制 SHA256；
- 可针对单个映射失败进行隔离；
- 可执行清理、回滚和失败重试；
- 易于纳入 Approval Gate 和审计体系。

---

## 4. 功能交付范围

### 4.1 本轮必须完成

1. 将 `dcm2niix.exe` 打包进 Windows 桌面应用。
2. 后端能够稳定发现并验证内置转换器。
3. DICOM Preflight 只检查 DICOM 转换相关条件。
4. 前端能够审核转换映射。
5. 用户能够完成转换审批。
6. 页面出现真实的 `Convert DICOM to NIfTI` 按钮。
7. 后端执行真实 dcm2niix 转换。
8. 输出 BIDS 风格 `.nii.gz` 和 `.json`。
9. 记录执行日志、manifest、provenance 和 checksum。
10. 转换成功后刷新 Dashboard、Viewer 和项目状态。
11. 支持失败、部分成功和阻断状态。
12. 完成真实 DemoData 端到端验证。

### 4.2 本轮不包含

- SPM、DPABI、MATLAB 预处理；
- Slice Timing、Realignment、Normalization；
- ALFF、ReHo、功能连接计算；
- PACS、DICOMweb 或医院影像系统接入；
- 自研 DICOM→NIfTI 算法；
- macOS/Linux 打包；
- 批量集群调度；
- 临床用途。

---

## 5. 目标用户流程

### 5.1 正常流程

```text
1. 用户选择包含 FunRaw/T1Raw 的目录
2. 系统识别 DICOM 文件、受试者和序列
3. 系统生成 DICOM→BIDS 映射
4. 用户审核受试者、模态和目标文件名
5. 系统检查：
   - dcm2niix 是否可用
   - 输出路径是否安全
   - 磁盘空间是否足够
   - 映射是否完整
6. 用户确认：
   - 映射已审核
   - rawdata 只读
   - 仅科研使用
   - 接受外部转换器执行
   - 接受失败清理策略
7. 系统创建审批包和执行记录
8. 用户点击 Convert DICOM to NIfTI
9. 后端依次执行转换
10. 页面显示执行进度和每个映射结果
11. 系统校验输出文件和 rawdata
12. 成功后注册 converted BIDS
13. Dashboard、Viewer 和 QC 入口自动刷新
```

### 5.2 DemoData 预期输出

```text
converted_bids/
├── sub-001/
│   ├── anat/
│   │   ├── sub-001_T1w.nii.gz
│   │   └── sub-001_T1w.json
│   └── func/
│       ├── sub-001_task-rest_bold.nii.gz
│       └── sub-001_task-rest_bold.json
├── sub-002/
│   ├── anat/
│   └── func/
└── sub-003/
    ├── anat/
    └── func/
```

预期核心结果：

- DICOM 文件：1,104；
- 受试者：3；
- 转换映射：6；
- NIfTI：6；
- JSON sidecar：至少 6；
- rawdata 文件数量保持 1,104；
- rawdata checksum 不变。

---

## 6. 当前已有能力

仓库已经具备以下基础，不应重复开发：

- FunRaw/T1Raw 数据识别；
- 受试者编号标准化；
- 6 条 DICOM→BIDS 映射生成；
- Conversion Dry-Run；
- dcm2niix 命令模板；
- 输出路径安全校验；
- 实际 dcm2niix 执行服务；
- public execute endpoint；
- rawdata checksum-before / after；
- rollback plan；
- output manifest；
- execution provenance；
- audit execution start / final；
- DemoData 真实 E2E 测试框架；
- converted BIDS 注册为 preprocessing input 的接口。

因此本轮开发重点不是重写转换器，而是打通并修正现有能力之间的产品链路。

---

## 7. 原始未完成清单闭环状态

本节承接审查后得到的 6 个核心阻断项。闭环判定以当前代码、测试和本轮修改为准；不再把这些项作为仍阻断事项重复列入后续计划。

| 原始清单项 | 需要修改的文件或模块 | 本轮补充、修改或核对内容 | 完成判定标准 | 当前状态 |
|---|---|---|---|---|
| 7.1 桌面程序找不到 dcm2niix | `desktop/resources/tools/windows-x64/`、`desktop/packaging/pyinstaller_backend.spec`、`desktop/resources/tools/README.md`、`src/backend/app/runtime/desktop_config.py`、`src/backend/app/services/dicom_conversion_execution.py`、本文档 | 核对已有 bundled 资源目录、许可证、SHA256、PyInstaller `datas` 打包配置、desktop config capability、运行时探测顺序；在本文档补齐闭环证据。 | 开发/打包资源路径可被探测；`--version` 和 SHA256 可记录；找不到时返回 `unavailable/blocked` 类清晰状态，不误报为用户禁用。 | 已完成 |
| 7.2 DICOM 转换与 MATLAB/SPM 门控错误耦合 | `src/backend/app/schemas/dicom_conversion_execution.py`、`src/backend/app/schemas/dicom_conversion_public_execution.py`、`src/backend/app/services/dicom_conversion_execution.py`、相关测试、本文档 | 核对 DICOM 专用 flags 已限定为 `MEDIMAGE_ENABLE_DICOM_CONVERSION`、`MEDIMAGE_ENABLE_REVIEWED_EXECUTION`、`MEDIMAGE_ALLOW_USER_DATA_CONVERSION`；public endpoint 只额外要求 `MEDIMAGE_ALLOW_PUBLIC_DICOM_CONVERSION_ENDPOINT`；MATLAB/SPM/real preprocessing 不再作为 DICOM preflight 阻断项。 | MATLAB/SPM 未配置时，只要 DICOM 专用条件满足，DICOM preflight 可进入 review/ready 路径；默认用户数据执行仍关闭。 | 已完成 |
| 7.3 Persist review package 只保存 blocked 草稿 | `src/backend/app/api/conversion_routes.py`、`src/backend/app/schemas/dicom_conversion_prepare.py`、`src/backend/app/services/dicom_conversion_prepare.py`、`src/frontend/src/hooks/useDicomConversionWorkflow.ts`、`src/frontend/src/components/DicomConversionExecutePanel.tsx`、`src/frontend/src/components/DicomConversionReviewPanel.tsx`、相关测试、本文档 | 保留旧 `persist-plan` 作为草稿兼容路径；新增并接入 canonical `POST /api/projects/{project_id}/dicom-conversion/prepare`。前端 prepare flow 收集 8 项用户确认，后端自动完成 preflight、dcm2niix 探测、checksum-before、rollback、approval、audit preview、run reservation，并返回权威 readiness 与 `conversion_run_id`。 | 页面不再只能保存 `approved=false` 的 blocked 草稿；用户完成确认后可通过 prepare endpoint 获得 approved/ready 方向的 conversion run 与证据路径。 | 已完成 |
| 7.4 Release Readiness 状态没有传递给 ExecutePanel | `src/frontend/src/components/DicomConversionReviewPanel.tsx`、`src/frontend/src/components/DicomConversionExecutePanel.tsx`、`src/frontend/src/hooks/useDicomConversionWorkflow.ts`、`tests/unit/test_dicom_conversion_frontend_execute_ui.py`、本文档 | 将 release readiness 提升到 `DicomConversionReviewPanel` 父级状态；`ReleaseReadinessSection` 通过 `onReadinessChange` 写回父级；同一 `releaseReadiness` 对象传入 `DicomConversionExecutePanel`。prepare 响应也通过 `onPrepared` 回传父级并更新 active conversion run。 | Readiness 查询结果和 ExecutePanel 使用同一父级状态；prepare 产生的 `conversion_run_id` 可驱动后续 readiness/execute UI。 | 已完成 |
| 7.5 Readiness 依赖扫描源码 | `src/backend/app/services/dicom_conversion_release_readiness.py`、`tests/unit/test_dicom_conversion_release_readiness.py`、本文档 | 删除后端对 `src/frontend/...` 源码文件的扫描；public endpoint 状态改为检查运行时 `conversion_routes.router`；frontend execute UI 状态改为读取显式 runtime/env/config 信号：`MEDIMAGE_FRONTEND_DICOM_EXECUTE_UI_ENABLED`、`MEDIMAGE_DICOM_EXECUTE_UI_ENABLED`、`VITE_ENABLE_DICOM_EXECUTE_UI` 或 desktop config。 | 桌面打包后 readiness 不依赖源码文件是否存在；单测断言 `_is_frontend_execute_button_present()` 不使用 `open()` 或前端源码路径。 | 已完成 |
| 7.6 转换成功后项目状态未形成闭环 | `src/backend/app/services/dicom_conversion_result_registration.py`、`src/backend/app/api/conversion_routes.py`、`src/frontend/src/components/DicomConversionExecutePanel.tsx`、`src/frontend/src/lib/api/dicom.ts`、`tests/unit/test_dicom_conversion_result_registration.py`、本文档 | 修正前端注册成功结果时使用 `output_manifest_path` 和 `execution_provenance_path`；后端注册服务更新 converted BIDS、NIfTI/subject/BOLD/T1w 计数、checksum、preprocessing handoff、Dashboard/Viewer 刷新信号，并新增 `recent_activity` 与 `results_artifacts` metadata。 | 成功或 partial 后，项目 metadata 可驱动 Dashboard/Viewer/Preprocessing/Recent Activity/Results 刷新；测试验证 NIfTI 计数、converted BIDS、Recent Activity、Results artifact 和 preprocessing input。 | 已完成 |

### 7.1 dcm2niix 打包与探测闭环

当前仓库已具备：

- `desktop/resources/tools/windows-x64/dcm2niix.exe`、`LICENSE.txt`、`dcm2niix.sha256` 资源位；
- `desktop/packaging/pyinstaller_backend.spec` 将 `desktop/resources/tools/windows-x64/` 中的文件打入 `resources/tools/windows-x64/`；
- `desktop/resources/tools/README.md` 记录固定版本、SHA256、release/build 阶段放置规则和运行时发现顺序；
- `src/backend/app/runtime/desktop_config.py:get_dicom_conversion_capability()` 返回 converter availability、path、version、SHA256、strategy；
- `src/backend/app/services/dicom_conversion_execution.py:_detect_dcm2niix_runtime()` 覆盖 desktop config、env、conda/mamba、PATH、bundled resource、legacy dev path，并记录 expected version 与 SHA256。

### 7.2 DICOM 专用门控闭环

当前 DICOM preflight 只要求 DICOM 转换专用条件：

```text
MEDIMAGE_ENABLE_DICOM_CONVERSION
MEDIMAGE_ENABLE_REVIEWED_EXECUTION
MEDIMAGE_ALLOW_USER_DATA_CONVERSION
```

公开执行 endpoint 额外要求：

```text
MEDIMAGE_ALLOW_PUBLIC_DICOM_CONVERSION_ENDPOINT
```

以下变量不再作为 DICOM→NIfTI preflight 阻断项：

```text
MEDIMAGE_ENABLE_REAL_PREPROCESSING
MEDIMAGE_MATLAB_ENABLED
MEDIMAGE_SPM_SMOKE_ENABLED
```

它们仍属于后续 preprocessing / SPM / MATLAB 路径的安全门控。对 DICOM 转换而言，MATLAB/SPM 未启用是安全状态，不是阻断原因。

### 7.3 Prepare 与 approval 闭环

旧的 `Persist review package` 语义被保留为 draft/compatibility 路径，不再承担完整执行准备职责。完整闭环由 canonical prepare endpoint 承担：

```text
POST /api/projects/{project_id}/dicom-conversion/prepare
```

后端一次调用完成：

1. 重新运行 DICOM preflight；
2. 探测并记录 dcm2niix；
3. 校验 mapping、output root 和磁盘空间；
4. 生成 rawdata checksum-before；
5. 生成 rollback dry-run plan；
6. 生成 approval record；
7. 生成 audit preview；
8. 持久化 preflight、mapping、command templates；
9. 预留 conversion run；
10. 返回 `technical_ready`、`approval_ready`、`execution_ready`、`next_action` 和证据路径。

前端 `useDicomConversionWorkflow()` 负责 operator confirmations、prepare 调用和 `conversion_run_id` 状态，不要求用户手工填写系统可验证字段。

### 7.4 Readiness 状态传递闭环

Readiness 现在由父级 `DicomConversionReviewPanel` 持有：

```text
ReleaseReadinessSection
  → onReadinessChange(setReleaseReadiness)
  → DicomConversionExecutePanel(readiness={releaseReadiness})
```

Prepare 成功后：

```text
DicomConversionExecutePanel
  → onPrepared(response)
  → setPreparedConversionRunId(response.conversion_run_id)
  → activeConversionRunId
```

因此 ExecutePanel 接收的不再是永远为空的父级 readiness，prepare 产生的新 run 也能进入后续 readiness/execute 流程。

### 7.5 Runtime readiness 闭环

Release readiness 不再读取前端源码文件来猜测按钮是否存在。当前规则是：

- public conversion endpoint：检查已注册的 runtime router；
- frontend execute UI：检查显式 runtime/env/config 信号；
- SPM/DPABI/MATLAB：保持默认 disabled；
- full preprocessing：保持与 DICOM 转换解耦；
- disk、rollback、approval/audit：由后端服务检查。

这避免了桌面打包后源码文件缺失、压缩或路径变化导致 readiness 误判。

### 7.6 项目状态闭环

转换成功或 partial 后，前端调用：

```text
POST /api/projects/{project_id}/dicom-conversion/register-result
```

注册服务更新：

- `last_conversion_*` summary；
- `converted_bids_available` 和 `converted_bids_dir`；
- NIfTI、BOLD、T1w、subject 计数；
- manifest / provenance 路径；
- `recent_activity` 中的 DICOM conversion 记录；
- `results_artifacts` 中的 manifest 和 provenance；
- preprocessing input handoff；
- `dashboard_refresh_required` 和 `viewer_refresh_required`。

前端注册 payload 使用 public execute response 的权威字段：

```text
output_manifest_path
execution_provenance_path
checksum_verified
```

因此 Dashboard、Viewer、Recent Activity、Results 和 Preprocessing 入口具备统一的项目 metadata 信号。

---

## 8. 目标架构

```text
Frontend
  ├── DICOM Detection
  ├── Mapping Review
  ├── Conversion Readiness
  ├── Approval Form
  ├── Execute / Progress
  └── Result Summary
        ↓ HTTP
DICOM Conversion Routes
        ↓
DICOM Conversion Orchestrator
  ├── Tool Capability
  ├── Preflight
  ├── Mapping Validation
  ├── Approval Gate
  ├── Audit Preparation
  ├── Checksum Snapshot
  ├── Rollback Plan
  └── Execute
        ↓
Dcm2niix Process Adapter
  ├── Structured argv
  ├── shell=False
  ├── timeout
  ├── stdout/stderr
  └── return-code validation
        ↓
Workspace / converted_bids
  ├── NIfTI
  ├── JSON sidecars
  ├── logs
  ├── manifest
  ├── provenance
  ├── checksums
  └── audit records
```

---

## 9. dcm2niix 打包方案

### 9.1 资源目录

建议在仓库中建立：

```text
desktop/
└── resources/
    └── tools/
        └── windows-x64/
            ├── dcm2niix.exe
            ├── LICENSE.txt
            └── dcm2niix.sha256
```

注意：

- 二进制文件是否直接纳入 Git 仓库，需要结合仓库策略和许可证决定；
- 也可在 release/build 阶段从固定、校验过的发布资产复制；
- 不允许构建过程中下载未固定版本的最新文件；
- 必须锁定版本和 SHA256。

### 9.2 桌面安装目录

打包后预期：

```text
MedImage Agent/
├── MedImage Agent.exe
├── resources/
│   └── tools/
│       └── dcm2niix.exe
└── backend/
    └── medimage-backend.exe
```

### 9.3 工具发现顺序

后端统一采用：

```text
1. 桌面应用显式传入的 resource path
2. desktop config 中的 dcm2niix_path
3. MEDIMAGE_DCM2NIIX_PATH
4. 当前 Python/conda 环境
5. 系统 PATH
6. 项目开发目录 tools/dcm2niix.exe
7. 未找到时返回 unavailable
```

### 9.4 工具探测结果

统一返回：

```json
{
  "available": true,
  "status": "available",
  "path": "C:/.../resources/tools/dcm2niix.exe",
  "version": "v1.0.x",
  "sha256": "...",
  "strategy": "bundled_resource",
  "error": null
}
```

### 9.5 启动时校验

桌面应用启动后应执行只读探测：

```text
dcm2niix.exe --version
```

校验：

- 文件存在；
- 可执行；
- 返回版本信息；
- SHA256 与应用声明匹配；
- 不执行任何用户数据转换。

---

## 10. 配置设计

### 10.1 Desktop Config

新增：

```json
{
  "dicom_conversion": {
    "enabled": false,
    "dcm2niix_path": "",
    "prefer_bundled": true,
    "overwrite_policy": "fail_if_exists",
    "timeout_seconds": 1800
  }
}
```

### 10.2 Capability API

新增或扩展 capability 接口：

```json
{
  "dicom_conversion": {
    "enabled": true,
    "converter_available": true,
    "converter_name": "dcm2niix",
    "converter_path": "...",
    "converter_version": "...",
    "converter_sha256": "...",
    "execution_supported": true
  }
}
```

### 10.3 Settings 页面

显示：

- DICOM converter status；
- dcm2niix version；
- resource strategy；
- bundled / custom path；
- Detect again；
- Restore bundled converter；
- conversion enabled 状态。

普通用户默认使用 bundled converter，不要求手工选路径。

---

## 11. 后端门控重构

### 11.1 DICOM 专用必需条件

建议最小必需条件为：

```text
MEDIMAGE_ENABLE_DICOM_CONVERSION
MEDIMAGE_ENABLE_REVIEWED_EXECUTION
MEDIMAGE_ALLOW_USER_DATA_CONVERSION
```

### 11.2 HTTP execute endpoint 附加条件

仅当开放页面/API 执行时要求：

```text
MEDIMAGE_ALLOW_PUBLIC_DICOM_CONVERSION_ENDPOINT
```

### 11.3 从 DICOM Preflight 移除

以下条件不再作为 DICOM 转换阻断项：

```text
MEDIMAGE_ENABLE_REAL_PREPROCESSING
MEDIMAGE_MATLAB_ENABLED
MEDIMAGE_SPM_SMOKE_ENABLED
```

这些条件应仅用于后续预处理模块。

### 11.4 始终保持的禁止条件

DICOM 转换执行期间必须确保：

```text
SPM execution disabled
DPABI execution disabled
MATLAB execution disabled
full preprocessing disabled
```

“未启用 MATLAB/SPM”应是安全状态，而不是阻断原因。

---

## 12. Preflight 状态设计

建议统一为：

| 状态 | 含义 |
|---|---|
| `unavailable` | dcm2niix 不存在或不可执行 |
| `disabled` | 转换功能开关未启用 |
| `blocked` | 输入、输出、安全或映射不合法 |
| `review_required` | 技术检查通过，等待用户审核 |
| `ready` | 技术检查和审批均通过 |
| `running` | 正在执行 |
| `succeeded` | 全部映射成功 |
| `partial` | 部分映射成功 |
| `failed` | 全部或关键步骤失败 |

Preflight 返回应明确区分：

```json
{
  "technical_ready": true,
  "approval_ready": false,
  "execution_ready": false,
  "status": "review_required",
  "next_action": "approve_conversion_plan"
}
```

---

## 13. 审批与执行准备编排

### 13.1 新增统一准备接口

建议新增：

```text
POST /api/projects/{project_id}/dicom-conversion/prepare
```

输入：

```json
{
  "approved_by": "operator",
  "selected_mapping_ids": ["mapping-1", "mapping-2"],
  "overwrite_policy": "fail_if_exists",
  "confirmations": {
    "mappings_reviewed": true,
    "rawdata_readonly": true,
    "research_use_only": true,
    "no_clinical_use": true,
    "external_converter": true,
    "rollback_policy": true,
    "risk_acknowledgement": true,
    "confirm_execution": true
  }
}
```

### 13.2 后端自动完成

该接口内部完成：

1. 重新运行 Preflight；
2. 验证 dcm2niix；
3. 验证映射未变化；
4. 验证输出路径；
5. 验证磁盘空间；
6. 计算 rawdata checksum-before；
7. 创建 rollback plan；
8. 生成完整 conversion approval record；
9. 生成 audit preview；
10. 持久化 review package；
11. 创建 conversion run；
12. 返回权威 readiness。

### 13.3 用户确认与系统验证分离

用户确认：

- 已审核映射；
- 同意执行；
- rawdata 只读；
- 科研用途；
- 非临床用途；
- 接受外部转换器；
- 接受回滚策略；
- 接受执行风险。

系统验证：

- output root 是否安全；
- dcm2niix 是否存在；
- 版本是否可读取；
- 映射是否完整；
- checksum 是否生成；
- rollback plan 是否存在；
- 磁盘空间是否足够；
- 环境门控是否满足。

不得要求用户手工把系统可验证字段勾成 true。

---

## 14. 执行接口

### 14.1 推荐接口

```text
POST /api/projects/{project_id}/dicom-conversion/runs/{conversion_run_id}/execute
```

请求：

```json
{
  "approval_id": "...",
  "confirm_execution": true
}
```

### 14.2 执行前再次验证

执行前必须重新检查：

- conversion run 存在；
- approval 未过期；
- mapping snapshot 完整；
- dcm2niix 版本未变化；
- output root 仍安全；
- checksum-before 存在；
- rollback plan 存在；
- rawdata 目录仍存在；
- 输出目录不存在冲突；
- overwrite policy 可执行。

### 14.3 dcm2niix 调用

每个 mapping 使用：

```text
dcm2niix.exe
-z y
-b y
-f <bids_filename_without_extension>
-o <output_directory>
<input_dicom_directory>
```

具体参数以当前已验证模板为准。

调用规则：

```python
subprocess.run(
    argv,
    shell=False,
    capture_output=True,
    text=True,
    timeout=timeout_seconds,
    check=False,
)
```

### 14.4 成功判定

不能只依赖 return code。还需检查：

- return code 为 0；
- stdout/stderr 不包含明确错误；
- 预期 `.nii.gz` 存在；
- 预期 `.json` 存在；
- 文件大小大于 0；
- 输出位于允许目录；
- 输出文件可被 NIfTI 读取器打开；
- manifest 中没有 missing required output。

---

## 15. 失败处理

### 15.1 单映射失败

记录：

```json
{
  "mapping_id": "...",
  "subject_id": "sub-002",
  "modality": "func",
  "status": "failed",
  "return_code": 1,
  "stderr_excerpt": "...",
  "retryable": true
}
```

### 15.2 整体状态

- 6/6 成功：`succeeded`
- 1–5 条成功：`partial`
- 0 条成功：`failed`
- rawdata 变化：`safety_violation`

### 15.3 回滚策略

默认：

```text
fail_if_exists + quarantine_partial_outputs
```

失败后：

- 不删除 rawdata；
- 将本轮新生成的部分文件移动到 run quarantine 目录，或按现有合同执行清理；
- 保留日志、failure record 和 rollback evidence；
- 不将失败输出注册为可用 converted BIDS。

---

## 16. 前端工作流

### 16.1 状态机

```typescript
type DicomConversionUiState =
  | "not_planned"
  | "planning"
  | "converter_unavailable"
  | "review_required"
  | "preparing"
  | "ready"
  | "converting"
  | "succeeded"
  | "partial"
  | "failed"
  | "blocked";
```

### 16.2 按钮设计

#### 初始状态

```text
Generate conversion plan
```

#### 转换器缺失

```text
DICOM converter unavailable
Open Settings
Retry detection
```

#### 技术检查通过

```text
Review 6 mappings
Approve conversion plan
```

#### 准备完成

```text
Convert DICOM to NIfTI
```

#### 执行中

```text
Converting 2 / 6
Current: sub-001 / T1w
```

#### 成功后

```text
Conversion completed
Open converted dataset
Continue to NIfTI QC
```

### 16.3 替换当前易混淆文案

将：

```text
Run conversion preflight
```

改为：

```text
Check conversion readiness
```

完成一次后改为：

```text
Refresh readiness
```

将：

```text
Persist review package
```

拆分为：

```text
Save review draft
Approve conversion plan
```

### 16.4 动态 Next Action

示例：

| 阻断原因 | Next Action |
|---|---|
| dcm2niix 缺失 | Open Settings |
| 转换关闭 | Enable DICOM conversion |
| mappings 为空 | Regenerate conversion plan |
| output root 不安全 | Reset output location |
| 等待审核 | Review and approve mappings |
| 准备完成 | Convert DICOM to NIfTI |
| 部分失败 | Review failed mappings |

---

## 17. Readiness 重构

### 17.1 权威状态来源

Readiness 只能来自后端运行时状态，不能通过扫描源码判断。

检查内容：

- converter capability；
- conversion feature enabled；
- mapping count；
- approval state；
- checksum-before；
- rollback plan；
- output root；
- disk space；
- audit package；
- current conversion run state。

### 17.2 前端状态统一

Review、Readiness 和 Execute 组件必须使用同一个 workflow controller 或 hook：

```text
useDicomConversionWorkflow(projectId)
```

负责：

- 当前 plan；
- 当前 conversion run；
- readiness；
- approval；
- execution status；
- refresh；
- prepare；
- execute；
- retry。

不允许多个组件分别维护互不一致的 readiness。

---

## 18. 执行进度

### 18.1 MVP 阶段

DemoData 规模较小，第一版可复用同步 HTTP 执行：

```text
点击 Convert
→ 页面进入 converting
→ 后端依次执行 6 条 mapping
→ 返回完整结果
```

### 18.2 后续异步化

后续支持大型数据集时改为：

```text
POST /dicom-conversion/runs/{id}/execute
GET  /dicom-conversion/runs/{id}
POST /dicom-conversion/runs/{id}/cancel
POST /dicom-conversion/runs/{id}/retry-failed
```

MVP 不应被异步任务系统重构拖延，但数据模型需要为未来保留：

- total；
- completed；
- failed；
- current mapping；
- started_at；
- estimated remaining；
- cancellation requested。

---

## 19. 转换结果与项目联动

转换成功后自动完成：

1. 扫描 converted BIDS；
2. 验证 3 个 BOLD 和 3 个 T1w；
3. 注册 converted output root；
4. 更新 project metadata；
5. 更新 converted subjects；
6. 更新 NIfTI files；
7. 更新 Data Readiness；
8. 更新 Viewer source；
9. 更新 Recent Activity；
10. 注册为后续 preprocessing input；
11. 在 Results 中显示 manifest、provenance 和日志。

### 19.1 Dashboard 预期变化

```text
Converted subjects: 0 → 3
NIfTI files: 0 → 6
BIDS/NIfTI: Ready
Preprocessing: Available
Environment: Converter available
```

### 19.2 Viewer 预期变化

从：

```text
Fallback preview
No NIfTI image sources
```

变为：

```text
Source: converted_bids
Series: sub-001_task-rest_bold
```

---

## 20. 数据与证据文件

每个 conversion run 建议结构：

```text
conversion_runs/<run_id>/
├── approval_record.json
├── audit_preview.json
├── audit_execution_start.json
├── audit_execution_final.json
├── preflight_snapshot.json
├── mapping_snapshot.json
├── command_templates.json
├── rawdata_checksum_before.json
├── rawdata_checksum_after.json
├── rawdata_checksum_comparison.json
├── rollback_plan_dry_run.json
├── rollback_result.json
├── output_manifest.json
├── execution_provenance.json
├── failure_record.json
└── logs/
    ├── dicom_to_nifti_stdout.log
    └── dicom_to_nifti_stderr.log
```

---

## 21. 实施阶段

## Phase 0：建立基线

### 工作内容

- 记录当前 commit；
- 运行后端、前端和 DICOM focused tests；
- 保存当前本地测试截图和结果；
- 确认 DemoData 为 1,104 DICOM、3 subjects、6 mappings；
- 创建 Feature Bundle 任务文档。

### 验收标准

- 当前行为可复现；
- 已知失败与新失败可区分；
- 不修改业务代码。

---

## Phase 1：内置 dcm2niix 与 capability

### 工作内容

- 固定 dcm2niix Windows 版本；
- 保存许可证和 SHA256；
- 将二进制加入桌面构建资源；
- 增加 resource path 传递；
- 统一后端 detection；
- 增加 capability API；
- Settings 展示 converter 状态。

### 验收标准

- 开发模式可识别；
- 打包模式可识别；
- 不依赖 conda activation；
- `--version` 正常；
- SHA256 可记录；
- 找不到时错误清晰。

---

## Phase 2：DICOM 门控修正

### 工作内容

- 建立 DICOM 专用 required flags；
- 移除 MATLAB/SPM/real preprocessing 阻断；
- 保留默认关闭；
- 明确 `unavailable/disabled/blocked/review_required/ready`；
- 修复 dcm2niix availability 状态显示。

### 验收标准

在 MATLAB/SPM 未配置的情况下，只要 DICOM 条件满足，Preflight 可以进入 `review_required`。

---

## Phase 3：审批与 prepare-execution

### 工作内容

- 新增 prepare schema；
- 新增 orchestration service；
- 创建独立 DICOM conversion routes；
- 自动生成 checksum-before；
- 自动生成 rollback plan；
- 持久化完整 approval/audit；
- 返回 conversion run readiness。

### 验收标准

页面提交一次审批后：

- conversion_run_id 存在；
- approval 为 approved；
- checksum-before 存在；
- rollback plan 存在；
- audit package 存在；
- readiness 为 ready。

---

## Phase 4：前端工作流

### 工作内容

- 新增 workflow hook/controller；
- 统一 plan、readiness、approval 和 execute 状态；
- 修复 readiness 状态传递；
- 增加审批表单；
- 增加真实转换按钮；
- 增加 loading、blocked、partial、failed、succeeded 状态；
- 动态生成 Next Action。

### 验收标准

用户无需调用 API 或手工创建 JSON，即可从页面完成审批并进入 ready。

---

## Phase 5：真实执行与结果注册

### 工作内容

- 接通 ExecutePanel 与 execute endpoint；
- 复用现有 dcm2niix execution service；
- 校验每个 mapping 输出；
- 生成 manifest/provenance/audit；
- 验证 rawdata unchanged；
- 注册 converted BIDS；
- 刷新 Dashboard、Viewer、Recent Activity 和 Results。

### 验收标准

DemoData 生成：

- 6 NIfTI；
- 至少 6 JSON；
- rawdata 仍为 1,104；
- Dashboard 和 Viewer 使用真实转换结果。

---

## Phase 6：桌面打包与真实 E2E

### 工作内容

- 构建 PyInstaller backend；
- 构建 Electron Windows 包；
- 在干净 Windows 环境安装；
- 不安装 conda、不配置 PATH；
- 导入 DemoData；
- 从页面完成转换；
- 检查应用重启后状态恢复。

### 验收标准

安装后的应用能够独立完成真实 DICOM→NIfTI 转换。

---

## 22. 任务拆分

为避免单个任务过大，建议顺序拆分为 5 个实现任务。

### TASK 1：Bundled dcm2niix Capability

**目标**

将 dcm2niix 内置到桌面构建并统一后端探测。

**主要修改范围**

```text
desktop/packaging/pyinstaller_backend.spec
desktop/packaging/build_backend.ps1
desktop/electron/*
src/backend/app/runtime/desktop_config.py
src/backend/app/services/dicom_conversion_execution.py
相关测试
```

**验收**

- bundled resource 可发现；
- version 和 SHA256 可获取；
- 未找到时不会误显示 disabled；
- 开发和打包路径均覆盖。

---

### TASK 2：DICOM-specific Gate Cleanup

**目标**

移除 MATLAB/SPM 对 DICOM 转换的错误依赖。

**主要修改范围**

```text
src/backend/app/schemas/dicom_conversion_execution.py
src/backend/app/schemas/dicom_conversion_public_execution.py
src/backend/app/services/dicom_conversion_execution.py
Preflight route/service
相关单元测试
```

**验收**

- DICOM flags 满足即可进入 review；
- MATLAB/SPM 保持关闭且不阻断；
- 默认仍不可执行用户数据。

---

### TASK 3：Prepare and Approval Orchestration

**目标**

建立一次调用即可完成审批准备的后端编排。

**主要修改范围**

```text
新增 dicom conversion domain routes
新增 prepare schema
新增 orchestration service
dicom_conversion_plan_persistence.py
dicom_conversion_release_approval.py
dicom_conversion_review_package.py
相关测试
```

**验收**

- 生成 approved conversion run；
- 生成 checksum、rollback、audit；
- readiness 可执行；
- blocked draft 和 approved plan 明确区分。

---

### TASK 4：Frontend Conversion Workflow

**目标**

形成可由用户操作的完整页面闭环。

**主要修改范围**

```text
DicomConversionReviewPanel.tsx
DicomConversionReleaseReadinessPanel.tsx
DicomConversionExecutePanel.tsx
src/frontend/src/lib/api/dicom.ts
frontend types
新增 workflow hook/controller
frontend tests
```

**验收**

- 页面能够审核、批准、执行；
- readiness 状态一致；
- next action 正确；
- 错误与部分成功可见。

---

### TASK 5：Result Registration and Desktop E2E

**目标**

完成转换后的项目联动和桌面真实验收。

**主要修改范围**

```text
converted BIDS registration
project metadata refresh
dashboard counts
viewer source refresh
recent activity
results/artifact UI
desktop packaging tests
integration E2E
```

**验收**

- DemoData 页面转换成功；
- 6 NIfTI；
- Viewer 加载；
- Dashboard 更新；
- rawdata 不变；
- 安装包独立运行。

---

## 23. 测试矩阵

### 23.1 工具探测

| 场景 | 预期 |
|---|---|
| bundled exe 存在 | available |
| desktop config custom path | available |
| env path | available |
| PATH | available |
| 文件不存在 | unavailable |
| 无执行权限 | unavailable |
| `--version` 失败 | version_failed |
| SHA256 不匹配 | blocked |

### 23.2 Preflight

| 场景 | 预期 |
|---|---|
| 6 mappings + converter available | review_required |
| mappings 为空 | blocked |
| output 在 rawdata 内 | blocked |
| output 不在 project 内 | blocked |
| 磁盘不足 | blocked |
| DICOM conversion disabled | disabled |
| MATLAB 未配置 | 不阻断 |
| SPM 未配置 | 不阻断 |

### 23.3 审批

| 场景 | 预期 |
|---|---|
| 未审核 mappings | blocked |
| 未确认 rawdata readonly | blocked |
| 未确认科研用途 | blocked |
| 未确认执行 | blocked |
| 完整确认 | ready |
| approval 过期 | blocked |
| mapping snapshot 改变 | blocked |

### 23.4 执行

| 场景 | 预期 |
|---|---|
| 6 mapping 全成功 | succeeded |
| 1 mapping 失败 | partial |
| 全部失败 | failed |
| timeout | failed + rollback |
| return code 非 0 | failed |
| 输出文件缺失 | failed |
| JSON sidecar 缺失 | failed |
| 输出到 rawdata | safety_violation |
| rawdata checksum 改变 | safety_violation |

### 23.5 前端

- converter unavailable；
- review required；
- preparing；
- ready；
- converting；
- succeeded；
- partial；
- failed；
- blocked；
- 刷新页面恢复状态；
- 应用重启恢复状态。

---

## 24. Fake dcm2niix 测试工具

CI 不应依赖真实 dcm2niix。建议创建 fake executable 或测试 runner，模拟：

1. 正常生成 NIfTI 和 JSON；
2. 某一 mapping 返回失败；
3. 超时；
4. 只生成 NIfTI 不生成 JSON；
5. 输出到错误目录；
6. stdout 包含 error；
7. return code 0 但输出无效；
8. 生成 partial output。

真实 dcm2niix E2E 保持 opt-in，仅在专门 Windows 测试环境运行。

---

## 25. 真实 E2E 验收步骤

```text
1. 安装 MedImage Agent Windows 包
2. 不安装 conda，不配置系统 PATH
3. 启动应用
4. Settings 显示 DICOM converter available
5. 导入 DemoData
6. 确认 1,104 DICOM、3 subjects、6 mappings
7. 审核 3 BOLD + 3 T1w 映射
8. 批准转换
9. 点击 Convert DICOM to NIfTI
10. 等待转换完成
11. 检查 6 个 .nii.gz
12. 检查至少 6 个 sidecar
13. 检查 manifest/provenance/audit/checksum
14. 检查 rawdata 仍为 1,104
15. 检查 Dashboard 显示 3 converted subjects
16. 检查 Viewer 加载真实 NIfTI
17. 重启应用
18. 检查转换结果和 run 状态仍可恢复
```

---

## 26. 风险控制

### 26.1 二进制再分发

风险：

- dcm2niix 版本和许可证管理；
- 发布资产来源；
- 二进制被替换。

控制：

- 锁定版本；
- 保存许可证；
- 固定 SHA256；
- 构建时校验；
- 运行时记录 SHA256。

### 26.2 杀毒软件误报

风险：

- Electron + PyInstaller + bundled native exe 可能触发安全软件。

控制：

- 避免运行时下载；
- 代码签名；
- 固定构建流程；
- 保留来源和校验值；
- 在干净 Windows 环境 smoke。

### 26.3 路径问题

风险：

- 空格、中文路径、长路径；
- AppData 路径；
- Windows path separator。

控制：

- 永远使用 argv list；
- 不拼 shell string；
- 使用 `Path.resolve()`；
- 测试空格和中文目录；
- 禁止 `..` path traversal。

### 26.4 大数据耗时

风险：

- 同步接口长时间阻塞。

控制：

- MVP 限制 subjects 数；
- 设置 per-mapping timeout；
- 页面提示不要关闭；
- 后续升级异步 run。

### 26.5 部分成功

风险：

- 3 个受试者中某个模态失败。

控制：

- mapping 级结果；
- 状态 `partial`；
- 不将不完整 subject 默认为可用；
- 提供 failed mappings 重试入口。

---

## 27. 优先级

| 优先级 | 工作项 |
|---|---|
| P0 | 将 dcm2niix 打包并可发现 |
| P0 | 移除 MATLAB/SPM 转换门控 |
| P0 | 实现完整 approval/prepare |
| P0 | 修复 readiness 状态流 |
| P0 | 页面真实执行按钮 |
| P1 | 转换结果注册与 Dashboard 刷新 |
| P1 | Viewer 加载 converted NIfTI |
| P1 | fake executable CI 测试 |
| P1 | Windows 安装包 E2E |
| P2 | 异步任务和取消 |
| P2 | failed mapping 重试 |
| P2 | macOS/Linux 支持 |

---

## 28. 时间估算

以单人顺序实施计算：

| 阶段 | 预计时间 |
|---|---:|
| 基线和任务文档 | 0.5 天 |
| bundled dcm2niix + capability | 1–1.5 天 |
| 门控修正 | 0.5–1 天 |
| prepare/approval orchestration | 1–1.5 天 |
| 前端状态机与执行入口 | 1–1.5 天 |
| 结果注册和页面刷新 | 0.5–1 天 |
| 测试、打包和 E2E | 1–1.5 天 |
| 合计 | 5.5–8 天 |

异步任务、取消和失败重试不包含在该 MVP 时间内。

---

## 29. 最终验收标准

只有同时满足以下条件，DICOM→NIfTI 功能才算交付完成：

- [ ] 用户可从页面发起转换；
- [ ] 不需要手工调用 API；
- [ ] 不需要安装 conda；
- [ ] 不需要配置 PATH；
- [ ] dcm2niix 随桌面程序分发；
- [ ] 后端验证 dcm2niix version 和 SHA256；
- [ ] MATLAB/SPM 未配置时不阻断转换；
- [ ] 默认情况下用户数据执行仍关闭；
- [ ] 用户必须审核 mappings；
- [ ] 用户必须显式确认执行；
- [ ] 输出目录位于 project workspace；
- [ ] 输出不进入 rawdata；
- [ ] subprocess 使用 shell=False；
- [ ] 6 条 DemoData mapping 全部执行；
- [ ] 生成 6 个 NIfTI；
- [ ] 生成至少 6 个 JSON sidecar；
- [ ] rawdata DICOM 数量仍为 1,104；
- [ ] rawdata checksum 一致；
- [ ] manifest 存在；
- [ ] provenance 存在；
- [ ] audit start/final 存在；
- [ ] checksum comparison 存在；
- [ ] Dashboard 显示 3 converted subjects；
- [ ] Dashboard 显示 6 NIfTI；
- [ ] Viewer 能加载转换结果；
- [ ] Recent Activity 有转换记录；
- [ ] 应用重启后可恢复结果；
- [ ] 失败和 partial 状态有明确提示；
- [ ] 安装包在干净 Windows 环境通过 E2E。

---

## 30. 推荐开发顺序

```text
TASK 1：内置 dcm2niix
    ↓
TASK 2：修正 DICOM 门控
    ↓
TASK 3：审批与 prepare 编排
    ↓
TASK 4：前端执行工作流
    ↓
TASK 5：结果注册与桌面 E2E
```

必须坚持：

```text
一个任务
→ 一个 owner agent
→ 一个 branch/worktree
→ 一个 coherent diff
→ 完成后独立 review
```

不应让多个实现代理同时编辑同一任务分支。

---

## 31. 最终交付定义

最终用户体验应为：

```text
MedImage Agent 已内置 DICOM 转换器。
用户导入 FunRaw/T1Raw 后，系统自动生成转换映射。
用户审核并批准后，点击一个明确的转换按钮即可生成
BIDS 风格 NIfTI 和 JSON sidecar。
整个过程保持 rawdata 只读，并保存完整审计证据。
```

这既满足当前“尽快实现 DICOM→NIfTI”的核心目标，也保留了 MedImage Agent 原有的确定性执行、安全门控、审计和科研可复现性。
