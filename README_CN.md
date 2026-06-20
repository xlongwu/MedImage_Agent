# MedImage Agent

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-v0.5.0--rc1-1976d2)](docs/releases/v0.6.0-rc1.md)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136%2B-green)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18%2B-61dafb)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5%2B-3178c6)](https://www.typescriptlang.org/)

[English](README.md) | **中文**

MedImage Agent 是面向静息态 fMRI（rs-fMRI）研究的确定性
Plan-then-Execute 桌面平台。LLM 只负责规划和建议；执行必须留在
Pipeline Runtime 和注册节点 runner 内。

本项目是研究工程平台，不用于临床诊断或医疗决策。

当前发布线：**v0.6.0-rc1**。详见
[发布说明](docs/releases/v0.6.0-rc1.md)。

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 20+
- MATLAB + SPM12 可选，仅用于显式环境变量门控的 SPM 工作流
- CuPy 可选，仅用于 GPU 路径

### 安装

```bash
pip install -r requirements.txt
cd src/frontend && npm install
```

### 启动开发服务

```bash
uvicorn src.backend.app.main:app --host 127.0.0.1 --port 8000
cd src/frontend && npm run dev

# 或一键启动：
start.bat
./start.sh
```

### 运行测试

```powershell
D:\Anaconda3\envs\mamba\python.exe -m pytest --tb=short --basetemp=.pytest_tmp
```

前端验证：

```powershell
cmd /c npm --prefix src/frontend run typecheck
cmd /c npm --prefix src/frontend run test
cmd /c npm --prefix src/frontend run build
```

## 桌面应用

Windows 桌面应用使用 Electron 壳和 PyInstaller 后端 sidecar。前端仍然只通过
HTTP API 与后端通信，不直接访问本地文件系统。

开发构建入口：

```powershell
npm --prefix src/frontend run build
powershell -File desktop/packaging/build_backend.ps1 -PythonExe "D:\Anaconda3\envs\mamba\python.exe"
powershell -File desktop/packaging/build_desktop.ps1 -DirOnly -ElectronRuntimeZip "desktop\electron\.electron-cache\manual-runtime\electron-v31.7.7-win32-x64.zip"
```

详见[桌面应用打包](docs/DESKTOP_APP_PACKAGING.md)。

## 架构

```text
Frontend (React + TypeScript + Vite)
    -> HTTP API
API Layer (FastAPI + Pydantic)
    -> Services and Schemas
Agent Runtime (Plan-then-Execute + Approval Gate)
    -> Pipeline Runtime (DAG Executor + Scheduler)
    -> Plugin Node Registry + Tool Catalog
```

状态保存在本地并按项目隔离：SQLite 存储项目元数据，JSON 存储运行状态和
artifact。运行时状态写入使用原子文件写入。Pipeline Runtime 是唯一 pipeline
执行路径。

当前 router、service、schema、node registry、前端 API、存储和桌面边界见
[架构文档](docs/architecture.md)。

## 当前稳定工作流

```text
选择 BIDS/rawdata
-> 创建项目
-> 生成 project_config.yaml 和 dataset_index.json
-> 注入项目上下文并审查计划
-> 保存 reviewed plan
-> 通过审批门执行 reviewed plan
-> 查看 run summary、events、logs 和 artifacts
```

DICOM/FunRaw/T1Raw 数据支持只读检测和转换 dry-run 预览。公共 DICOM 转换执行
路径是 fail-closed 的环境变量、审批和 readiness 门控路径，不会自动执行。

Phase 5 预处理工作流运行在 converted/sandboxed 输入上，仍然需要显式确认和
环境变量门控。

## 项目结构

```text
src/backend/app/
  api/                         领域 router 和 API middleware
  core/                        配置、异常、日志
  schemas/                     请求/响应与契约 schema
  services/                    业务逻辑和 read model
  runtime/                     pipeline executor、state store、node registry
  runtime/node_registry_plugins/
                               node runner 插件注册表
  tools/                       处理模块、QC、wrapper、CLI helper

src/frontend/src/
  lib/api/                     统一 client 和领域 API module
  components/                  可复用 UI 面板
  features/                    feature 级 UI 组合
  hooks/                       共享 React hooks
  state/                       workflow state model
  types/                       共享前端类型

desktop/
  electron/                    Electron shell 和 smoke checks
  packaging/                   PyInstaller 与 Windows 构建脚本

docs/
  releases/                    历史发布说明
  architecture.md              当前架构
  DESKTOP_APP_PACKAGING.md     打包指南

tests/
  unit/                        单元测试和源码契约测试
  integration/                 opt-in smoke / integration tests
```

## 安全架构

| 规则 | 机制 |
| --- | --- |
| Rawdata 只读 | 路径策略、checksum、审批文案 |
| 必须审批 | Tool Catalog + Approval Gate + 显式确认 |
| 防目录穿越 | `path_safety.py` 和 project/run artifact ID |
| 前端隔离 | HTTP API modules 和受控 Electron bridge |
| 外部工具门控 | 环境变量、approval/readiness、audit records |
| 仅研究用途 | UI 和文档警示 |

## 已知限制

- 不用于临床诊断或医疗决策。
- DPABI 执行默认禁用。
- MATLAB/SPM 执行需要本地工具和显式环境变量。
- DICOM 转换执行默认阻断，需要 release approval evidence 和多重确认。
- 部分数值预处理阶段在缺少可选科学计算依赖时会使用 metadata-first fallback。
- 当前发布线不包含 group statistics、classification、diagnosis model、report
  editor 或 auto-update 工作流。
- 桌面打包和 GUI smoke 需要兼容的本地 Windows 桌面环境。

## 文档

- [当前项目状态](PROJECT_STATE.md)
- [架构文档](docs/architecture.md)
- [发布说明 v0.6.0-rc1](docs/releases/v0.6.0-rc1.md)
- [发布说明 v0.4.0-rc1](docs/releases/v0.4.0-rc1.md)
- [发布说明 v0.3.0-rc1](docs/releases/v0.3.0-rc1.md)
- [桌面应用打包](docs/DESKTOP_APP_PACKAGING.md)
- [真实项目运行生命周期](docs/REAL_PROJECT_RUN_LIFECYCLE.md)
- [安全边界](docs/SAFETY_BOUNDARIES.md)

## 许可证

本项目用于学术研究目的。
