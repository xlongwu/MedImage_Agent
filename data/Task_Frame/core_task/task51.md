# 第五十一步 Prompt：MVP User Guide + Developer Guide 文档体系闭环

```text
你是我的工程搭建助手。前五十步已经完成：

- MedImage Agent 工程骨架
- Pipeline runtime
- Agent runtime
- MATLAB / SPM / DPABI 环境检查
- synthetic BIDS 数据生成与扫描
- rs-fMRI preprocessing protocol
- rs-fMRI step registry
- SPM Slice Timing Correction + Metadata QC
- SPM Realignment + Motion QC
- Slice Timing → Realignment → Motion QC 链式核心 pipeline
- SPM Coregistration + Registration QC
- SPM Segmentation + Tissue QC
- SPM Normalization + Normalization QC
- SPM Smoothing + Smoothing QC
- Nuisance Regression 参数计划 + Confound Matrix + Python/DPABI 双后端设计
- Temporal Filtering + Filtering QC
- ALFF / fALFF 计算 + QC + GPU Candidate Backend 设计
- ReHo 计算 + ReHo QC + GPU/DPABI Backend Contract
- Functional Connectivity ROI/Seed 相关分析 + FC QC + GPU/DPABI Backend Contract
- Group-level Dataset Summary + Cross-subject Metrics Dashboard
- Dataset Report Exporter + 可交付报告包
- Report Package Validator + Integrity / Safety Audit
- Project Release Readiness Check + MVP 发布准备度审计

现在开始第五十一步。

第五十一步目标：实现 “MVP User Guide + Developer Guide 文档体系闭环”。

当前系统已经进入 MVP release 前准备阶段，但目前文档主要分散在 README、specs、step prompt 和各模块说明中。  
本步骤要建立一个统一的文档体系，让新用户、开发者和评审者能够理解：

1. 项目是什么。
2. 如何安装和启动。
3. 如何运行 synthetic demo。
4. 如何使用前端。
5. 如何理解 pipeline。
6. 如何理解安全边界。
7. 如何理解 SPM / DPABI / GPU contract。
8. 如何使用 report exporter / validator。
9. 如何开发新节点、新指标、新后端。
10. 如何排查常见问题。
11. MVP 当前支持什么、不支持什么。
12. 未来如何扩展到真实数据，但当前不处理真实医学影像。

本步骤要实现：

1. Documentation system specification。
2. 创建 `docs/` 文档体系。
3. 创建面向用户的 User Guide。
4. 创建面向开发者的 Developer Guide。
5. 创建 API Reference 文档。
6. 创建 Pipeline Guide 文档。
7. 创建 Frontend Guide 文档。
8. 创建 Safety and Limitations 文档。
9. 创建 Report Package Guide 文档。
10. 创建 Troubleshooting 文档。
11. 创建 Architecture Overview 文档。
12. 创建 Contribution / Extension Guide 文档。
13. 创建 Docs Inventory 工具：
    - 扫描 docs。
    - 检查关键文档是否存在。
    - 检查关键 heading 是否存在。
    - 检查安全声明是否存在。
    - 检查内部 markdown links 是否基本可解析。
    - 生成 docs inventory JSON / Markdown。
14. 新增 backend API：
    - `POST /api/docs/inventory/run`
    - `GET /api/docs/inventory`
15. 新增 frontend 面板：
    - Documentation Center
    - 可以运行 docs inventory。
    - 可以加载 docs inventory。
    - 显示 docs readiness status。
    - 显示 docs list。
    - 显示 missing docs。
    - 显示 safety coverage。
    - 显示 docs inventory report。
16. 新增 pipeline：
    - 只运行 docs inventory。
    - 不执行 SPM / MATLAB / DPABI / GPU。
17. 增加轻量 unit test。
18. 更新 README。

本步骤必须满足：

- 只读取项目 docs / specs / README。
- 只写入 `reports/docs_inventory`。
- 可以新增 docs 文件。
- 不处理真实医学影像数据。
- 不修改 rawdata。
- 不修改 derivatives。
- 不修改 exports。
- 不运行 SPM。
- 不运行 MATLAB。
- 不调用 DPABI。
- 不调用 DPARSF_run。
- 不调用 DPARSFA_run。
- 不调用 DPABI GUI。
- 不执行 GPU。
- 不删除文件。
- 不做医学结论。
- 不做 clinical interpretation。
- 不做 group-level statistics / inference。
- 不自动生成 PDF / Word / PPT。
- 不自动发布文档站点。

本步骤不要实现：

- MkDocs / Docusaurus 构建
- 在线部署
- PDF / Word / PPT 报告生成
- CI/CD 发布
- 自动修复项目代码
- 真实医学影像处理
- 真实 DPABI 执行
- 真实 GPU 执行

本步骤只做：建立 MVP 文档体系、生成文档目录和静态检查 inventory，并在 API / 前端暴露文档完整性状态。

---

## 1. 创建 specs/mvp_documentation_system_spec.md

创建文件：

```text
specs/mvp_documentation_system_spec.md
```

内容：

```markdown
# MVP Documentation System Specification

This document defines the MVP documentation system for the MedImage Agent project.

## Goals

The documentation system provides a stable documentation entry point for users, developers, reviewers, and future maintainers.

It explains:

- what the project does
- what the MVP supports
- how to install and run the synthetic demo
- how to use the frontend
- how to run CLI pipelines
- how the pipeline runtime works
- how backend APIs are organized
- how report export and validation work
- what safety boundaries are enforced
- how to extend the project

## Scope

Supported in this step:

- docs directory
- user guide
- developer guide
- architecture overview
- pipeline guide
- API reference
- frontend guide
- report package guide
- safety and limitations guide
- troubleshooting guide
- contribution and extension guide
- docs inventory generator
- docs inventory API
- frontend documentation center
- lightweight unit tests

Unsupported in this step:

- documentation website build
- online deployment
- PDF generation
- Word generation
- PowerPoint generation
- CI/CD publishing
- clinical interpretation
- real medical image preprocessing
- DPABI execution
- SPM execution
- MATLAB execution
- GPU execution

## Required Documents

```text
docs/README.md
docs/index.md
docs/user_guide.md
docs/developer_guide.md
docs/architecture_overview.md
docs/pipeline_guide.md
docs/api_reference.md
docs/frontend_guide.md
docs/report_package_guide.md
docs/safety_and_limitations.md
docs/troubleshooting.md
docs/contribution_and_extension_guide.md
```

## Inventory Outputs

```text
reports/docs_inventory/docs_inventory.json
reports/docs_inventory/docs_inventory_report.md
```

## Safety Rules

- This step writes only docs and reports/docs_inventory.
- It does not modify rawdata, derivatives, exports, SPM, or DPABI source code.
- It does not run SPM, MATLAB, DPABI, or GPU code.
- It does not process real medical images.
- It does not generate clinical conclusions.
- It does not perform statistical inference.
```

---

## 2. 创建 docs/README.md

创建目录和文件：

```text
docs/README.md
```

内容：

```markdown
# MedImage Agent Documentation

This directory contains the MVP documentation for the MedImage Agent project.

## Start Here

- [Documentation Index](index.md)
- [User Guide](user_guide.md)
- [Developer Guide](developer_guide.md)
- [Architecture Overview](architecture_overview.md)
- [Pipeline Guide](pipeline_guide.md)
- [API Reference](api_reference.md)
- [Frontend Guide](frontend_guide.md)
- [Report Package Guide](report_package_guide.md)
- [Safety and Limitations](safety_and_limitations.md)
- [Troubleshooting](troubleshooting.md)
- [Contribution and Extension Guide](contribution_and_extension_guide.md)

## MVP Scope

The MVP focuses on synthetic rs-fMRI engineering validation.

It does not process real clinical data, does not generate clinical conclusions, does not execute DPABI, and does not execute GPU code.
```

---

## 3. 创建 docs/index.md

创建文件：

```text
docs/index.md
```

内容：

```markdown
# Documentation Index

## Project Overview

MedImage Agent is an engineering MVP for building an agent-assisted medical imaging preprocessing and reporting workflow.

The current MVP focuses on synthetic rs-fMRI data and implements a controlled pipeline for:

- synthetic BIDS-like data generation
- SPM-backed preprocessing wrappers with approval gates
- Python post-processing metrics
- QC reports
- report package export
- report package validation
- release readiness checks

## User-facing Docs

- [User Guide](user_guide.md)
- [Frontend Guide](frontend_guide.md)
- [Report Package Guide](report_package_guide.md)
- [Safety and Limitations](safety_and_limitations.md)
- [Troubleshooting](troubleshooting.md)

## Developer-facing Docs

- [Developer Guide](developer_guide.md)
- [Architecture Overview](architecture_overview.md)
- [Pipeline Guide](pipeline_guide.md)
- [API Reference](api_reference.md)
- [Contribution and Extension Guide](contribution_and_extension_guide.md)

## Safety Reminder

This MVP is for engineering validation using synthetic data.

It does not modify rawdata, does not execute DPABI, does not execute GPU code, does not perform statistical inference, and does not generate clinical conclusions.
```

---

## 4. 创建 docs/user_guide.md

创建文件：

```text
docs/user_guide.md
```

内容：

```markdown
# User Guide

## What This Project Does

MedImage Agent helps organize a synthetic rs-fMRI preprocessing and reporting workflow into a controllable agent-style system.

It provides:

- pipeline execution
- step-level QC
- dataset-level QC
- frontend visualization
- report package export
- report package validation

## MVP Dataset Scope

The MVP is designed for synthetic BIDS-like rs-fMRI data.

It should not be used to process real clinical imaging data.

## Quick Start

### 1. Install Dependencies

Install the Python and frontend dependencies used by the project.

Typical Python dependencies include:

```bash
pip install -r requirements.txt
```

If no requirements file exists yet, install the dependencies referenced by tests and tools, such as:

```bash
pip install numpy nibabel pyyaml fastapi uvicorn pytest
```

### 2. Start Backend

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### 3. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Run Synthetic Pipeline Steps

Each stage has a CLI entrypoint. For example:

```bash
python -m backend.app.tools.run_rsfmri_group_summary_cli
python -m backend.app.tools.run_rsfmri_report_exporter_cli
python -m backend.app.tools.run_rsfmri_report_validator_cli
python -m backend.app.tools.run_release_readiness_cli
```

SPM-related pipelines require explicit approval gates.

## Frontend Workflow

Use the frontend panels in order:

1. Environment and data inspection
2. rs-fMRI preprocessing stages
3. Nuisance regression
4. Temporal filtering
5. ALFF / fALFF
6. ReHo
7. Functional connectivity
8. Group dataset dashboard
9. Report exporter
10. Report validator
11. Release readiness

## Outputs

Important outputs are written under:

```text
derivatives/
reports/
work/
exports/
```

## Report Package

The report exporter creates:

```text
exports/rsfmri_report_package/{export_id}/
exports/rsfmri_report_package/{export_id}.zip
```

The validator checks manifest, checksums, ZIP integrity, and safety flags.

## Safety

This MVP:

- does not modify rawdata
- does not execute DPABI
- does not execute GPU code
- does not perform statistical inference
- does not generate clinical conclusions
```

---

## 5. 创建 docs/developer_guide.md

创建文件：

```text
docs/developer_guide.md
```

内容：

```markdown
# Developer Guide

## Project Structure

```text
backend/app/
  api/
  runtime/
  tools/
examples/
frontend/src/
specs/
tests/unit/
docs/
reports/
exports/
```

## Backend Tools

Backend tools are small Python modules under:

```text
backend/app/tools/
```

Each tool should:

- expose a clear function
- accept explicit input/output directories
- write structured JSON outputs
- return a dictionary with `ok`, `node_id`, `outputs`, `warnings`, and `errors`
- avoid side effects outside declared output directories

## Runtime Nodes

Pipeline nodes are registered in:

```text
backend/app/runtime/node_registry.py
```

A node runner should:

- receive `NodeExecutionContext`
- receive `PipelineNode`
- validate required context fields
- call one backend tool function
- return structured results

## Adding a New Node

1. Add a backend tool in `backend/app/tools/`.
2. Add a node runner in `node_registry.py`.
3. Add the node ID to `NODE_REGISTRY`.
4. Add an example pipeline under `examples/`.
5. Add CLI entrypoint if useful.
6. Add API request model and route if frontend access is needed.
7. Add frontend API function and panel if visualization is needed.
8. Add unit tests.
9. Update README and docs.

## Tool Return Contract

Recommended result shape:

```json
{
  "ok": true,
  "node_id": "example_node",
  "backend": "python",
  "outputs": [],
  "warnings": [],
  "errors": []
}
```

## Safety Rules

New tools must not:

- modify rawdata
- delete files
- execute DPABI without a future explicit approved wrapper
- call DPARSF_run
- call DPARSFA_run
- call DPABI GUI
- execute GPU code unless the backend is explicitly implemented and approved
- process real medical images in this MVP
```

---

## 6. 创建 docs/architecture_overview.md

创建文件：

```text
docs/architecture_overview.md
```

内容：

```markdown
# Architecture Overview

## High-level Architecture

The project is organized around four layers:

1. Pipeline runtime
2. Backend tools
3. API layer
4. Frontend panels

## Pipeline Runtime

The runtime reads YAML pipeline definitions from `examples/`, resolves dependencies, executes registered nodes, and writes pipeline run summaries under `work/pipeline_runs`.

## Backend Tools

Backend tools implement small, testable actions such as:

- synthetic data generation
- QC calculation
- temporal filtering
- ALFF/fALFF
- ReHo
- functional connectivity
- group summary
- report export
- report validation
- release readiness

## API Layer

FastAPI routes expose selected operations to the frontend.

Read-only GET endpoints load existing results. POST endpoints run approved or read-only pipelines.

## Frontend

The frontend provides one panel per major workflow area.

Each panel usually supports:

- run
- load
- view JSON
- view Markdown report
- view summary cards

## Data Flow

```text
examples/
  -> pipeline runtime
  -> backend tools
  -> derivatives / reports / work / exports
  -> API
  -> frontend
```

## Contract-only Backends

DPABI and GPU backends are represented as contracts in this MVP.

Contracts document intended future inputs, outputs, parameters, blocked functions, and safety state.

They are not executed in this MVP.
```

---

## 7. 创建 docs/pipeline_guide.md

创建文件：

```text
docs/pipeline_guide.md
```

内容：

```markdown
# Pipeline Guide

## Pipeline Files

Example pipelines live under:

```text
examples/
```

Important pipelines include:

```text
pipeline_rsfmri_nuisance_regression.yaml
pipeline_rsfmri_temporal_filtering.yaml
pipeline_rsfmri_alff_falff.yaml
pipeline_rsfmri_reho.yaml
pipeline_rsfmri_functional_connectivity.yaml
pipeline_rsfmri_group_summary.yaml
pipeline_rsfmri_report_exporter.yaml
pipeline_rsfmri_report_validator.yaml
pipeline_release_readiness.yaml
pipeline_docs_inventory.yaml
```

## Node Structure

Each node defines:

- id
- name
- agent
- backend
- depends_on
- inputs
- outputs
- params
- parallel_level
- gpu_supported
- cache

## Approval Gates

SPM-backed preprocessing nodes require explicit approval.

This avoids accidentally running MATLAB/SPM operations.

Read-only reporting utilities do not require approval because they do not execute preprocessing.

## Running Pipelines

Use CLI modules:

```bash
python -m backend.app.tools.run_rsfmri_group_summary_cli
python -m backend.app.tools.run_rsfmri_report_exporter_cli
python -m backend.app.tools.run_rsfmri_report_validator_cli
python -m backend.app.tools.run_release_readiness_cli
python -m backend.app.tools.run_docs_inventory_cli
```

## Pipeline Outputs

Pipeline run summaries are written under:

```text
work/pipeline_runs/{run_id}/summary.json
```

## Safety

Pipeline definitions should not include automatic real-data execution.

SPM and MATLAB steps must remain approval-gated.
```

---

## 8. 创建 docs/api_reference.md

创建文件：

```text
docs/api_reference.md
```

内容：

```markdown
# API Reference

## Backend Base URL

Default backend URL:

```text
http://127.0.0.1:8000
```

## rs-fMRI Pipeline APIs

### Nuisance Regression

```text
POST /api/rsfmri/nuisance-regression/run
GET  /api/rsfmri/nuisance-regression
```

### Temporal Filtering

```text
POST /api/rsfmri/temporal-filtering/run
GET  /api/rsfmri/temporal-filtering
```

### ALFF / fALFF

```text
POST /api/rsfmri/alff-falff/run
GET  /api/rsfmri/alff-falff
```

### ReHo

```text
POST /api/rsfmri/reho/run
GET  /api/rsfmri/reho
```

### Functional Connectivity

```text
POST /api/rsfmri/functional-connectivity/run
GET  /api/rsfmri/functional-connectivity
```

### Group Summary

```text
POST /api/rsfmri/group-summary/run
GET  /api/rsfmri/group-summary
```

### Report Export

```text
POST /api/rsfmri/report-export/run
GET  /api/rsfmri/report-export/latest
GET  /api/rsfmri/report-export/list
```

### Report Validator

```text
POST /api/rsfmri/report-validator/run
GET  /api/rsfmri/report-validator/latest
GET  /api/rsfmri/report-validator/list
```

### Release Readiness

```text
POST /api/release-readiness/run
GET  /api/release-readiness
```

### Docs Inventory

```text
POST /api/docs/inventory/run
GET  /api/docs/inventory
```

## Response Pattern

Most endpoints return dictionaries containing:

```json
{
  "ok": true,
  "outputs": [],
  "warnings": [],
  "errors": []
}
```

## Approval

SPM-dependent run APIs require explicit approval.

Read-only APIs such as group summary, report export, report validation, release readiness, and docs inventory do not require SPM approval.
```

---

## 9. 创建 docs/frontend_guide.md

创建文件：

```text
docs/frontend_guide.md
```

内容：

```markdown
# Frontend Guide

## Overview

The frontend exposes pipeline and reporting functions through a set of panels.

Each panel typically includes:

- a run button
- a load button
- status badge
- summary cards
- JSON viewer
- Markdown viewer

## Important Panels

- rs-fMRI Nuisance Regression
- rs-fMRI Temporal Filtering
- rs-fMRI ALFF / fALFF
- rs-fMRI ReHo
- rs-fMRI Functional Connectivity
- rs-fMRI Group Dataset Dashboard
- rs-fMRI Report Exporter
- rs-fMRI Report Package Validator
- Project Release Readiness
- Documentation Center

## Frontend API

Frontend API helpers live in:

```text
frontend/src/api.ts
```

Panel components live in:

```text
frontend/src/components/
```

## Adding a Panel

1. Add backend API endpoints.
2. Add frontend API helper functions.
3. Add a React panel component.
4. Add the panel to `App.tsx`.
5. Add tests if the project has frontend tests.
6. Update docs.

## Safety UX

Run buttons for approved preprocessing should show confirmation dialogs.

Read-only reporting utilities do not need the same approval gate, but should clearly state that they do not modify rawdata or execute DPABI/GPU code.
```

---

## 10. 创建 docs/report_package_guide.md

创建文件：

```text
docs/report_package_guide.md
```

内容：

```markdown
# Report Package Guide

## Purpose

The report package exporter collects existing synthetic rs-fMRI engineering outputs into a portable package.

It is intended for audit, review, and archive workflows.

## Exporter

Run:

```bash
python -m backend.app.tools.run_rsfmri_report_exporter_cli
```

Outputs:

```text
exports/rsfmri_report_package/{export_id}/
exports/rsfmri_report_package/{export_id}.zip
```

## Package Contents

```text
MANIFEST.json
README.md
index.md
export_summary.json
checksums/SHA256SUMS.txt
summary/
subjects/
metrics/
fc/
contracts/
pipeline_runs/
tables/
```

## Validator

Run:

```bash
python -m backend.app.tools.run_rsfmri_report_validator_cli
```

The validator checks:

- required files
- manifest readability
- SHA256 checksums
- ZIP integrity
- forbidden rawdata / NIfTI / MAT inclusion
- safety flags

## Important Limitation

The package is not a clinical report.

It contains engineering validation artifacts for synthetic data only.
```

---

## 11. 创建 docs/safety_and_limitations.md

创建文件：

```text
docs/safety_and_limitations.md
```

内容：

```markdown
# Safety and Limitations

## MVP Safety Boundaries

This MVP is for engineering validation with synthetic rs-fMRI data.

It does not:

- process real clinical data
- make clinical conclusions
- perform statistical inference
- automatically exclude subjects
- modify rawdata
- execute DPABI
- execute GPU code
- call DPARSF_run
- call DPARSFA_run
- call DPABI GUI
- modify SPM or DPABI source code
- delete files

## SPM Approval Gate

SPM-backed steps require explicit approval.

This protects users from accidentally running MATLAB/SPM preprocessing.

## DPABI Contract-only Mode

DPABI support is represented by backend contracts.

The contracts document intended future behavior, but they are not executable in this MVP.

## GPU Contract-only Mode

GPU acceleration is represented by candidate backend contracts.

The contracts document future CuPy, Torch, or MATLAB GPU directions, but they are not executable in this MVP.

## Report Safety

Report packages should not include rawdata or large binary image outputs.

The report validator checks package integrity and safety flags.

## Clinical Limitation

No output from this MVP should be interpreted as a medical diagnosis, clinical biomarker, or treatment-relevant conclusion.
```

---

## 12. 创建 docs/troubleshooting.md

创建文件：

```text
docs/troubleshooting.md
```

内容：

```markdown
# Troubleshooting

## Backend Does Not Start

Check that dependencies are installed:

```bash
pip install numpy nibabel pyyaml fastapi uvicorn pytest
```

Start backend:

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

## Frontend Does Not Start

Run:

```bash
cd frontend
npm install
npm run dev
```

## API Returns 403

SPM-backed pipelines require explicit approval.

Reporting utilities such as group summary, report exporter, report validator, release readiness, and docs inventory should not require approval.

## No Group Summary Found

Run:

```bash
python -m backend.app.tools.run_rsfmri_group_summary_cli
```

## No Report Package Found

Run:

```bash
python -m backend.app.tools.run_rsfmri_report_exporter_cli
```

## No Validation Found

Run:

```bash
python -m backend.app.tools.run_rsfmri_report_validator_cli
```

## Release Readiness Fails

Open:

```text
reports/release_readiness/release_readiness_report.md
```

Review failed checks and missing files.

## Docs Inventory Fails

Open:

```text
reports/docs_inventory/docs_inventory_report.md
```

Review missing docs, missing headings, or safety coverage gaps.

## MATLAB / SPM Not Available

Read-only tools should still work.

SPM preprocessing steps will require local MATLAB and SPM availability.
```

---

## 13. 创建 docs/contribution_and_extension_guide.md

创建文件：

```text
docs/contribution_and_extension_guide.md
```

内容：

```markdown
# Contribution and Extension Guide

## Extending the Pipeline

To add a new processing stage:

1. Write a specification under `specs/`.
2. Implement a backend tool under `backend/app/tools/`.
3. Add a node runner to `backend/app/runtime/node_registry.py`.
4. Add an example pipeline under `examples/`.
5. Add a CLI wrapper.
6. Add API models and routes if needed.
7. Add frontend API helpers and panel if needed.
8. Add unit tests.
9. Update README and docs.
10. Run release readiness.

## Adding a New Metric

A metric tool should:

- read derivative inputs only
- write under derivatives or reports
- generate subject-level QC
- generate dataset-level summary where appropriate
- return structured output
- include tests

## Adding a Future DPABI Backend

Future DPABI execution must:

- avoid DPARSF_run and DPARSFA_run unless explicitly approved in a future design
- avoid GUI automation
- use single-function wrappers where possible
- require explicit approval
- log commands and outputs
- preserve rawdata

## Adding a Future GPU Backend

Future GPU execution must:

- be optional
- fall back to CPU
- be explicitly configured
- report device information
- avoid hidden GPU execution in read-only tools
- include tests that do not require GPU hardware

## Documentation Updates

Every new feature should update:

- specs
- docs
- README
- API reference
- frontend guide if UI changes
- troubleshooting guide if new failure modes are introduced
```

---

## 14. 创建 backend/app/tools/docs_inventory.py

创建文件：

```text
backend/app/tools/docs_inventory.py
```

目标：实现 docs inventory generator。

提供函数：

```python
build_docs_inventory(
    project_root: str = ".",
    reports_dir: str = "./reports",
) -> dict
```

输出：

```text
reports/docs_inventory/docs_inventory.json
reports/docs_inventory/docs_inventory_report.md
```

实现要求：

1. 检查 required docs 是否存在。
2. 检查每个 doc 是否非空。
3. 提取 Markdown headings。
4. 检查关键安全短语是否出现。
5. 检查内部 markdown link 是否指向存在文件。
6. 输出 JSON 和 Markdown。
7. 只写 reports/docs_inventory。
8. 不执行项目代码。
9. 不修改 docs。
10. 只使用 Python 标准库。

参考实现：

```python
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


REQUIRED_DOCS = [
    "docs/README.md",
    "docs/index.md",
    "docs/user_guide.md",
    "docs/developer_guide.md",
    "docs/architecture_overview.md",
    "docs/pipeline_guide.md",
    "docs/api_reference.md",
    "docs/frontend_guide.md",
    "docs/report_package_guide.md",
    "docs/safety_and_limitations.md",
    "docs/troubleshooting.md",
    "docs/contribution_and_extension_guide.md",
]

SAFETY_PHRASES = [
    "does not modify rawdata",
    "does not execute DPABI",
    "does not execute GPU",
    "does not perform statistical inference",
    "does not generate clinical conclusions",
]

LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_headings(text: str) -> list[str]:
    headings = []
    for line in text.splitlines():
        if line.startswith("#"):
            headings.append(line.strip())
    return headings


def _check_links(root: Path, doc_path: Path, text: str) -> list[dict[str, Any]]:
    links = []

    for match in LINK_PATTERN.finditer(text):
        label = match.group(1)
        target = match.group(2).strip()

        if target.startswith("http://") or target.startswith("https://") or target.startswith("#"):
            links.append({
                "label": label,
                "target": target,
                "status": "SKIP_EXTERNAL_OR_ANCHOR",
            })
            continue

        clean_target = target.split("#", 1)[0]
        target_path = (doc_path.parent / clean_target).resolve()

        try:
            target_path.relative_to(root.resolve())
            safe = True
        except ValueError:
            safe = False

        exists = target_path.exists() if safe else False

        links.append({
            "label": label,
            "target": target,
            "resolved_path": str(target_path),
            "safe": safe,
            "exists": exists,
            "status": "PASS" if safe and exists else "FAIL",
        })

    return links


def _write_report(path: Path, result: dict[str, Any]) -> None:
    lines = []
    lines.append("# Documentation Inventory Report")
    lines.append("")
    lines.append(f"- Status: **{result.get('docs_status')}**")
    lines.append(f"- Checked at: `{result.get('checked_at')}`")
    lines.append(f"- Required docs: {result.get('required_docs_total')}")
    lines.append(f"- Existing docs: {result.get('existing_docs_total')}")
    lines.append(f"- Missing docs: {result.get('missing_docs_total')}")
    lines.append(f"- Broken links: {result.get('broken_links_total')}")
    lines.append(f"- Safety phrases found: {result.get('safety_phrases_found_total')}")
    lines.append("")
    lines.append("## Documents")
    lines.append("")
    lines.append("| Document | Status | Headings | Broken Links |")
    lines.append("|---|---|---:|---:|")
    for item in result.get("documents", []):
        lines.append(
            f"| {item.get('path')} | {item.get('status')} | "
            f"{len(item.get('headings', []))} | {item.get('broken_links_total')} |"
        )

    lines.append("")
    lines.append("## Missing Documents")
    lines.append("")
    for item in result.get("missing_docs", []):
        lines.append(f"- `{item}`")
    if not result.get("missing_docs"):
        lines.append("- None")

    lines.append("")
    lines.append("## Safety Coverage")
    lines.append("")
    for phrase, found in result.get("safety_phrase_coverage", {}).items():
        lines.append(f"- `{phrase}`: {found}")

    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("Docs inventory is read-only for docs and writes only reports/docs_inventory.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_docs_inventory(
    project_root: str = ".",
    reports_dir: str = "./reports",
) -> dict[str, Any]:
    root = Path(project_root)
    reports = Path(reports_dir)

    out_dir = reports / "docs_inventory"
    out_dir.mkdir(parents=True, exist_ok=True)

    inventory_json = out_dir / "docs_inventory.json"
    report_md = out_dir / "docs_inventory_report.md"

    documents = []
    missing_docs = []
    all_text = ""

    for rel in REQUIRED_DOCS:
        path = root / rel
        exists = path.exists()
        text = _read_text(path)
        non_empty = bool(text.strip())
        headings = _extract_headings(text)
        links = _check_links(root, path, text) if exists else []
        broken_links = [item for item in links if item.get("status") == "FAIL"]

        if not exists:
            missing_docs.append(rel)

        status = "PASS"
        if not exists:
            status = "FAIL"
        elif not non_empty:
            status = "FAIL"
        elif not headings:
            status = "WARNING"
        elif broken_links:
            status = "WARNING"

        documents.append({
            "path": rel,
            "absolute_path": str(path),
            "exists": exists,
            "non_empty": non_empty,
            "headings": headings,
            "links": links,
            "broken_links_total": len(broken_links),
            "status": status,
        })

        all_text += "\n" + text

    safety_phrase_coverage = {
        phrase: phrase in all_text
        for phrase in SAFETY_PHRASES
    }

    broken_links_total = sum(int(item["broken_links_total"]) for item in documents)
    existing_docs_total = sum(1 for item in documents if item["exists"])
    missing_docs_total = len(missing_docs)
    safety_found_total = sum(1 for found in safety_phrase_coverage.values() if found)

    fail_count = sum(1 for item in documents if item["status"] == "FAIL")
    warning_count = sum(1 for item in documents if item["status"] == "WARNING")

    if fail_count > 0:
        docs_status = "FAIL"
    elif warning_count > 0 or safety_found_total < len(SAFETY_PHRASES):
        docs_status = "WARNING"
    else:
        docs_status = "PASS"

    result = {
        "ok": docs_status in {"PASS", "WARNING"},
        "node_id": "docs_inventory",
        "backend": "python",
        "checked_at": _iso_now(),
        "docs_status": docs_status,
        "required_docs_total": len(REQUIRED_DOCS),
        "existing_docs_total": existing_docs_total,
        "missing_docs_total": missing_docs_total,
        "broken_links_total": broken_links_total,
        "safety_phrases_found_total": safety_found_total,
        "safety_phrase_coverage": safety_phrase_coverage,
        "documents": documents,
        "missing_docs": missing_docs,
        "outputs": [
            str(inventory_json),
            str(report_md),
        ],
        "warnings": [],
        "errors": [],
    }

    if missing_docs:
        result["errors"].append(f"Missing docs: {missing_docs}")
    if broken_links_total > 0:
        result["warnings"].append(f"Broken internal links found: {broken_links_total}")
    if safety_found_total < len(SAFETY_PHRASES):
        result["warnings"].append("Not all safety phrases were found in docs.")

    inventory_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_report(report_md, result)

    return result
```

---

## 15. 修改 backend/app/runtime/node_registry.py

新增节点：

```text
docs_inventory
```

新增导入：

```python
from backend.app.tools.docs_inventory import build_docs_inventory
```

新增 runner：

```python
def run_docs_inventory_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = build_docs_inventory(
        project_root=node.params.get("project_root", "."),
        reports_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result
```

更新 `NODE_REGISTRY`：

```python
"docs_inventory": run_docs_inventory_node,
```

---

## 16. 创建 examples/pipeline_docs_inventory.yaml

创建文件：

```text
examples/pipeline_docs_inventory.yaml
```

内容：

```yaml
pipeline_id: docs_inventory_pipeline
version: "0.1.0"
modality: project
description: "Run read-only documentation inventory and documentation readiness checks."

execution:
  stop_on_failure: true
  run_id: "run_docs_inventory_001"
  scheduler:
    mode: "local"
    max_workers: 1
    matlab_max_workers: 0

nodes:
  - id: docs_inventory
    name: Documentation Inventory
    agent: report-runner
    backend: python
    depends_on: []
    inputs:
      - "./docs"
      - "./specs"
      - "./README.md"
    outputs:
      - "./reports/docs_inventory/docs_inventory.json"
      - "./reports/docs_inventory/docs_inventory_report.md"
    params:
      project_root: "."
    parallel_level: project
    gpu_supported: false
    cache: false
```

本 pipeline 不执行任何 SPM / MATLAB / DPABI / GPU。  
它只读取 docs / specs / README，并写入 reports/docs_inventory。

---

## 17. 创建 backend/app/tools/run_docs_inventory_cli.py

创建文件：

```text
backend/app/tools/run_docs_inventory_cli.py
```

内容：

```python
from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.pipeline_executor import run_pipeline


def main() -> int:
    args = sys.argv[1:]

    project_config = Path(args[0]) if len(args) > 0 else Path("examples/project_config_dataset.yaml")
    pipeline = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_docs_inventory.yaml")

    summary = run_pipeline(project_config, pipeline)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    status = summary.get("status")
    if status == "SUCCESS":
        return 0
    if status == "INVALID":
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

---

## 18. 修改 backend/app/api/models.py

新增 request model：

```python
class DocsInventoryRequest(BaseModel):
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    pipeline_path: str = Field(default="examples/pipeline_docs_inventory.yaml")
```

---

## 19. 修改 backend/app/api/routes.py

新增 API：

```text
POST /api/docs/inventory/run
GET  /api/docs/inventory
```

新增导入：

```python
from backend.app.api.models import DocsInventoryRequest
from backend.app.runtime.pipeline_executor import run_pipeline
```

新增路由：

```python
@router.post("/api/docs/inventory/run")
def api_run_docs_inventory(
    request: DocsInventoryRequest,
) -> dict[str, Any]:
    try:
        summary = run_pipeline(
            request.project_config_path,
            request.pipeline_path,
        )

        if summary.get("status") not in {"SUCCESS", "PARTIAL"}:
            raise HTTPException(status_code=400, detail=summary)

        return summary

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/docs/inventory")
def api_get_docs_inventory() -> dict[str, Any]:
    base = Path("reports") / "docs_inventory"

    return {
        "ok": True,
        "docs_inventory": _read_json_if_exists(base / "docs_inventory.json"),
        "docs_inventory_report": _read_text_if_exists(base / "docs_inventory_report.md"),
    }
```

注意：本 POST 不需要 approved，因为不执行 SPM / DPABI / GPU，只做 docs inventory 静态检查。

---

## 20. 修改 frontend/src/api.ts

新增：

```ts
export async function runDocsInventory(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/docs/inventory/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getDocsInventory(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/docs/inventory"
  );
}
```

---

## 21. 创建 frontend/src/components/DocumentationCenterPanel.tsx

创建文件：

```text
frontend/src/components/DocumentationCenterPanel.tsx
```

内容：

```tsx
import { useState } from "react";
import {
  getDocsInventory,
  runDocsInventory
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function DocumentationCenterPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    setStatus("RUNNING");
    setError("");

    try {
      const response = await runDocsInventory(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_docs_inventory.yaml"
      });
      setResult(response);
      setStatus("SUCCESS");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleLoad() {
    setStatus("LOADING");
    setError("");

    try {
      const response = await getDocsInventory(baseUrl);
      setLoaded(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const inventory = loaded?.docs_inventory as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button onClick={handleRun}>
          运行 Docs Inventory
        </button>
        <button onClick={handleLoad}>加载 Docs Inventory</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="metricGrid">
        <div className="metricCard">
          <span>Docs Status</span>
          <strong>{String(inventory?.docs_status ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Required Docs</span>
          <strong>{String(inventory?.required_docs_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Existing Docs</span>
          <strong>{String(inventory?.existing_docs_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Missing Docs</span>
          <strong>{String(inventory?.missing_docs_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Broken Links</span>
          <strong>{String(inventory?.broken_links_total ?? "-")}</strong>
        </div>
      </div>

      <h3>Run Summary</h3>
      <JsonBlock value={result} emptyText="尚未运行" />

      <h3>Docs Inventory</h3>
      <JsonBlock value={loaded?.docs_inventory} emptyText="暂无 docs inventory" />

      <h3>Missing Docs</h3>
      <JsonBlock value={inventory?.missing_docs} emptyText="暂无 missing docs" />

      <h3>Safety Phrase Coverage</h3>
      <JsonBlock value={inventory?.safety_phrase_coverage} emptyText="暂无 safety coverage" />

      <h3>Docs Inventory Report</h3>
      <TextViewer
        text={
          typeof loaded?.docs_inventory_report === "string"
            ? loaded.docs_inventory_report
            : null
        }
        emptyText="暂无 docs inventory report"
      />
    </div>
  );
}
```

---

## 22. 修改 frontend/src/App.tsx

新增导入：

```tsx
import { DocumentationCenterPanel } from "./components/DocumentationCenterPanel";
```

在 `Project Release Readiness` 后新增 Section：

```tsx
<Section
  title="Documentation Center"
  description="查看和检查 MVP 用户文档、开发者文档、API 文档、pipeline 文档和安全边界文档。"
>
  <DocumentationCenterPanel baseUrl={baseUrl} />
</Section>
```

---

## 23. 新增轻量测试

创建文件：

```text
tests/unit/test_docs_inventory.py
```

内容：

```python
from __future__ import annotations

import json
from pathlib import Path

from backend.app.tools.docs_inventory import build_docs_inventory


def test_docs_inventory_generates_report(tmp_path: Path):
    root = tmp_path / "project"
    reports = tmp_path / "reports"
    docs = root / "docs"
    docs.mkdir(parents=True)

    required_docs = [
        "README.md",
        "index.md",
        "user_guide.md",
        "developer_guide.md",
        "architecture_overview.md",
        "pipeline_guide.md",
        "api_reference.md",
        "frontend_guide.md",
        "report_package_guide.md",
        "safety_and_limitations.md",
        "troubleshooting.md",
        "contribution_and_extension_guide.md",
    ]

    for name in required_docs:
        (docs / name).write_text(
            "\n".join([
                f"# {name}",
                "",
                "This documentation does not modify rawdata.",
                "It does not execute DPABI.",
                "It does not execute GPU.",
                "It does not perform statistical inference.",
                "It does not generate clinical conclusions.",
            ]),
            encoding="utf-8",
        )

    result = build_docs_inventory(
        project_root=str(root),
        reports_dir=str(reports),
    )

    assert result["node_id"] == "docs_inventory"
    assert result["docs_status"] in {"PASS", "WARNING", "FAIL"}
    assert result["existing_docs_total"] == len(required_docs)

    out_dir = reports / "docs_inventory"
    assert (out_dir / "docs_inventory.json").exists()
    assert (out_dir / "docs_inventory_report.md").exists()

    payload = json.loads((out_dir / "docs_inventory.json").read_text(encoding="utf-8"))
    assert payload["missing_docs_total"] == 0
```

---

## 24. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

```python
call("GET", "/api/docs/inventory")
```

不要在 smoke test 中调用 POST run，避免改变 reports。

---

## 25. 更新 README.md

追加第五十一步说明：

```markdown
## Step 51: MVP User Guide and Developer Guide Documentation System

This step creates a documentation system for the MVP.

It includes:

- docs index
- user guide
- developer guide
- architecture overview
- pipeline guide
- API reference
- frontend guide
- report package guide
- safety and limitations
- troubleshooting
- contribution and extension guide
- docs inventory generator
- docs inventory API
- frontend Documentation Center

It writes docs under `docs/` and inventory outputs under `reports/docs_inventory`.

It does not execute SPM, MATLAB, DPABI, or GPU code.

### Run

```bash
python -m backend.app.tools.run_docs_inventory_cli
```

Expected outputs:

```text
reports/docs_inventory/docs_inventory.json
reports/docs_inventory/docs_inventory_report.md
work/pipeline_runs/run_docs_inventory_001/summary.json
```

### API

```bash
curl http://127.0.0.1:8000/api/docs/inventory
```

Run docs inventory:

```bash
curl -X POST http://127.0.0.1:8000/api/docs/inventory/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_docs_inventory.yaml"
  }'
```

### Frontend

Use:

```text
Documentation Center
```

### Safety

This step:

- only reads docs / specs / README
- writes only reports/docs_inventory
- does not modify rawdata
- does not modify derivatives
- does not modify exports
- does not run SPM
- does not run MATLAB
- does not run DPABI
- does not run GPU
- does not call DPARSF_run
- does not call DPARSFA_run
- does not call DPABI GUI
- does not perform group-level statistical inference
- does not make clinical conclusions
```

---

## 26. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/mvp_documentation_system_spec.md
docs/README.md
docs/index.md
docs/user_guide.md
docs/developer_guide.md
docs/architecture_overview.md
docs/pipeline_guide.md
docs/api_reference.md
docs/frontend_guide.md
docs/report_package_guide.md
docs/safety_and_limitations.md
docs/troubleshooting.md
docs/contribution_and_extension_guide.md
backend/app/tools/docs_inventory.py
backend/app/runtime/node_registry.py
examples/pipeline_docs_inventory.yaml
backend/app/tools/run_docs_inventory_cli.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/DocumentationCenterPanel.tsx
frontend/src/App.tsx
tests/unit/test_docs_inventory.py
backend/app/tools/api_smoke_test.py
README.md
```

运行 docs inventory：

```bash
python -m backend.app.tools.run_docs_inventory_cli
```

应生成：

```text
reports/docs_inventory/docs_inventory.json
reports/docs_inventory/docs_inventory_report.md
```

docs_inventory JSON 必须包含：

```json
{
  "node_id": "docs_inventory",
  "docs_status": "PASS",
  "required_docs_total": 12,
  "existing_docs_total": 12,
  "missing_docs_total": 0,
  "broken_links_total": 0,
  "safety_phrase_coverage": {},
  "documents": []
}
```

实际状态可为 PASS / WARNING / FAIL，取决于文档链接和安全短语覆盖。

运行测试：

```bash
python -m pytest tests/unit/test_docs_inventory.py -q
```

启动后端：

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

测试 API：

```bash
curl http://127.0.0.1:8000/api/docs/inventory

curl -X POST http://127.0.0.1:8000/api/docs/inventory/run \
  -H "Content-Type: application/json" \
  -d '{}'
```

启动前端：

```bash
cd frontend
npm run dev
```

页面应该能完成：

1. 显示 Documentation Center 区域。
2. 可以点击运行 Docs Inventory。
3. 可以加载 Docs Inventory。
4. 显示 docs status。
5. 显示 required docs 数量。
6. 显示 existing docs 数量。
7. 显示 missing docs 数量。
8. 显示 broken links 数量。
9. 显示 docs inventory JSON。
10. 显示 missing docs JSON。
11. 显示 safety phrase coverage。
12. 显示 docs inventory Markdown report。
13. 不修改 rawdata。
14. 不修改 derivatives。
15. 不修改 exports。
16. 不运行 SPM / MATLAB。
17. 不运行 DPABI。
18. 不运行 GPU。
19. 不执行统计推断。
20. 不生成临床结论。

---

## 27. 重要限制

本步骤只做 MVP 文档体系和 Docs Inventory。

不要实现：

- MkDocs / Docusaurus 构建
- 在线部署
- PDF / Word / PPT 文档生成
- 自动修复文档链接
- Docker build
- CI/CD
- PyPI / npm 发布
- group-level statistical testing
- clinical interpretation
- subject exclusion automation
- 真实医学影像处理
- DPABI 全流程执行
- DPARSF_run 自动执行
- DPARSFA_run 自动执行
- DPABI GUI 自动化
- SPM / MATLAB 执行
- GPU 执行
- rawdata 修改
- 文件删除

完成后请总结：

1. 新增了哪些 docs 文件
2. 修改了哪些工程文件
3. User Guide 面向谁
4. Developer Guide 面向谁
5. Pipeline Guide 说明什么
6. API Reference 说明什么
7. Safety and Limitations 为什么是 MVP release 必须项
8. Docs Inventory 如何检查缺失文档和链接
9. Documentation Center 前端如何展示文档 readiness
10. 为什么本步骤不构建在线文档站点
11. 下一步如何实现 Quickstart Demo Orchestrator：一键运行 synthetic demo 的最小安全演示流程

```
新建了 4 个文档文件——docs/architecture.md（系统架构）、docs/user_guide.md（快速启动指南）、docs/developer_guide.md（新增 pipeline 步骤的标准流程）、docs/safety_and_limitations.md（安全规则和局限性声明）。同时写了 docs_inventory.py 来校验文档完整性。
```
