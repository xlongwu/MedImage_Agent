# MedImage Agent

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-v0.5.0--rc1-1976d2)](docs/releases/v0.6.0-rc1.md)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136%2B-green)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18%2B-61dafb)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5%2B-3178c6)](https://www.typescriptlang.org/)

**English** | [中文](README_CN.md)

MedImage Agent is a deterministic Plan-then-Execute desktop platform for
resting-state fMRI (rs-fMRI) research. The LLM plans and advises; execution
stays inside the Pipeline Runtime and registered node runners.

This is a research engineering platform, not a clinical diagnosis or clinical
decision product.

Current release line: **v0.6.0-rc1**. See
[release notes](docs/releases/v0.6.0-rc1.md).

## Quick Start

### Requirements

- Python 3.11+
- Node.js 20+
- MATLAB + SPM12 optional, only for explicitly env-gated SPM workflows
- CuPy optional, only for GPU paths

### Install

```bash
pip install -r requirements.txt
cd src/frontend && npm install
```

### Start Development Servers

```bash
uvicorn src.backend.app.main:app --host 127.0.0.1 --port 8000
cd src/frontend && npm run dev

# Or one-click:
start.bat
./start.sh
```

### Run Tests

```powershell
D:\Anaconda3\envs\mamba\python.exe -m pytest --tb=short --basetemp=.pytest_tmp
```

Frontend validation:

```powershell
cmd /c npm --prefix src/frontend run typecheck
cmd /c npm --prefix src/frontend run test
cmd /c npm --prefix src/frontend run build
```

## Desktop App

The Windows desktop app uses an Electron shell and a PyInstaller backend
sidecar. The frontend still talks to the backend through HTTP APIs; it does not
access the local filesystem directly.

Development build entry points:

```powershell
npm --prefix src/frontend run build
powershell -File desktop/packaging/build_backend.ps1 -PythonExe "D:\Anaconda3\envs\mamba\python.exe"
powershell -File desktop/packaging/build_desktop.ps1 -DirOnly -ElectronRuntimeZip "desktop\electron\.electron-cache\manual-runtime\electron-v31.7.7-win32-x64.zip"
```

See [Desktop App Packaging](docs/DESKTOP_APP_PACKAGING.md).

## Architecture

```text
Frontend (React + TypeScript + Vite)
    -> HTTP API
API Layer (FastAPI + Pydantic)
    -> Services and Schemas
Agent Runtime (Plan-then-Execute + Approval Gate)
    -> Pipeline Runtime (DAG Executor + Scheduler)
    -> Plugin Node Registry + Tool Catalog
```

State is local and project-scoped: SQLite stores project metadata and JSON
files store run state and artifacts. Runtime state writes use atomic file
writes. The Pipeline Runtime is the only pipeline execution path.

See [Architecture](docs/architecture.md) for current router, service, schema,
node registry, frontend API, storage, and desktop boundaries.

## Current Stable Workflow

```text
Select BIDS/rawdata
-> Create project
-> Generate project_config.yaml and dataset_index.json
-> Review plan with project context
-> Save reviewed plan
-> Execute reviewed plan through approval gates
-> Inspect run summary, events, logs, and artifacts
```

DICOM/FunRaw/T1Raw datasets support read-only detection and conversion dry-run
preview. Public DICOM conversion execution exists only as a fail-closed,
env-gated, approval/readiness-gated path; it is not automatic.

Phase 5 preprocessing workflows operate on converted/sandboxed inputs and
remain explicit, confirmable, and environment gated.

## Project Structure

```text
src/backend/app/
  api/                         domain routers and API middleware
  core/                        config, exceptions, logging
  schemas/                     request/response and contract schemas
  services/                    business logic and read models
  runtime/                     pipeline executor, state store, node registry
  runtime/node_registry_plugins/
                               plugin registries for node runners
  tools/                       processing, QC, wrappers, CLI helpers

src/frontend/src/
  lib/api/                     shared client and domain API modules
  components/                  reusable UI panels
  features/                    feature-level UI composition
  hooks/                       shared React hooks
  state/                       workflow state models
  types/                       shared frontend types

desktop/
  electron/                    Electron shell and smoke checks
  packaging/                   PyInstaller and Windows build scripts

docs/
  releases/                    historical release notes
  architecture.md              current architecture
  DESKTOP_APP_PACKAGING.md     packaging guide

tests/
  unit/                        unit and source-contract tests
  integration/                 opt-in smoke and integration tests
```

## Safety Architecture

| Rule | Mechanism |
| --- | --- |
| Rawdata read-only | path policy, checksum checks, approval wording |
| Approval required | Tool Catalog + Approval Gate + explicit confirmations |
| Path traversal blocked | `path_safety.py` and project/run artifact IDs |
| Frontend isolated | HTTP API modules and approved Electron bridge |
| External tools gated | environment flags, approval/readiness checks, audit records |
| Research use only | UI and documentation warnings |

## Known Limitations

- Not for clinical diagnosis or medical decision-making.
- DPABI execution remains disabled by default.
- MATLAB/SPM execution requires local tools plus explicit env flags.
- DICOM conversion execution is default-blocked and requires release approval
  evidence and multiple confirmations.
- Some numerical preprocessing stages may use metadata-first fallbacks when
  optional scientific dependencies are unavailable.
- No group statistics, classification, diagnosis model, report editor, or
  auto-update workflow is included in the current release line.
- Desktop packaging and GUI smoke require a compatible local Windows desktop
  environment.

## Documentation

- [Current Project State](PROJECT_STATE.md)
- [Architecture](docs/architecture.md)
- [Release Notes v0.6.0-rc1](docs/releases/v0.6.0-rc1.md)
- [Release Notes v0.4.0-rc1](docs/releases/v0.4.0-rc1.md)
- [Release Notes v0.3.0-rc1](docs/releases/v0.3.0-rc1.md)
- [Desktop App Packaging](docs/DESKTOP_APP_PACKAGING.md)
- [Real Project Run Lifecycle](docs/REAL_PROJECT_RUN_LIFECYCLE.md)
- [Safety Boundaries](docs/SAFETY_BOUNDARIES.md)

## License

This project is for academic research purposes.
