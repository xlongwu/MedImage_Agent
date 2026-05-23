# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

MedImage Agent is a **deterministic agentic pipeline engineering platform** for resting-state fMRI (rs-fMRI) research. It uses a **Plan-then-Execute** architecture: the Agent Runtime generates structured pipeline plans from user goals, and the Pipeline Runtime executes them deterministically as a DAG. No open-ended LLM conversation loop — the LLM only advises, never controls execution.

## Commands

```bash
# Install
pip install -r requirements.txt
cd src/frontend && npm install

# Start backend (port 8000)
uvicorn src.backend.app.main:app --host 127.0.0.1 --port 8000

# Start frontend (port 5173)
cd src/frontend && npm run dev

# One-click startup
./start.sh          # Linux/macOS
start.bat           # Windows

# Docker demo (no MATLAB)
docker compose -f deploy/docker-compose.demo.yml up --build

# Run all tests
pytest

# Run a single test file
pytest tests/unit/test_motion_qc.py

# Run a specific test
pytest tests/unit/test_pipeline_schema.py -k test_validates_minimal_pipeline

# Run CLI tools (each pipeline YAML has a corresponding CLI runner)
python -m src.backend.app.tools.run_pipeline_cli examples/project_config.yaml examples/pipeline_mvp.yaml
python -m src.backend.app.tools.run_rsfmri_spm_realign_motion_qc_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_spm_realign_motion_qc.yaml --approve

# Build frontend
cd src/frontend && npm run build
```

## Architecture

Four layers, top to bottom:

```
Frontend (React 18 + TypeScript + Vite)
    ↓
API Layer (FastAPI + Pydantic) — src/backend/app/api/
    ↓
Agent Runtime (Plan-then-Execute + Approval Gate) — src/backend/app/runtime/agent_runtime.py
    ↓
Pipeline Runtime (DAG Executor + Scheduler) — src/backend/app/runtime/pipeline_executor.py
```

### Key design decisions

- **State is file-system based**, not a database. Each run writes state JSON files under `work/states/<run_id>/`. The `state_store.py` module handles all persistence.
- **Node Registry pattern**: every pipeline step maps a node `id` to a runner function in `src/backend/app/runtime/node_registry.py`. To add a new processing step, register it there.
- **Pipeline YAMLs** define workflows declaratively. Each node has `id`, `backend`, `depends_on`, `inputs`, `outputs`, `params`, `parallel_level`, and `gpu_supported` fields. Schema lives at `src/backend/app/schemas/pipeline_schema.py`.
- **Tool permission system** (`src/backend/app/runtime/tool_registry.py`): each tool declares `read_only`, `writes_files`, `destructive`, `requires_confirmation`, and `parallel_safe` flags. Execution of `requires_confirmation` tools fails without explicit `approved=true`.
- **Path safety** (`src/backend/app/runtime/path_safety.py`): all file access goes through path resolution that prevents directory traversal and enforces allowed read/write directories.
- **The orchestrator agent** (`src/agents/orchestrator.md`) is deterministic — it does not call an LLM. It creates structured plans from config and pipeline YAML.
- **DPABI/GPU backends are contract-only**: they generate spec files but never execute. Actual MATLAB/SPM execution requires `approved=true` and `MEDIMAGE_MATLAB_ENABLED=true`.

### Directory map

| Directory | Purpose |
|---|---|
| `src/backend/app/runtime/` | Pipeline executor, node registry, scheduler, state store, hooks, error diagnosis, retry, memory store |
| `src/backend/app/tools/` | All processing modules, QC, CLI runners, contract writers, SPM/MATLAB wrappers |
| `src/backend/app/api/` | FastAPI routes (`routes.py`) and Pydantic models (`models.py`) |
| `src/backend/app/schemas/` | Pipeline YAML schema validation |
| `src/backend/app/preprocessing/` | rs-fMRI step registry and plan builder |
| `src/backend/app/advisor/` | LLM advisor modules (parameter, protocol, QC, error, docs-qa advisors) |
| `src/frontend/src/components/` | React panels, one per pipeline stage + workflow shell |
| `examples/` | Pipeline YAML files (30+) and project config YAMLs |
| `specs/` | Feature specification markdown files (50+) |
| `docs/` | Architecture, developer guide, user guide, next-stage plan |
| `memory/global/` | Error knowledge base (`ERROR_KB.yaml`) |
| `matlab/` | MATLAB SPM wrapper scripts |
| `third_party/` | DPABI and SPM binaries (not committed, local only) |
| `deploy/` | Dockerfiles and docker-compose |

### Adding a new pipeline stage

Per `docs/developer_guide.md`:
1. Create the processing/QC module in `src/backend/app/tools/`
2. Register the node in `src/backend/app/runtime/node_registry.py`
3. Create a pipeline YAML in `examples/`
4. Create a CLI runner in `src/backend/app/tools/`
5. Add API endpoint in `src/backend/app/api/routes.py` + model in `models.py`
6. Add a frontend panel in `src/frontend/src/components/`
7. Add tests in `tests/unit/`

### Key conventions

- Subject-level nodes accept `subject_record` and `subject_id` parameters. Project-level nodes do not.
- Every processing step has a companion QC module.
- All derivative outputs go to `outputs/derivatives/` — never modify `data/` (rawdata).
- Import style uses `from __future__ import annotations` throughout.
