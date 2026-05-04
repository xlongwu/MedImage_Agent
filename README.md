# MedImage Agent

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61dafb)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0%2B-3178c6)](https://www.typescriptlang.org/)

**English** | [中文](README_CN.md)

MedImage Agent is a **deterministic agentic pipeline engineering platform** for resting-state fMRI (rs-fMRI) research. Inspired by the Plan-then-Execute architecture of Hermes Agent, it abandons the open-ended conversational loop of general LLM Agents and builds a secure, reproducible, and auditable medical image analysis workflow system.

**Core Positioning**: Medical Imaging AI Workflow / Agentic Pipeline / Research Engineering Platform

---

## Table of Contents

- [Background & Problem](#background--problem)
- [Core Design Philosophy](#core-design-philosophy)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Core Modules](#core-modules)
- [Security Mechanisms](#security-mechanisms)
- [Current Status & Boundaries](#current-status--boundaries)
- [Development Roadmap](#development-roadmap)
- [Documentation](#documentation)

---

## Background & Problem

In the field of rs-fMRI research, preprocessing workflows heavily rely on manual operations and researchers' experience. A typical workflow involves tools such as SPM (MATLAB) and DPABI, spanning over a dozen steps, each with numerous parameters to configure. This introduces three core challenges:

1. **Error-proneness**: Manual operations can easily miss steps or misconfigure parameters, leading to unreliable results
2. **Irreproducibility**: Researchers often fail to fully document all parameters and software versions in publications, making replication difficult for others
3. **Lack of auditability**: Traditional script-based pipelines lack complete execution records, making it impossible to trace "who did what, when, with which parameters, and what was produced"

Meanwhile, although general LLM Agents (such as Claude Code) are intelligent, directly controlling medical data poses security risks—they may accidentally delete files, modify raw data, and the stochastic nature of LLMs undermines scientific reproducibility.

---

## Core Design Philosophy

### Why Not a Regular Pipeline?

Traditional pipelines are static scripts lacking intelligent planning capabilities. MedImage Agent introduces an **Agent Runtime** that can automatically plan pipeline structures based on user goals, while the execution remains fully deterministic.

### Why Not a Regular Chatbot?

General LLM Agents adopt open-ended conversational loops with inherent randomness and security risks. MedImage Agent employs a **Plan-then-Execute** model:
- **Agent only plans**: Decomposes user goals into a pipeline plan
- **Engine handles execution**: Deterministic DAG engine executes strictly with no randomness
- **Human confirmation for critical steps**: Approval Gate ensures researchers' professional judgment is always in place

### Relationship with Hermes Agent

We draw inspiration from Hermes Agent's "plan-then-execute" architectural philosophy, but perform domain-specific refactoring:
- Retain the core Plan-then-Execute paradigm
- Replace open-ended conversation with deterministic pipeline execution
- Add medical imaging-specific security mechanisms (rawdata protection, permission grading, audit logging)

---

## System Architecture

The system is divided into four layers:

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend Layer                          │
│  React 18 + TypeScript + Vite + ECharts                     │
│  Pipeline Canvas | QC Report Viewer | Run History Timeline  │
│  Insights Dashboard | Approval Gate UI                      │
├─────────────────────────────────────────────────────────────┤
│                      API Layer                               │
│  FastAPI + Pydantic + asyncio + SSE (Server-Sent Events)    │
│  RESTful Endpoints | Streaming Logs | Health Checks         │
├─────────────────────────────────────────────────────────────┤
│                      Agent Runtime                           │
│  Plan-then-Execute | LLM Advisor | Approval Gate            │
│  Tool Registry (Permission Grading) | SessionDB | Audit     │
├─────────────────────────────────────────────────────────────┤
│                      Pipeline Runtime                        │
│  DAG Executor (Topological Sort) | Scheduler (Subject-Level │
│  Parallel) | Node Registry | State Store | Hook System      │
│  Error Diagnoser | Retry Runtime | Reproducibility Bundle   │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow / Control Flow / Audit Flow

**Data Flow**:
```
Rawdata (Read-only) → Pipeline Executor → Derivatives → QC → Reports
```

**Control Flow**:
```
User Goal → Agent Runtime (Plan) → Approval Gate → Pipeline Executor (Execute) → Results
```

**Audit Flow**:
```
Every Operation → Audit Logger → SessionDB → Run History → Reproducibility Bundle
```

---

## Tech Stack

### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Visualization**: ECharts (QC charts, motion parameter curves, ALFF/ReHo distributions)
- **State Management**: React Hooks
- **API Communication**: Fetch API + SSE streaming

### Backend
- **Framework**: FastAPI (Python 3.10+)
- **Async**: asyncio + async/await
- **Data Validation**: Pydantic
- **File Serving**: Static file hosting

### Pipeline Runtime
- **Execution Engine**: Custom DAG execution engine (topological sorting)
- **Scheduler**: Custom Scheduler (subject-level parallel processing)
- **State Management**: File-system-based State Store (run_id isolation)
- **Hook System**: pre / post / approval three-category hooks
- **Error Handling**: Error Diagnoser (error classification) + Retry Runtime (retry strategies)

### Agent Runtime
- **Architecture Pattern**: Plan-then-Execute
- **Planner**: Agent Runtime (decomposes goals into pipeline plans)
- **Approval Gate**: Human confirmation for critical steps
- **Tool Registry**: Three-tier permission system (readonly / write / destructive)
- **LLM Advisor**: Suggestion generation (does not control execution)
- **Session Database**: SessionDB (SQLite, records plan/execution/history)

### Medical Image Processing
- **Core Algorithms** (Native Python implementation):
  - ALFF / fALFF (FFT-based power spectrum calculation)
  - ReHo (Kendall's W, 27-neighborhood)
  - Functional Connectivity (ROI time-series correlation)
  - Nuisance Regression (linear regression denoising)
  - Temporal Filtering (band-pass filtering)
  - Motion QC (FD, DVARS, framewise displacement)
- **Data Format**: BIDS (Brain Imaging Data Structure)

### MATLAB / SPM / DPABI Integration
- **Integration Mode**: Contract-only design (extensible)
- **SPM Tools**: Realign, Slice Timing, Smooth, Normalize, Coregister, Segment
- **DPABI**: Plugin-style interface (extensible)

### GPU Acceleration Design
- **Status**: In design / extensible
- **Design Approach**: CuPy-accelerated matrix operations, subject-level parallelism

### Security & Audit
- **Path Safety**: Path normalization, directory traversal prevention, work_dir isolation
- **Permission Control**: Tool Registry permission grading
- **Audit Logging**: Audit Logger (operation logs, result logs)
- **Raw Data Protection**: Rawdata read-only access

---

## Quick Start

### Requirements

- Python 3.10+
- Node.js 18+
- MATLAB + SPM12 (optional, for SPM preprocessing steps)

### Install Dependencies

```bash
# Backend dependencies
pip install -r requirements.txt

# Frontend dependencies
cd frontend && npm install
```

### Start Services

```bash
# Start backend (development mode)
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

# Start frontend (development mode)
cd frontend && npm run dev
```

### Docker Demo Mode

```bash
# Start containerized demo (without MATLAB)
docker compose -f deploy/docker-compose.demo.yml up --build
```

### Run Examples

```bash
# Generate synthetic BIDS data
python -m backend.app.tools.synthetic_bids

# Run dataset evaluation
python -m backend.app.tools.run_dataset_evaluation_cli examples/project_config_dataset.yaml

# Run SPM realignment + Motion QC (requires approval)
python -m backend.app.tools.run_rsfmri_spm_realign_motion_qc_cli \
  examples/project_config_dataset.yaml \
  examples/pipeline_rsfmri_spm_realign_motion_qc.yaml \
  --approve
```

---

## Project Structure

```
MedImage_Agent/
├── src/
│   ├── backend/
│   │   └── app/
│   │       ├── api/                    # FastAPI routes
│   │       │   └── routes.py
│   │       ├── core/                   # Core config & models
│   │       │   ├── config.py
│   │       │   └── models.py
│   │       ├── runtime/                # Pipeline + Agent Runtime
│   │       │   ├── agent_runtime.py    # Agent planning & execution
│   │       │   ├── pipeline_executor.py # DAG execution engine
│   │       │   ├── scheduler.py        # Parallel scheduler
│   │       │   ├── node_registry.py    # Node registry
│   │       │   ├── state_store.py      # State persistence
│   │       │   ├── hook_manager.py     # Hook system
│   │       │   ├── error_diagnoser.py  # Error diagnosis
│   │       │   ├── retry_runtime.py    # Retry mechanism
│   │       │   └── run_inspector.py    # Run inspector
│   │       ├── tools/                  # Tool modules
│   │       │   ├── alff_falff.py       # ALFF/fALFF computation
│   │       │   ├── reho.py             # ReHo computation
│   │       │   ├── functional_connectivity.py  # Functional connectivity
│   │       │   ├── motion_qc.py        # Motion QC
│   │       │   ├── nuisance_regression.py      # Nuisance regression
│   │       │   ├── temporal_filtering.py       # Temporal filtering
│   │       │   ├── data_inspector.py   # Data inspection
│   │       │   ├── dataset_evaluator.py        # Dataset evaluation
│   │       │   ├── report_writer.py    # Report generation
│   │       │   ├── report_validator.py # Report validation
│   │       │   ├── reproducibility_bundle.py   # Reproducibility bundle
│   │       │   ├── synthetic_bids.py   # Synthetic data generation
│   │       │   └── spm_*.py            # SPM integration runners
│   │       ├── safety/                 # Security modules
│   │       │   ├── path_safety.py      # Path safety
│   │       │   ├── tool_registry.py    # Tool permission registry
│   │       │   └── audit_logger.py     # Audit logging
│   │       └── main.py                 # FastAPI entry point
│   └── frontend/
│       ├── src/
│       │   ├── App.tsx                 # Main app component
│       │   ├── components/             # UI components
│       │   ├── api.ts                  # API wrapper
│       │   └── types.ts                # TypeScript types
│       └── package.json
├── docs/                               # Project documentation
│   ├── architecture.md                 # Architecture design doc
│   ├── agent_runtime_spec.md           # Agent Runtime specification
│   └── pipeline_executor.md            # Pipeline Executor specification
├── examples/                           # Example configurations
│   ├── project_config_dataset.yaml
│   └── pipeline_*.yaml
├── tests/                              # Tests
│   └── unit/                           # Unit tests
├── deploy/                             # Deployment configs
│   ├── docker-compose.demo.yml
│   ├── backend.Dockerfile
│   └── frontend.Dockerfile
├── requirements.txt                    # Python dependencies
└── README.md                           # This file
```

---

## Core Modules

### 1. Pipeline Runtime (Deterministic Execution Engine)

- **DAG Execution**: Dependency-based execution via topological sorting, ensuring steps run in correct order
- **Parallel Scheduling**: Subject-level parallel processing to improve multi-subject dataset throughput
- **State Persistence**: State files written immediately after each step completes, supporting breakpoint resumption
- **Hook System**: pre-hook (parameter validation), post-hook (result verification), approval-hook (human confirmation)

### 2. Agent Runtime (Intelligent Planning Layer)

- **Plan-then-Execute**: Agent generates pipeline plan, deterministic engine executes
- **Approval Gate**: plan-level approval (overall confirmation) + step-level approval (destructive operation confirmation)
- **Tool Registry**: Tools declare permission levels at registration, implementing least privilege principle
- **LLM Advisor**: Natural language descriptions converted to pipeline configuration suggestions (non-mandatory)

### 3. Medical Image Processing

| Module | Function | Status |
|--------|----------|--------|
| ALFF / fALFF | Low-frequency amplitude calculation | ✅ Implemented |
| ReHo | Regional homogeneity calculation | ✅ Implemented |
| Functional Connectivity | Functional connectivity matrix | ✅ Implemented |
| Motion QC | Motion metrics (FD/DVARS) | ✅ Implemented |
| Nuisance Regression | Denoising regression | ✅ Implemented |
| Temporal Filtering | Band-pass filtering | ✅ Implemented |
| SPM Realign | Motion correction | ✅ Implemented |
| SPM Slice Timing | Slice timing correction | ✅ Implemented |
| SPM Normalize | Spatial normalization | ✅ Implemented |
| SPM Smooth | Spatial smoothing | ✅ Implemented |
| SPM Coregister | Coregistration | ✅ Implemented |
| SPM Segment | Segmentation | ✅ Implemented |
| GPU Acceleration | CuPy acceleration | 🔄 In Design |

### 4. QC & Reporting

- **Automated QC**: Motion QC, dataset integrity checks, outlier detection
- **Report Generation**: Markdown + HTML dual format with ECharts visualizations
- **Report Validation**: Schema validation, data consistency checks
- **Reproducibility Bundle**: Environment snapshot + file checksum + git state

### 5. Data Management

- **BIDS Support**: Compliant with Brain Imaging Data Structure specification
- **Synthetic Data**: synthetic_bids.py generates test data for development and validation without real patient data
- **Dataset Evaluation**: Automatic checks for completeness, scan parameter consistency, and outliers

---

## Security Mechanisms

MedImage Agent adopts a multi-layer security design to ensure research data is not accidentally modified:

### 1. Path Safety
- All paths are forcibly normalized, directory traversal attacks are prohibited
- Operations are forcibly restricted within work_dir, system-sensitive paths are inaccessible
- Rawdata directory is marked read-only, any write operation is rejected

### 2. Tool Permission Grading (Tool Registry)
- **readonly**: Read-only operations (e.g., data inspection, report generation)
- **write**: Write operations (e.g., saving intermediate results)
- **destructive**: Destructive operations (e.g., deletion, overwriting), automatically triggers Approval Gate

### 3. Approval Gate
- **plan-level approval**: Overall pipeline execution requires confirmation
- **step-level approval**: Destructive operations require secondary confirmation
- Unapproved operations fail safely and will not execute

### 4. Audit Logger
- Records timestamp, user, tool, parameters, and results for all operations
- Supports full Run History traceability
- Audit logs themselves are immutable

### 5. Raw Data Protection
- Rawdata is accessed in read-only mode
- All outputs are written to isolated derivatives directories
- Synthetic data mode (synthetic_only) supports risk-free demonstrations

---

## Current Status & Boundaries

### Implemented
- ✅ Complete Pipeline Runtime (DAG execution, parallel scheduling, state persistence)
- ✅ Agent Runtime (Plan-then-Execute, Approval Gate, Tool Registry)
- ✅ Core imaging algorithms (ALFF/fALFF, ReHo, Functional Connectivity)
- ✅ SPM integration interfaces (Contract-only design, 6 core modules)
- ✅ QC automation (Motion QC, dataset evaluation)
- ✅ Reporting system (Markdown/HTML dual format, reproducibility bundle)
- ✅ Frontend visualization (Pipeline Canvas, QC Viewer, Run History, Insights Dashboard)
- ✅ Security mechanisms (Path Safety, permission grading, audit logging)
- ✅ Error diagnosis and retry system

### In Design / Extensible
- 🔄 GPU acceleration (CuPy implementation, files created, core logic pending)
- 🔄 Full DPABI integration (interface design complete, pending implementation)
- 🔄 Distributed execution (multi-machine parallelism, architecture reserved)
- 🔄 Docker containerized one-click deployment (config files created)
- 🔄 Real clinical data validation (currently using synthetic data)

### Clear Boundaries
- **Not a clinical product**: This project is positioned as a research engineering platform, not for clinical diagnosis or clinical decision-making
- **Synthetic data demo**: Currently defaults to synthetic BIDS data, real data requires additional configuration
- **Optional MATLAB dependency**: SPM steps require MATLAB, core algorithms do not depend on it

---

## Development Roadmap

| Phase | Goal | Status |
|-------|------|--------|
| Phase 1 | Pipeline Runtime + Core Algorithms | ✅ Complete |
| Phase 2 | Agent Runtime + Security Mechanisms | ✅ Complete |
| Phase 3 | SPM Integration + QC System | ✅ Complete |
| Phase 4 | Frontend Visualization + Reporting System | ✅ Complete |
| Phase 5 | GPU Acceleration + Performance Optimization | 🔄 In Progress |
| Phase 6 | Real Data Validation + Publication | 📋 Planned |

---

## Documentation

- [Architecture Design Document](docs/architecture.md)
- [Agent Runtime Specification](docs/agent_runtime_spec.md)
- [Pipeline Executor Specification](docs/pipeline_executor.md)

---

## License

This project is for academic research purposes.

---

**Note**: MedImage Agent is a medical imaging research workflow platform / agentic pipeline system / rs-fMRI preprocessing and analysis engineering platform. It is not intended for clinical diagnosis or medical decision-making.
