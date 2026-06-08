# MedImage Agent

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136%2B-green)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61dafb)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0%2B-3178c6)](https://www.typescriptlang.org/)
[![Node](https://img.shields.io/badge/Node-24%2B-339933)](https://nodejs.org/)

![Tests](https://img.shields.io/badge/tests-2426%20passed-brightgreen)  ![Release](https://img.shields.io/badge/release-v0.3.0--rc1-blue)

**English** | [中文](README_CN.md)

MedImage Agent is a **deterministic Plan-then-Execute desktop platform** for
resting-state fMRI (rs-fMRI) research. The LLM plans and advises; execution
stays inside the Pipeline Runtime and registered node runners. It is a
research engineering platform, **not a clinical diagnosis or clinical decision
product**.

**Latest Release**: [v0.3.0-rc1](https://github.com/xlongwu/MedImage_Agent_WebUI_App/releases/tag/v0.3.0-rc1) — Desktop MVP Release Candidate ([release notes](docs/releases/v0.3.0-rc1.md))

---

## Table of Contents

- [Quick Start](#quick-start)
- [Desktop App](#desktop-app)
- [Architecture](#architecture)
- [Real Project Workflow](#real-project-workflow)
- [Project Structure](#project-structure)
- [Test Baseline](#test-baseline)
- [Safety Architecture](#safety-architecture)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)
- [Documentation](#documentation)

---

## Quick Start

### Requirements

- Python 3.11+ (validated: `D:\Anaconda3\envs\mamba\python.exe`)
- Node.js 20+ (validated: v24.16.0)
- MATLAB + SPM12 (optional, for SPM preprocessing)
- CuPy (optional, for GPU acceleration)

### Install

```bash
pip install -r requirements.txt
cd src/frontend && npm install
```

### Start (development)

```bash
uvicorn src.backend.app.main:app --host 127.0.0.1 --port 8000
cd src/frontend && npm run dev

# Or one-click:
start.bat           # Windows
./start.sh          # Linux/macOS
```

### Run Tests

```bash
D:\Anaconda3\envs\mamba\python.exe -m pytest --tb=short --basetemp=.pytest_tmp
```

---

## Desktop App

v0.3.0-rc1 ships a self-contained Windows desktop application. No Python or
Node.js installation is required at runtime.

### Download

| Format | File | Size |
|---|---|---|
| **NSIS Installer** | `MedImage Agent Setup.exe` | 112 MB |
| **Portable** | `MedImage Agent.exe` | 112 MB |

Download from the [GitHub Release page](https://github.com/xlongwu/MedImage_Agent_WebUI_App/releases/tag/v0.3.0-rc1).

### How It Works

1. Electron shell starts → extracts PyInstaller backend sidecar
2. Backend binds to `127.0.0.1` on an available port (starting at 8765)
3. Electron waits for `/api/health` → loads the React frontend
4. When the app closes, the backend sidecar is stopped cleanly
5. The frontend communicates through HTTP APIs; it never accesses the filesystem directly

### Build from Source

```powershell
npm --prefix src/frontend run build
powershell -File desktop/packaging/build_backend.ps1 -PythonExe "D:\Anaconda3\envs\mamba\python.exe"
powershell -File desktop/packaging/build_desktop.ps1 -DirOnly -ElectronRuntimeZip "desktop\electron\.electron-cache\manual-runtime\electron-v31.7.7-win32-x64.zip"
```

See [Desktop App Packaging](docs/DESKTOP_APP_PACKAGING.md) for detailed instructions.

---

## Architecture

```
Frontend (React 18 + TypeScript + Vite)
    ↓ HTTP API
API Layer (FastAPI + Pydantic)
    ↓
Agent Runtime (Plan-then-Execute + Approval Gate)
    ↓
Pipeline Runtime (DAG Executor + Scheduler)
```

Four layers, top to bottom. State is file-system based (SQLite for project
metadata, JSON for run state). The LLM only advises; the Pipeline Runtime is
the sole execution path.

---

## Real Project Workflow

```
Select BIDS/rawdata → Create Project → project_config.yaml + dataset_index.json
    → Plan Review (project context injected)
    → Save Reviewed Plan (persisted to SQLite)
    → Execute Reviewed (Approval Gate gated, unique run_id)
    → Run Summary / Artifacts
    → Run History UI → Artifact Preview (JSON/CSV/Markdown/text/log/NIfTI/MAT)
```

Every execution produces a unique `run_id`, a summary JSON, and run-scoped
artifacts discoverable through the artifact API. Rawdata is referenced
read-only and verified unchanged after execution.

---

## Project Structure

```
MedImage_Agent/
├── src/
│   ├── backend/app/
│   │   ├── api/              # FastAPI routes
│   │   ├── services/         # Business logic (SQLite store, artifact services)
│   │   ├── planner/          # Plan context, reviewed plan store, approval, audit
│   │   ├── runtime/          # Pipeline executor, node registry, state store
│   │   ├── tools/            # Processing modules, QC, CLI runners
│   │   ├── schemas/          # Pipeline YAML schema validation
│   │   └── advisor/          # LLM advisor modules
│   └── frontend/
│       ├── src/components/   # React panels (PlanReviewConsole, ProjectRunsPanel, run-history/*)
│       ├── electron/         # Electron main/preload/smoke-check
│       └── scripts/          # Smoke tests
├── desktop/
│   ├── electron/             # Electron packaging (main, preload, builder config, smoke)
│   └── packaging/            # PyInstaller specs, PowerShell build scripts
├── docs/
│   ├── releases/             # Release notes and SHA256SUMS
│   ├── DESKTOP_APP_PACKAGING.md
│   ├── REAL_PROJECT_RUN_LIFECYCLE.md
│   └── MVP_RELEASE_SMOKE_CHECKLIST.md
├── tests/
│   ├── unit/                 # 100+ unit test files
│   └── integration/          # Safe smoke, external BIDS smoke, contract smoke
├── examples/                 # Pipeline YAMLs and project configs
└── deploy/                   # Dockerfiles and docker-compose
```

---

## Test Baseline

| Metric | Value |
|---|---|
| Full pytest (historical Phase 3 freeze) | **2915 passed, 1 skipped, 0 failed** |
| Recent focused validation | **43 passed + 41 regression passed** |
| Frontend TypeScript | `tsc --noEmit` ✅ |
| Frontend Vite build | 106 modules, Vite production build ✅ |
| Electron smoke check | 51/51 ✅ |
| GUI desktop startup | Verified on Windows 10/11 ✅ |
| FunRaw/T1Raw DICOM smoke | 1104 DICOM, rawdata unchanged ✅ |
| Test environment | `D:\Anaconda3\envs\mamba\python.exe` (Python 3.11.15) |

Expected skips: `pydicom`, `cupy`, `MEDIMAGE_EXTERNAL_BIDS_SMOKE_DIR`.
Historical baselines are labelled; confirm current pass count with a fresh pytest run before relying on exact numbers.

---

## Safety Architecture

| Rule | Mechanism |
|---|---|
| Rawdata read-only | `copy_mode: reference`, `rawdata_readonly: true` in config |
| Approval Gate mandatory | All file writes and execution require explicit approval |
| Path traversal prevention | `path_safety.py` resolves and validates all paths |
| Artifact path gating | `project_id + run_id + artifact_id` — no arbitrary paths accepted |
| Binary/NIfTI/MAT metadata-only | Preview shows metadata, not content |
| Frontend isolation | HTTP APIs only; no direct filesystem access |
| Desktop bridge | `window.medimage.openExternalPath` available in Electron |
| GPU/MATLAB/SPM/DPABI gated | Requires `approved=true` and environment opt-in |

---

## FunRaw/T1Raw DICOM Support

v0.3.0-rc1 includes read-only detection of DPABI/SPM-style FunRaw/T1Raw DICOM
rawdata via a path-based detector (`src/backend/app/services/funraw_t1raw_detector.py`).
No pydicom is required.  Validated with 1104 DICOM files across 3 subjects and
6 subject-modality groups.

- **Data Readiness** reports DICOM raw layout as `warning` (not `blocked`).
- **NIfTI QC** correctly reports no NIfTI files (no synthetic fallback).
- **Conversion Dry-Run** produces 6 BIDS/NIfTI mapping previews.
- No DICOM conversion is executed.  No dcm2niix is called.  Rawdata is not modified.
- DICOM-to-NIfTI conversion execution is future work and must go through safety
  contract / approval / audit design first.

## Known Limitations

- NIfTI viewer not included (metadata-only)
- No complete QC dashboard
- No report editor
- MATLAB/SPM/DPABI/GPU are contract-only in this release
- **SPM realign is preparation-only**: parameter validation, environment health checks, dry-run manifests, and batch previews are available, but real MATLAB/SPM execution is not implemented
- **DICOM conversion is dry-run only**: mapping previews are generated but no files are written.
  Real dcm2niix execution is not implemented and must go through safety contract design first.
- **QC Dashboard cache is single-module prototype**: `cache=off|prefer|refresh` is supported, but caching currently applies only to the NIfTI QC Snapshot module. Other dashboard modules still run normally. Cache never modifies rawdata.
- **BIDS Validation fail is expected** for raw DICOM datasets before conversion.
  The UI now explains this.
- Dataset Summary may not yet fully integrate DICOM counts.
- Electron app is unsigned (SmartScreen warning on first run)
- Windows-only packaging
- No auto-update

See [release notes](docs/releases/v0.3.0-rc1.md) for full details.

---

## Roadmap

| Release | Focus |
|---|---|
| **v0.3.0-rc1** (current) | Desktop MVP: real project workflow, run history, artifact preview |
| v0.3.x | Installer signing, auto-update, CI/CD packaging pipeline; SPM realign preparation (params, health, dry-run, batch preview) |
| v0.4.0 | NIfTI viewer, enhanced QC dashboard, MATLAB/SPM runtime (opt-in) |
| Future | macOS/Linux packaging, DICOM browser, plugin system |

---

## Documentation

- [Release Notes v0.3.0-rc1](docs/releases/v0.3.0-rc1.md)
- [Desktop App Packaging](docs/DESKTOP_APP_PACKAGING.md)
- [Real Project Run Lifecycle](docs/REAL_PROJECT_RUN_LIFECYCLE.md)
- [MVP Release Smoke Checklist](docs/MVP_RELEASE_SMOKE_CHECKLIST.md)
- [Architecture Design](docs/architecture.md)
- [Agent Runtime Specification](docs/agent_runtime_spec.md)
- [Pipeline Executor Specification](docs/pipeline_executor.md)

---

## License

This project is for academic research purposes.

**MedImage Agent is a research engineering platform. It is not intended for
clinical diagnosis or medical decision-making.**
