# Phase A：v0.1 MVP 封版验证

> 目标版本：v0.1.0 | 预计工期：2–3 天 | 前置条件：Phase A 无前置

---

## 1. 目标与范围

冻结当前 MVP 代码，完成干净环境可复现验证，生成 release notes，打 tag 作为 v0.1 Release Candidate。

**不做**：新功能开发、架构调整、真实 SPM/DPABI 接入、LLM 集成。

---

## 2. 前置条件检查

- [x] `requirements.txt` 已存在（Phase A 前置任务中已创建）
- [x] 所有单元测试通过（36/36 PASS）
- [ ] `run_quickstart_demo_cli` 验证
- [ ] `run_release_readiness_cli` 验证
- [ ] `run_docs_inventory_cli` 验证

---

## 3. 新增/修改文件清单

```text
docs/mvp_release_notes.md              # 新增：MVP 发布说明
CHANGELOG.md                            # 新增：版本变更日志
.gitignore                              # 检查：确保不遗漏
```

---

## 4. 逐步实施步骤

### Step 1：环境清理与 .gitignore 检查

```bash
git status
```

需要确认 `.gitignore` 已排除：
```text
__pycache__/
*.pyc
.pytest_cache/
work/
logs/
derivatives/
exports/
*.log
.env
node_modules/
dist/
```

若缺失则补充。

### Step 2：干净环境完整测试

```bash
# 1. 全新 virtualenv 安装
python -m venv /tmp/medimage_test_venv
source /tmp/medimage_test_venv/bin/activate  # Windows: \path\to\venv\Scripts\activate
pip install -r requirements.txt

# 2. 全量单元测试
python -m pytest tests/ -v

# 3. Quickstart demo（纯 Python，不需要 MATLAB）
python -m backend.app.tools.run_quickstart_demo_cli

# 4. Report export
python -m backend.app.tools.run_rsfmri_report_exporter_cli

# 5. Report validation
python -m backend.app.tools.run_rsfmri_report_validator_cli

# 6. Release readiness
python -m backend.app.tools.run_release_readiness_cli

# 7. Docs inventory
python -m backend.app.tools.run_docs_inventory_cli
```

每步预期输出 `{"ok": true}` 或 exit code 0。

### Step 3：后端启动验证

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

逐项 curl 检查：

```bash
# Health
curl -s http://127.0.0.1:8000/api/health | python -m json.tool

# Pipelines list
curl -s http://127.0.0.1:8000/api/pipelines | python -m json.tool

# Quickstart demo status
curl -s http://127.0.0.1:8000/api/quickstart-demo/latest | python -m json.tool

# Release readiness
curl -s http://127.0.0.1:8000/api/release-readiness | python -m json.tool

# Docs inventory
curl -s http://127.0.0.1:8000/api/docs/inventory | python -m json.tool
```

### Step 4：前端构建验证

```bash
cd frontend
npm install
npm run build
```

确认 `dist/` 目录生成，包含 `index.html` + JS/CSS assets。

### Step 5：编写 MVP Release Notes

创建 `docs/mvp_release_notes.md`，内容包含：

```markdown
# MedImage Agent v0.1.0 MVP Release Notes

## 概述
MedImage Agent v0.1.0 是面向 rs-fMRI 预处理的可视化 Agent 工作流平台 MVP。

## 已实现功能
### 确定性 Pipeline 引擎
- 50+ 注册节点
- 支持 sequential / local_parallel 调度
- Plan-then-Execute 模式
- Hook 生命周期（before_plan / after_plan / before_execute / after_execute / on_error）

### rs-fMRI 预处理全链路（Python 后端）
- Slice Timing → Realign → Coregister → Segment → Normalize → Smooth
- Nuisance Regression (Friston24)
- Temporal Filtering (FFT band-pass)
- ALFF / fALFF
- ReHo (KCC)
- Functional Connectivity (ROI correlation)

### 每阶段 QC
- Motion QC (FD/DVARS)
- Registration QC
- Normalization QC
- Tissue QC
- Smoothing QC
- ALFF/fALFF QC
- ReHo QC
- FC QC

### 数据集评估
- Group Summary
- Dataset Evaluation Report
- Exclusion Recommendations

### Report System
- Markdown + HTML 报告
- ZIP 导出 + SHA256 校验
- Package 验证

### API
- 60+ REST 端点
- FastAPI + CORS

### 前端
- React + TypeScript + Vite
- 25 个功能面板
- 覆盖全预处理阶段

### 安全
- Path traversal 防护
- Rawdata 只读
- Tool 权限声明
- Approval gate

### 测试
- 36 单元测试 / 全量通过

## 不支持的功能（明确声明）
- 真实 MATLAB/SPM 调用（仅 synthetic/wrapper）
- 真实 DPABI 调用（仅 contract-only）
- GPU 加速（仅 contract）
- Slurm/HPC 调度
- LLM 集成
- 真实临床数据处理
- PDF 报告

## 已知限制
- Windows 路径处理未全面测试
- DICOM 导入不支持
- 无用户认证

## 系统要求
- Python >= 3.10
- Node.js >= 18（前端开发）

## 快速开始
见 README.md Quickstart 章节
```

### Step 6：创建 CHANGELOG.md

```markdown
# Changelog

## [0.1.0] - 2026-05-02

### Added
- Deterministic pipeline engine with 50+ registered nodes
- Plan-then-Execute mode with Hook lifecycle
- Full rs-fMRI preprocessing chain (Python backend)
- Per-stage QC modules (Motion, Registration, Normalization, Tissue, Smoothing, ALFF, ReHo, FC)
- SPM/DPABI wrapper contracts (contract-only mode)
- Synthetic BIDS dataset generator
- Report export (ZIP + SHA256)
- Report package validator
- Release readiness checker
- 60+ REST API endpoints
- React + TypeScript frontend (25 panels)
- Path traversal safety
- Tool permission registry
- Error knowledge base
- Memory store (3-tier layout)
- 36 unit tests
- Docker demo deployment

[0.1.0]: https://github.com/.../releases/tag/v0.1.0
```

### Step 7：Git Tag

```bash
git add .
git commit -m "chore: v0.1.0 MVP release candidate

- Add MVP release notes
- Add CHANGELOG.md
- All 36 tests passing
- Quickstart demo verified"
git tag -a v0.1.0-mvp-rc1 -m "v0.1.0 MVP Release Candidate 1"
```

---

## 5. 交付物

```text
docs/mvp_release_notes.md
CHANGELOG.md
git tag: v0.1.0-mvp-rc1
```

---

## 6. 验收标准

- [ ] 全新 venv 中 `pip install -r requirements.txt` 成功
- [ ] `pytest` 36/36 全量通过
- [ ] `run_quickstart_demo_cli` 返回 ok=true
- [ ] `run_rsfmri_report_exporter_cli` 生成 ZIP
- [ ] `run_rsfmri_report_validator_cli` 验证 PASS
- [ ] `run_release_readiness_cli` 无 CRITICAL FAIL
- [ ] `run_docs_inventory_cli` 正常输出
- [ ] `uvicorn` 启动无 import 错误
- [ ] `/api/health` 返回 `{"ok": true}`
- [ ] `frontend` build 成功
- [ ] `.gitignore` 覆盖 `work/` `logs/` `derivatives/` `exports/` `__pycache__/`
- [ ] `docs/mvp_release_notes.md` 明确说明支持和不支持内容
- [ ] `CHANGELOG.md` 记录 v0.1.0 变更

---

## 7. 风险与注意事项

- **不要**在此阶段修改任何 runtime 逻辑
- **不要**引入新依赖
- 若 CLI 工具不存在（如 `run_history_cli`），改为通过 API 端点验证
- Windows 环境需注意路径分隔符（用 `pathlib.Path` 处理）
