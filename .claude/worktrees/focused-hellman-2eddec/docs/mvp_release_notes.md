# MedImage Agent v0.1.0 MVP Release Notes

> 发布日期：2026-05-03
> 版本标签：v0.1.0-mvp-rc1

---

## 概述

MedImage Agent v0.1.0 是面向 rs-fMRI 预处理的可视化 Agent 工作流平台最小可行产品 (MVP)。

核心设计理念：**确定性 pipeline 引擎 + Agent 化辅助层**。LLM 不直接执行医学影像处理，而是作为外层顾问。

---

## 已实现功能

### 确定性 Pipeline 引擎

- 50+ 注册节点（backend/app/runtime/node_registry.py）
- 支持 `sequential` / `local_parallel` 两种调度模式
- Plan-then-Execute 模式（agent_plan.py → agent_runtime.py）
- 5 个 Hook 生命周期（before_plan / after_plan / before_execute / after_execute / on_error）
- 权限门控：每个工具声明 read_only、writes_files、destructive、requires_confirmation
- 错误诊断 + 重试计划（error_diagnoser.py + retry_runtime.py）
- 后台复盘（background_review.py）

### rs-fMRI 预处理全链路（Python 后端，纯 Python 无需 MATLAB）

- Slice Timing → Realign → Coregister → Segment → Normalize → Smooth
- Nuisance Regression（Friston24 模型）
- Temporal Filtering（FFT band-pass）
- ALFF / fALFF
- ReHo（KCC, Kendall's Coefficient of Concordance）
- Functional Connectivity（ROI correlation matrix + seed-to-voxel maps）

### 每阶段 Subject 级 QC

- Motion QC（FD, DVARS, threshold counts）
- Registration QC（affine translation, center distance）
- Normalization QC（MNI center distance, boundary overlap）
- Tissue QC（GM/WM/CSF volume fractions）
- Smoothing QC（variance ratio）
- Slice Timing QC
- ALFF/fALFF QC（finite fraction, frequency bins）
- ReHo QC（valid voxels, finite fraction）
- Functional Connectivity QC（symmetry, empty ROIs）

### 数据集级评估与报告

- Group Dataset Summary
- Dataset Evaluation Report
- Subject Exclusion Recommendations
- Subject QC Table CSV

### Report System

- Markdown + HTML 报告生成
- ZIP 导出 + SHA256 校验和
- Report Package 结构验证
- Reproducibility Manifest

### SPM / DPABI / GPU Wrapper（contract-only 模式）

- 9 个 SPM MATLAB wrapper 脚本
- 15+ DPABI wrapper contract 文件
- 3 个 GPU candidate contract 文件
- 默认 contract_only：生成协议但不执行真实后端

### 后端 API

- 60+ REST 端点（FastAPI + CORS）
- Agent Plan/Execute 端点
- Pipeline 管理端点
- 全 rs-fMRI 预处理阶段端点
- DPABI capability/contract 端点
- GPU detection/benchmark 端点
- Report export/validation 端点
- Release readiness 端点
- Docs inventory 端点

### 前端

- React + TypeScript + Vite SPA
- 25 个功能面板，覆盖全预处理阶段
- Project Dashboard
- Agent Controls（Plan / Execute）
- 所有 rs-fMRI 预处理阶段面板（Slice Timing → FC）
- DPABI Capability Panel
- Group Summary Dashboard
- Report Exporter / Validator
- Release Readiness Panel
- Documentation Center

### 安全机制

- Path traversal 防护（path_safety.py）
- Rawdata 永远只读
- Tool 权限声明与审批门控
- Derivatives 写入隔离
- Synthetic BIDS 默认输入
- 环境变量安全默认值（MEDIMAGE_SYNTHETIC_ONLY=true）
- PHI 敏感字段不记录到 run history

### 测试

- 36 单元测试，全量通过
- 覆盖 ALFF、ReHo、FC、Motion QC、Registration QC、Normalization QC 等核心模块
- 集成测试：synthetic BIDS → data inspection → preprocessing 全链路

### 部署

- Docker Compose 部署（backend + frontend + nginx）
- Dockerfile 多阶段构建
- 本地开发模式（uvicorn + vite）

---

## 不支持的功能（明确声明）

- 真实 MATLAB/SPM 调用（仅 synthetic data + contract-only wrapper）
- 真实 DPABI 调用（仅 contract-only）
- GPU 加速执行（仅 contract + benchmark CLI）
- Slurm/HPC 集群调度
- LLM 集成（advisor 层规划中，Phase F）
- 真实临床/研究数据处理
- PDF 报告生成（仅 Markdown + HTML）
- DICOM 导入
- 用户认证与多租户
- 断点续跑（checkpoint/resume）
- 缓存复用（cache 字段在 schema 中但未实现逻辑）

---

## 已知限制

- Windows 路径处理（部分路径使用 `\` vs `/`，pytest 通过但 CI 未覆盖）
- DICOM 导入不支持（仅 BIDS/BIDS-like NIfTI）
- Synthetic BIDS 数据为随机噪声，不反映真实 fMRI 信号特征
- MATLAB/SPM wrapper 仅在 subprocess 框架层面完成，未真实调用 MATLAB
- DPABI 全部为 contract-only，未执行任何 DPABI 函数
- Quickstart demo 的 report validation 在某些场景可能因动态内容时间戳导致 checksum 不匹配

---

## 系统要求

### 后端
- Python >= 3.10
- pip 包：见 requirements.txt（fastapi, uvicorn, pydantic, pyyaml, numpy, nibabel, httpx, pytest）

### 前端（开发模式）
- Node.js >= 18
- npm

### 可选
- MATLAB R2020b+ + SPM12（Phase C）
- DPABI V8.2+（Phase D）
- CUDA GPU + CuPy（Phase E）

---

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行全部测试
python -m pytest tests/ -v

# 3. 运行 Quickstart Demo
python -m backend.app.tools.run_quickstart_demo_cli

# 4. 启动后端
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

# 5. 启动前端（另开终端）
cd frontend && npm install && npm run dev
```

---

## 版本路线

| 版本 | 主题 | 预计 |
|------|------|------|
| v0.1.0 | MVP 封版（当前） | 2026-05 |
| v0.2.0 | SessionDB + Insights + Error Intelligence | 2026-06 |
| v0.3.0 | 真实 SPM / DPABI / GPU 接入 | 2026-Q3 |
| v0.4.0 | LLM Advisor Layer | 2026-Q4 |
| v0.5.0 | 真实数据沙盒 | 2026-Q4 |

详见 `docs/MedImage_Agent_Next_Stage_Plan.md`
