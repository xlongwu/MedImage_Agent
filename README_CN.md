# MedImage Agent

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136%2B-green)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61dafb)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0%2B-3178c6)](https://www.typescriptlang.org/)
[![Node](https://img.shields.io/badge/Node-24%2B-339933)](https://nodejs.org/)

![Tests](https://img.shields.io/badge/tests-2426%20passed-brightgreen)  ![Release](https://img.shields.io/badge/release-v0.3.0--rc1-blue)

[English](README.md) | **中文**

MedImage Agent 是一个面向静息态 fMRI（rs-fMRI）研究的**确定性 Plan-then-Execute 桌面端平台**。
LLM 仅负责规划和顾问，执行完全由 Pipeline Runtime 和注册节点 Runner 完成。
这是一个研究工程平台，**不用于临床诊断或医疗决策**。

**最新版本**：[v0.3.0-rc1](https://github.com/xlongwu/MedImage_Agent_WebUI_App/releases/tag/v0.3.0-rc1) — 桌面端 MVP Release Candidate（[发布说明](docs/releases/v0.3.0-rc1.md)）

---

## 目录

- [快速开始](#快速开始)
- [桌面应用](#桌面应用)
- [系统架构](#系统架构)
- [真实项目工作流](#真实项目工作流)
- [项目结构](#项目结构)
- [测试基线](#测试基线)
- [安全架构](#安全架构)
- [已知限制](#已知限制)
- [开发路线图](#开发路线图)
- [文档](#文档)

---

## 快速开始

### 环境要求

- Python 3.11+（已验证：`D:\Anaconda3\envs\mamba\python.exe`）
- Node.js 20+（已验证：v24.16.0）
- MATLAB + SPM12（可选，用于 SPM 预处理）
- CuPy（可选，用于 GPU 加速）

### 安装

```bash
pip install -r requirements.txt
cd src/frontend && npm install
```

### 启动（开发模式）

```bash
uvicorn src.backend.app.main:app --host 127.0.0.1 --port 8000
cd src/frontend && npm run dev

# 或一键启动：
start.bat           # Windows
./start.sh          # Linux/macOS
```

### 运行测试

```bash
D:\Anaconda3\envs\mamba\python.exe -m pytest --tb=short --basetemp=.pytest_tmp
```

---

## 桌面应用

v0.3.0-rc1 提供自包含的 Windows 桌面应用，运行时无需安装 Python 或 Node.js。

### 下载

| 格式 | 文件 | 大小 |
|---|---|---|
| **NSIS 安装包** | `MedImage Agent Setup.exe` | 112 MB |
| **便携版** | `MedImage Agent.exe` | 112 MB |

从 [GitHub Release 页面](https://github.com/xlongwu/MedImage_Agent_WebUI_App/releases/tag/v0.3.0-rc1) 下载。

### 工作原理

1. Electron 壳启动 → 提取 PyInstaller 后端 sidecar
2. 后端绑定到 `127.0.0.1` 的可用端口（默认 8765）
3. Electron 等待 `/api/health` → 加载 React 前端
4. 关闭应用时，后端 sidecar 被自动清理
5. 前端仅通过 HTTP API 通信，不直接访问文件系统

### 从源码构建

```powershell
npm --prefix src/frontend run build
powershell -File desktop/packaging/build_backend.ps1 -PythonExe "D:\Anaconda3\envs\mamba\python.exe"
powershell -File desktop/packaging/build_desktop.ps1 -DirOnly -ElectronRuntimeZip "desktop\electron\.electron-cache\manual-runtime\electron-v31.7.7-win32-x64.zip"
```

详见[桌面应用打包文档](docs/DESKTOP_APP_PACKAGING.md)。

---

## 系统架构

```
Frontend (React 18 + TypeScript + Vite)
    ↓ HTTP API
API Layer (FastAPI + Pydantic)
    ↓
Agent Runtime (Plan-then-Execute + Approval Gate)
    ↓
Pipeline Runtime (DAG Executor + Scheduler)
```

四层架构，自上而下。状态基于文件系统（项目元数据用 SQLite，运行状态用 JSON）。
LLM 仅提供建议；Pipeline Runtime 是唯一执行路径。

---

## 真实项目工作流

```
选择 BIDS/rawdata → 创建项目 → project_config.yaml + dataset_index.json
    → Plan Review（注入项目上下文）
    → 保存 reviewed plan（持久化到 SQLite）
    → execute-reviewed（Approval Gate 门控，唯一 run_id）
    → Run Summary / Artifacts
    → Run History UI → Artifact Preview（JSON/CSV/Markdown/text/log/NIfTI/MAT）
```

每次执行生成唯一的 `run_id`、summary JSON 和运行范围 artifact。
Rawdata 以只读方式引用，执行后验证未修改。

---

## 项目结构

```
MedImage_Agent/
├── src/
│   ├── backend/app/
│   │   ├── api/              # FastAPI 路由
│   │   ├── services/         # 业务逻辑（SQLite store、artifact 服务）
│   │   ├── planner/          # 项目上下文、reviewed plan store、approval、audit
│   │   ├── runtime/          # Pipeline executor、node registry、state store
│   │   ├── tools/            # 处理模块、QC、CLI runners
│   │   ├── schemas/          # Pipeline YAML schema 验证
│   │   └── advisor/          # LLM advisor 模块
│   └── frontend/
│       ├── src/components/   # React 面板（PlanReviewConsole、ProjectRunsPanel、run-history/*）
│       ├── electron/         # Electron main/preload/smoke-check
│       └── scripts/          # Smoke tests
├── desktop/
│   ├── electron/             # Electron 打包（main、preload、builder config、smoke）
│   └── packaging/            # PyInstaller specs、PowerShell 构建脚本
├── docs/
│   ├── releases/             # 发布说明和 SHA256SUMS
│   ├── DESKTOP_APP_PACKAGING.md
│   ├── REAL_PROJECT_RUN_LIFECYCLE.md
│   └── MVP_RELEASE_SMOKE_CHECKLIST.md
├── tests/
│   ├── unit/                 # 100+ 单元测试文件
│   └── integration/          # 安全冒烟测试、外部 BIDS 冒烟、contract 冒烟
├── examples/                 # Pipeline YAML 和项目配置
└── deploy/                   # Dockerfile 和 docker-compose
```

---

## 测试基线

| 指标 | 值 |
|---|---|
| Full pytest（历史 Phase 3 freeze） | **2915 passed, 1 skipped, 0 failed** |
| 最近聚焦验证 | **43 passed + 41 regression passed** |
| 前端 TypeScript | `tsc --noEmit` ✅ |
| 前端 Vite build | 106 modules, Vite production build ✅ |
| Electron smoke check | 51/51 ✅ |
| GUI 桌面启动 | Windows 10/11 验证通过 ✅ |
| FunRaw/T1Raw DICOM 冒烟 | 1104 DICOM, rawdata 不变 ✅ |
| 测试环境 | `D:\Anaconda3\envs\mamba\python.exe` (Python 3.11.15) |

预期 skip：`pydicom`、`cupy`、`MEDIMAGE_EXTERNAL_BIDS_SMOKE_DIR`。
历史基线已标注；引用具体数字前请用最新 pytest 运行确认。

---

## 安全架构

| 规则 | 机制 |
|---|---|
| Rawdata 只读 | `copy_mode: reference`、`rawdata_readonly: true` |
| Approval Gate 强制执行 | 所有文件写入和执行需显式审批 |
| 路径防遍历 | `path_safety.py` 解析和验证所有路径 |
| Artifact 路径门控 | `project_id + run_id + artifact_id` — 不接受任意路径 |
| 二进制/NIfTI/MAT 仅元数据 | 预览显示元数据，非内容 |
| 前端隔离 | 仅通过 HTTP API 通信，不直接访问文件系统 |
| 桌面桥接 | Electron 中可用 `window.medimage.openExternalPath` |
| GPU/MATLAB/SPM/DPABI 门控 | 需要 `approved=true` 和环境变量 opt-in |

---

## FunRaw/T1Raw DICOM 支持

v0.3.0-rc1 包含对 DPABI/SPM 风格 FunRaw/T1Raw DICOM rawdata 的只读检测，
通过纯路径检测器实现（`src/backend/app/services/funraw_t1raw_detector.py`），
无需 pydicom。已用 1104 个 DICOM 文件（3 个被试，6 个 subject-modality 分组）验证。

- **Data Readiness** 将 DICOM raw layout 报告为 `warning`（非 `blocked`）。
- **NIfTI QC** 正确报告无 NIfTI 文件（无合成 fallback）。
- **Conversion Dry-Run** 生成 6 条 BIDS/NIfTI 映射预览。
- 不执行 DICOM 转换。不调用 dcm2niix。不修改 rawdata。
- DICOM-to-NIfTI 转换执行属于未来工作，必须先通过安全合同 / approval / audit 设计。

## 已知限制

- 不含 NIfTI viewer（仅元数据预览）
- 无完整 QC dashboard
- 无报告编辑器
- 此版本中 MATLAB/SPM/DPABI/GPU 仅为 contract-only
- **SPM realign 仅处于准备阶段**：参数验证、环境健康检查、dry-run 输出清单和批处理模板预览可用，但真正的 MATLAB/SPM 执行尚未实现
- **DICOM 转换为 dry-run only**：生成映射预览但不写文件。真正的 dcm2niix 执行尚未实现，必须先通过安全合同设计。
- **QC Dashboard 缓存为单模块原型**：支持 `cache=off|prefer|refresh`，但当前缓存仅覆盖 NIfTI QC Snapshot 一个模块。`cache=refresh` 会刷新该模块缓存，`cache=prefer` 会在 rawdata fingerprint 匹配时复用该模块缓存。其他 Dashboard 模块仍会正常运行。缓存不会修改 rawdata。
- **BIDS Validation fail 对原始 DICOM 是预期结果**：UI 已增加说明。
- Dataset Summary 可能尚未完全接入 DICOM counts。
- Electron 应用未签名（首次运行需放行 SmartScreen）
- 仅支持 Windows 打包
- 不支持自动更新

详见[发布说明](docs/releases/v0.3.0-rc1.md)。

---

## 开发路线图

| 版本 | 重点 |
|---|---|
| **v0.3.0-rc1**（当前） | 桌面端 MVP：真实项目工作流、运行历史、artifact 预览 |
| v0.3.x | 安装包签名、自动更新、CI/CD 打包流水线；SPM realign 准备阶段（参数、环境、dry-run、批处理模板预览） |
| v0.4.0 | NIfTI viewer、增强 QC dashboard、MATLAB/SPM 运行时（opt-in） |
| 未来 | macOS/Linux 打包、DICOM 浏览器、插件系统 |

---

## 文档

- [发布说明 v0.3.0-rc1](docs/releases/v0.3.0-rc1.md)
- [桌面应用打包](docs/DESKTOP_APP_PACKAGING.md)
- [真实项目运行生命周期](docs/REAL_PROJECT_RUN_LIFECYCLE.md)
- [MVP Release 冒烟清单](docs/MVP_RELEASE_SMOKE_CHECKLIST.md)
- [架构设计](docs/architecture.md)
- [Agent Runtime 规范](docs/agent_runtime_spec.md)
- [Pipeline Executor 规范](docs/pipeline_executor.md)

---

## 许可证

本项目用于学术研究目的。

**MedImage Agent 是一个研究工程平台，不用于临床诊断或医疗决策。**
