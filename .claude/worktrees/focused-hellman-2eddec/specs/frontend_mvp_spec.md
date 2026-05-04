# Frontend MVP Specification

This document defines the MVP web frontend for MedImage Agent.

## Goals

The frontend should provide a minimal visual workflow for:

1. Checking backend API status.
2. Viewing project configuration.
3. Viewing available pipelines.
4. Inspecting a selected pipeline.
5. Creating an Agent plan.
6. Reviewing the generated plan.
7. Explicitly approving execution.
8. Viewing agent run summary.
9. Viewing dataset evaluation reports.
10. Viewing background review and proposed memory patch.

## Scope

Supported:

- React + TypeScript + Vite
- Local FastAPI backend
- Simple dashboard layout
- API health check
- Pipeline list
- Plan button
- Execute with approval button
- Report viewer
- JSON / Markdown / CSV text preview

Unsupported:

- Authentication
- Multi-user support
- Database
- Drag-and-drop pipeline builder
- WebSocket logs
- Real-time task streaming
- Medical image viewer
- GPU dashboard
- DPABI-specific UI
- Production deployment

## Safety Rules

- Execution button must clearly say it will run the approved pipeline.
- Execution must send `approved: true`.
- UI must never call execute automatically.
- UI must not provide delete file controls.
- UI must not expose arbitrary file reading beyond backend safe-file API.
- UI must distinguish QC/report output from clinical diagnosis.

## MVP Pages

The MVP can be a single page with sections:

1. API Status
2. Project Config
3. Pipeline Explorer
4. Agent Plan
5. Execute Pipeline
6. Agent Run Summary
7. Dataset Evaluation Report
8. Background Review

## Default Backend

```text
http://127.0.0.1:8000
```
